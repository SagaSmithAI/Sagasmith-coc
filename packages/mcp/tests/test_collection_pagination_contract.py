from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator
from mcp import Client, StdioServerParameters
from sagasmith_core import RevisionService

from sagasmith_coc_mcp.config import McpConfig
from sagasmith_coc_mcp.server import create_server


def _config(tmp_path: Path) -> McpConfig:
    return McpConfig(
        home=tmp_path / "home",
        database_url=None,
        coc_skills_dir=tmp_path / "skills",
        modulegen_skills_dir=tmp_path / "modulegen",
    )


async def _seed_campaign(server) -> tuple[str, str]:
    campaign = (
        await server.call_tool(
            "campaign_change",
            {
                "action": "create",
                "data": {
                    "name": "Pagination contract",
                    "idempotency_key": "pagination-contract-campaign",
                },
            },
        )
    ).structured_content
    actor = (
        await server.call_tool(
            "character_change",
            {
                "action": "create",
                "campaign_id": campaign["id"],
                "data": {
                    "name": "Catalog Reader",
                    "character_type": "investigator",
                    "sheet": {"skills": {"Library Use": 60}},
                    "expected_campaign_revision": campaign["revision"],
                    "idempotency_key": "pagination-contract-actor",
                },
            },
        )
    ).structured_content
    return campaign["id"], actor["id"]


def _environment(tmp_path: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "SAGASMITH_COC_MCP_TRANSPORT": "stdio",
            "SAGASMITH_COC_MCP_HOME": str(tmp_path / "home"),
            "SAGASMITH_COC_SKILLS_DIR": str(tmp_path / "skills"),
            "SAGASMITH_MODULEGEN_SKILLS_DIR": str(tmp_path / "modulegen"),
        }
    )
    return environment


def test_real_modern_client_validates_successful_collection_results_against_catalog(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        campaign_id, actor_id = await _seed_campaign(create_server(_config(tmp_path)))
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "sagasmith_coc_mcp.server"],
            env=_environment(tmp_path),
        )
        calls = (
            ("module_draft", {"action": "get", "campaign_id": campaign_id}),
            ("rule_query", {"action": "sources", "campaign_id": campaign_id}),
            ("module_query", {"action": "list", "campaign_id": campaign_id}),
            ("module_query", {"action": "index", "campaign_id": campaign_id}),
            ("module_query", {"action": "progress", "campaign_id": campaign_id}),
            (
                "module_query",
                {"action": "search", "campaign_id": campaign_id, "query": "lantern"},
            ),
            ("memory_query", {"action": "list", "campaign_id": campaign_id}),
            (
                "memory_query",
                {"action": "search", "campaign_id": campaign_id, "query": "lantern"},
            ),
            (
                "actor_knowledge_query",
                {"action": "list", "campaign_id": campaign_id, "actor_id": actor_id},
            ),
            (
                "actor_knowledge_query",
                {
                    "action": "search",
                    "campaign_id": campaign_id,
                    "actor_id": actor_id,
                    "query": "lantern",
                },
            ),
            ("branch_query", {"action": "list", "campaign_id": campaign_id}),
            ("snapshot_query", {"action": "list", "campaign_id": campaign_id}),
            ("snapshot_query", {"action": "lineage", "campaign_id": campaign_id}),
            (
                "investigation_query",
                {"campaign_id": campaign_id, "actor_id": actor_id, "view": "history"},
            ),
            ("campaign_event", {"action": "list", "campaign_id": campaign_id}),
            ("state_revision", {"action": "history", "campaign_id": campaign_id}),
        )
        async with Client(parameters, mode="2026-07-28") as client:
            catalog = {tool.name: tool for tool in (await client.list_tools()).tools}
            for tool_name in {
                "actor_knowledge_query",
                "branch_query",
                "campaign_event",
                "investigation_query",
                "memory_query",
                "module_draft",
                "module_query",
                "rule_query",
                "snapshot_query",
                "state_revision",
            }:
                inputs = catalog[tool_name].input_schema["properties"]
                assert {"query", "limit", "cursor"}.issubset(inputs), tool_name
                assert inputs["limit"]["minimum"] == 1, tool_name
                assert inputs["limit"]["maximum"] == 100, tool_name
            for tool_name, arguments in calls:
                result = await client.call_tool(tool_name, arguments)
                assert result.is_error is False, (tool_name, result.content)
                assert result.content, tool_name
                assert result.structured_content is not None, tool_name
                structured = result.structured_content
                assert structured["next_cursor"] is None, tool_name
                assert structured["has_more"] is False, tool_name
                schema = catalog[tool_name].output_schema
                assert schema is not None, tool_name
                properties = schema["properties"]
                assert set(structured).issubset(properties), (
                    tool_name,
                    set(structured) - set(properties),
                )
                assert properties["has_more"]["type"] == "boolean", tool_name
                assert properties["next_cursor"]["type"] == ["string", "null"], tool_name
                collection_key = next(
                    key
                    for key in structured
                    if key
                    not in {
                        "actor_id",
                        "campaign_id",
                        "campaign_revision",
                        "has_more",
                        "next_cursor",
                        "order",
                    }
                )
                assert properties[collection_key]["type"] == "array", (
                    tool_name,
                    collection_key,
                )

    asyncio.run(exercise())


