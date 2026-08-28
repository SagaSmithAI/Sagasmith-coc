from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from sagasmith_core.auth_context import (
    AUTH_CONTEXT_DELEGATION_SCHEMA,
    AUTH_CONTEXT_META_KEY,
    sign_delegated_auth_context,
)

from sagasmith_coc_mcp.config import McpConfig
from sagasmith_coc_mcp.server import create_server

SECRET = "modern-test-auth-context-secret-at-least-32-bytes"
SERVICE = "sagasmith-coc-mcp"


def config(tmp_path: Path) -> McpConfig:
    return McpConfig(
        home=tmp_path / "home",
        database_url=None,
        coc_skills_dir=tmp_path / "skills",
        modulegen_skills_dir=tmp_path / "modulegen",
        auth_context_secret=SECRET,
    )


def delegated_meta(*, nonce: str, target_service: str = SERVICE) -> dict[str, object]:
    return {
        AUTH_CONTEXT_META_KEY: sign_delegated_auth_context(
            secret=SECRET,
            issuer="sagasmith-web",
            target_service=target_service,
            caller_principal="workload:hosted-agent",
            workload_identity="deployment:sagasmith-agent/test",
            requester_principal="discord:user:authorized",
            resource_owner_principal="discord:user:authorized",
            acting_host_principal="host:keeper",
            acting_character_id="character:investigator",
            authorized_audience=SERVICE,
            allowed_operations=["campaign_query"],
            conversation_principal="discord:room:test",
            campaign_id="campaign:scope",
            room_turn_id="turn:modern-contract",
            base_revision=0,
            nonce=nonce,
        )
    }


def modern_context(
    server,
    metadata: dict[str, object],
    *,
    headers: dict[str, str] | None = None,
) -> Context:
    request_context = SimpleNamespace(
        meta=metadata,
        protocol_version="2026-07-28",
        request=SimpleNamespace(headers=headers),
    )
    return Context(
        request_context=request_context,
        mcp_server=server,
        subscriptions=server._subscriptions,
    )


def test_modern_delegation_overrides_model_identity_and_binds_audience(tmp_path: Path) -> None:
    async def exercise() -> None:
        server = create_server(config(tmp_path))
        context = modern_context(
            server,
            delegated_meta(nonce="accepted-modern"),
            headers={
                "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                "tracestate": "vendor=opaque",
            },
        )
        result = await server.call_tool(
            "campaign_query",
            {"action": "list", "principal_id": "model:forged"},
            context,
        )
        assert not result.is_error
        receipt = result.content[0].meta["sagasmith_auth_context_receipt"]
        assert receipt["schema"] == AUTH_CONTEXT_DELEGATION_SCHEMA
        assert receipt["requester_principal"] == "discord:user:authorized"
        assert receipt["target_service"] == SERVICE
        assert receipt["authorized_audience"] == SERVICE
        assert receipt["room_turn_id"] == "turn:modern-contract"
        assert result.meta["sagasmith_trace_context"] == {
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
            "tracestate": "vendor=opaque",
        }

        wrong_service = modern_context(
            server,
            delegated_meta(nonce="wrong-service", target_service="sagasmith-dnd-mcp"),
        )
        with pytest.raises(ToolError, match="target service"):
            await server.call_tool(
                "campaign_query",
                {"action": "list", "principal_id": "model:forged"},
                wrong_service,
            )

        stale_revision = modern_context(server, delegated_meta(nonce="stale-revision"))
        with pytest.raises(ToolError, match="base revision is stale"):
            await server.call_tool(
                "campaign_query",
                {"action": "list", "base_revision": 1},
                stale_revision,
            )

    asyncio.run(exercise())


def test_modern_catalog_is_sorted_stable_annotated_and_schema_backed(tmp_path: Path) -> None:
    async def exercise() -> None:
        server = create_server(config(tmp_path))
        first = await server.list_tools()
        names = [tool.name for tool in first]
        assert names == sorted(names)
        assert len(names) == len(set(names))
        assert all(tool.output_schema is not None for tool in first)
        assert all(tool.annotations is not None for tool in first)
        assert all(tool.annotations.read_only_hint is not None for tool in first)
        assert all(tool.annotations.destructive_hint is not None for tool in first)
        assert all(tool.annotations.idempotent_hint is not None for tool in first)
        assert all(tool.annotations.open_world_hint is False for tool in first)

        server.exposure_registry.open(
            session_key="legacy:side-effect",
            principal_id="system:local",
            campaign_id=None,
            phase="lobby",
        )
        assert [tool.name for tool in await server.list_tools()] == names

    asyncio.run(exercise())


def test_campaign_catalog_filter_and_cursor_are_bounded(tmp_path: Path) -> None:
    async def exercise() -> None:
        server = create_server(
            McpConfig(
                home=tmp_path / "home",
                database_url=None,
                coc_skills_dir=tmp_path / "skills",
                modulegen_skills_dir=tmp_path / "modulegen",
            )
        )
        for index in range(3):
            await server.call_tool(
                "campaign_change",
                {
                    "action": "create",
                    "data": {
                        "name": f"Archive Case {index}",
                        "idempotency_key": f"campaign-{index}",
                    },
                },
            )
        first = (
            await server.call_tool(
                "campaign_query",
                {"action": "list", "query": "archive", "limit": 2},
            )
        ).structured_content
        assert len(first["campaigns"]) == 2
        assert first["next_cursor"] == "p:2"
        second = (
            await server.call_tool(
                "campaign_query",
                {
                    "action": "list",
                    "query": "archive",
                    "limit": 2,
                    "cursor": first["next_cursor"],
                },
            )
        ).structured_content
        assert len(second["campaigns"]) == 1
        assert second["next_cursor"] is None

        campaign_tool = next(
            tool for tool in await server.list_tools() if tool.name == "campaign_query"
        )
        limit_schema = campaign_tool.input_schema["properties"]["limit"]
        assert limit_schema["minimum"] == 1
        assert limit_schema["maximum"] == 100

    asyncio.run(exercise())