def test_real_modern_client_validates_every_continuity_result_shape(tmp_path: Path) -> None:
    async def exercise() -> None:
        campaign_id, actor_id = await _seed_campaign(create_server(_config(tmp_path)))
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "sagasmith_coc_mcp.server"],
            env=_environment(tmp_path),
        )
        async with Client(parameters, mode="2026-07-28") as client:
            catalog = {tool.name: tool for tool in (await client.list_tools()).tools}
            schema = catalog["continuity_context"].output_schema
            assert schema is not None
            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema)

            results = [
                await client.call_tool("continuity_context", {"campaign_id": campaign_id}),
                await client.call_tool(
                    "continuity_context",
                    {
                        "campaign_id": campaign_id,
                        "actor_id": actor_id,
                        "purpose": "actor_memory",
                    },
                ),
                await client.call_tool(
                    "continuity_context",
                    {
                        "campaign_id": campaign_id,
                        "purpose": "source_interpretation",
                        "query": "Interpret the lamp's soot against known evidence.",
                    },
                ),
            ]
            for result in results:
                assert result.is_error is False, result.content
                assert result.structured_content is not None
                assert list(validator.iter_errors(result.structured_content)) == []

            actor_memory = results[1].structured_content
            assert actor_memory["memory"]["identity"]
            bounded = results[2].structured_content
            assert bounded["constraints"]["may_write_state"] is False
            assert schema["properties"]["constraints"]["type"] == "object"

    asyncio.run(exercise())


def test_event_cursor_reaches_records_beyond_first_hundred(tmp_path: Path) -> None:
    async def exercise() -> None:
        server = create_server(_config(tmp_path))
        campaign_id, _ = await _seed_campaign(server)
        for index in range(105):
            added = await server.call_tool(
                "campaign_event",
                {
                    "action": "add",
                    "campaign_id": campaign_id,
                    "idempotency_key": f"event-{index:03d}",
                    "data": {"summary": f"Archive event {index:03d}"},
                },
            )
            assert added.is_error is False

        first = (
            await server.call_tool(
                "campaign_event",
                {"action": "list", "campaign_id": campaign_id, "limit": 100},
            )
        ).structured_content
        second = (
            await server.call_tool(
                "campaign_event",
                {
                    "action": "list",
                    "campaign_id": campaign_id,
                    "limit": 100,
                    "cursor": first["next_cursor"],
                },
            )
        ).structured_content
        assert first["has_more"] is True
        assert len(first["events"]) == 100
        assert second["has_more"] is False
        assert len(second["events"]) == 5
        assert len({item["id"] for item in first["events"] + second["events"]}) == 105

    asyncio.run(exercise())


@dataclass(frozen=True)
class _RevisionFixture:
    sequence: int
    operation: str


def test_state_revision_cursor_pushes_offset_into_core(
    tmp_path: Path,
    monkeypatch,
) -> None:
    offsets: list[int] = []

    def history(_self, _campaign_id: str, *, limit: int = 100, offset: int = 0):
        offsets.append(offset)
        values = [
            _RevisionFixture(sequence=index, operation=f"fixture-{index:03d}")
            for index in range(105, 0, -1)
        ]
        return values[offset : offset + limit]

    monkeypatch.setattr(RevisionService, "history", history)

    async def exercise() -> None:
        server = create_server(_config(tmp_path))
        campaign_id, _ = await _seed_campaign(server)
        first = (
            await server.call_tool(
                "state_revision",
                {"action": "history", "campaign_id": campaign_id, "limit": 100},
            )
        ).structured_content
        second = (
            await server.call_tool(
                "state_revision",
                {
                    "action": "history",
                    "campaign_id": campaign_id,
                    "limit": 100,
                    "cursor": first["next_cursor"],
                },
            )
        ).structured_content
        assert len(first["revisions"]) == 100
        assert first["has_more"] is True
        assert [item["sequence"] for item in second["revisions"]] == [5, 4, 3, 2, 1]
        assert second["has_more"] is False
        assert offsets == [0, 100, 100]

    asyncio.run(exercise())
