from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolRequestParams

from sagasmith_coc_mcp.config import McpConfig
from sagasmith_coc_mcp.server import _classify_tool_error, create_server


def _server(tmp_path: Path):
    return create_server(
        McpConfig(
            home=tmp_path / "home",
            database_url=None,
            coc_skills_dir=tmp_path / "skills",
            modulegen_skills_dir=tmp_path / "modulegen",
        )
    )


def test_every_public_tool_has_model_usable_contract_metadata(tmp_path: Path) -> None:
    async def exercise() -> None:
        tools = await _server(tmp_path).list_tools()
        assert len(tools) == 52
        for tool in tools:
            assert tool.description.strip(), tool.name
            properties = tool.input_schema.get("properties") or {}
            assert all(
                str(schema.get("description") or "").strip() for schema in properties.values()
            ), tool.name
            assert tool.output_schema is not None, tool.name
            assert (tool.output_schema.get("properties") or {}).get("error"), tool.name
            assert len(tool.output_schema.get("properties") or {}) > 2, tool.name
            assert tool.annotations is not None, tool.name
            assert tool.annotations.read_only_hint is not None, tool.name
            assert tool.annotations.destructive_hint is not None, tool.name
            assert tool.annotations.idempotent_hint is not None, tool.name
            assert tool.annotations.open_world_hint is False, tool.name

    asyncio.run(exercise())


def test_character_change_data_contract_advertises_nested_guards(tmp_path: Path) -> None:
    async def exercise() -> None:
        tools = await _server(tmp_path).list_tools()
        character_change = next(tool for tool in tools if tool.name == "character_change")
        description = character_change.input_schema["properties"]["data"]["description"]
        assert "idempotency_key" in description
        assert "expected_campaign_revision" in description
        assert "character_type" in description
        assert "expected_revision" in description

    asyncio.run(exercise())


def test_module_draft_contract_discriminates_package_workflow(tmp_path: Path) -> None:
    async def exercise() -> None:
        tools = await _server(tmp_path).list_tools()
        module_draft = next(tool for tool in tools if tool.name == "module_draft")
        schema = module_draft.input_schema
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)

        source_ref = {
            "source_key": "generated-scenario.md",
            "page": 1,
            "chunk_hash": "a" * 64,
            "note": "Agent-reviewed source evidence: scenario brief",
        }
        play_profile = {
            "investigator_count": {
                "minimum": 2,
                "maximum": 4,
                "source_refs": [source_ref],
            },
            "ruleset": {
                "supported": ["classic"],
                "recommended": "classic",
                "source_refs": [source_ref],
            },
            "era": {"value": "1920s", "source_refs": [source_ref]},
            "estimated_sessions": {
                "minimum": 1,
                "maximum": 3,
                "source_refs": [source_ref],
            },
            "pregenerated_characters": {
                "available": False,
                "applicability": "None",
                "source_refs": [source_ref],
            },
            "solo_play": {"supported": False, "source_refs": [source_ref]},
        }
        package_edit = {
            "action": "edit",
            "campaign_id": "campaign-1",
            "expected_revision": 4,
            "idempotency_key": "package-edit-1",
            "data": {
                "job_id": "job-1",
                "operation": "package",
                "manifest": {
                    "title": "The Lantern Below",
                    "classification": "scenario",
                    "compatibility": {
                        "editions": ["7e"],
                        "required_capabilities": ["module_pack_v2"],
                    },
                    "activation": {"mode": "campaign_attach", "default_active": False},
                    "continuity": {
                        "series_id": None,
                        "order": None,
                        "continues_from": None,
                        "state_policy": {},
                    },
                    "play_profile": play_profile,
                },
                "narrative": {"dossiers": [], "endings": []},
            },
        }
        assert list(validator.iter_errors(package_edit)) == []

        finalize = {
            "action": "finalize",
            "campaign_id": "campaign-1",
            "expected_revision": 5,
            "idempotency_key": "finalize-1",
            "data": {
                "job_id": "job-1",
                "package_id": "package-1",
                "confirmation": {
                    "confirmed": True,
                    "note": "Reviewed source receipts and Pack decisions.",
                },
            },
        }
        assert list(validator.iter_errors(finalize)) == []

        for missing in ("expected_revision", "idempotency_key"):
            invalid = dict(finalize)
            invalid.pop(missing)
            assert list(validator.iter_errors(invalid)), missing
        invalid_confirmation = {
            **finalize,
            "data": {"job_id": "job-1", "package_id": "package-1"},
        }
        assert list(validator.iter_errors(invalid_confirmation))

        data_description = schema["properties"]["data"]["description"]
        revision_description = schema["properties"]["expected_revision"]["description"]
        assert "finalize requires job_id, package_id" in data_description
        assert "Import-job revision" in revision_description
        assert len(schema["allOf"]) == 4

    asyncio.run(exercise())


def test_advertised_bounds_are_enforced_before_dispatch(tmp_path: Path) -> None:
    async def exercise() -> None:
        server = _server(tmp_path)
        with pytest.raises(ToolError, match="limit must be an integer between 1 and 100"):
            await server.call_tool("campaign_query", {"action": "list", "limit": 101})
        with pytest.raises(ToolError, match="65536 characters"):
            await server.call_tool(
                "campaign_change",
                {"action": "create", "data": {"name": "x" * 65_537}},
            )

    asyncio.run(exercise())


def test_tool_execution_error_is_structured_and_actionable(tmp_path: Path) -> None:
    async def exercise() -> None:
        server = _server(tmp_path)
        context = SimpleNamespace(
            protocol_version="2026-07-28",
            meta={},
            request=SimpleNamespace(headers={}),
        )
        result = await server._handle_call_tool(
            context,
            CallToolRequestParams(
                name="campaign_query",
                arguments={"action": "unsupported"},
            ),
        )
        assert result.is_error is True
        assert result.content
        error = result.structured_content["error"]
        assert error["code"] == "invalid_argument"
        assert error["message"]
        assert isinstance(error["retryable"], bool)
        assert error["recovery"]

    asyncio.run(exercise())


def test_success_preserves_legacy_text_and_structured_content(tmp_path: Path) -> None:
    async def exercise() -> None:
        result = await _server(tmp_path).call_tool("campaign_query", {"action": "list"})
        assert result.is_error is False
        assert result.content
        assert result.structured_content == {
            "campaigns": [],
            "next_cursor": None,
            "has_more": False,
        }

    asyncio.run(exercise())


def test_game_phase_returns_revision_promised_by_public_contract(tmp_path: Path) -> None:
    async def exercise() -> None:
        server = _server(tmp_path)
        created = await server.call_tool(
            "campaign_change",
            {"action": "create", "data": {"name": "Luna contract campaign"}},
        )
        campaign_id = created.structured_content["id"]
        phase = await server.call_tool("game_phase", {"campaign_id": campaign_id})
        assert phase.structured_content == {
            "campaign_id": campaign_id,
            "phase": "lobby",
            "revision": 1,
        }

    asyncio.run(exercise())


def test_nested_mutation_requirements_are_actionable(tmp_path: Path) -> None:
    async def exercise() -> None:
        server = _server(tmp_path)
        created = await server.call_tool(
            "campaign_change",
            {"action": "create", "data": {"name": "Nested requirements"}},
        )
        campaign_id = created.structured_content["id"]
        with pytest.raises(ToolError, match=r"data\.expected_campaign_revision is required"):
            await server.call_tool(
                "character_change",
                {
                    "action": "create",
                    "campaign_id": campaign_id,
                    "data": {"name": "Missing guard", "idempotency_key": "missing-guard"},
                },
            )

    asyncio.run(exercise())


def test_internal_key_error_text_is_not_classified_as_missing_input() -> None:
    error = _classify_tool_error("'internal_state_key'")
    assert error["error"]["code"] == "tool_execution_failed"
    assert "required" not in error["error"]["message"]


def test_character_type_and_campaign_locale_are_not_silently_discarded(tmp_path: Path) -> None:
    async def exercise() -> None:
        server = _server(tmp_path)
        created = await server.call_tool(
            "campaign_change",
            {
                "action": "create",
                "data": {
                    "name": "Metadata contract",
                    "era": "1927",
                    "locale": "Dunwich, Massachusetts",
                },
            },
        )
        campaign_id = created.structured_content["id"]
        assert created.structured_content["settings"] == {
            "era": "1927",
            "locale": "Dunwich, Massachusetts",
        }
        with pytest.raises(ToolError, match=r"data\.character_type is required"):
            await server.call_tool(
                "character_change",
                {
                    "action": "create",
                    "campaign_id": campaign_id,
                    "data": {
                        "name": "Typed NPC",
                        "type": "npc",
                        "idempotency_key": "typed-npc",
                        "expected_campaign_revision": 1,
                    },
                },
            )

    asyncio.run(exercise())


def test_legacy_scope_validation_returns_safe_error_for_unknown_actor(tmp_path: Path) -> None:
    async def exercise() -> None:
        server = _server(tmp_path)
        created = await server.call_tool(
            "campaign_change",
            {"action": "create", "data": {"name": "Unknown actor scope"}},
        )
        campaign_id = created.structured_content["id"]
        session_key = "legacy:unknown-actor"
        exposure = server.exposure_registry.open(
            session_key=session_key,
            principal_id="system:local",
            campaign_id=campaign_id,
            phase="lobby",
        )
        server.exposure_registry.set_tools(exposure, add=["character_query"])
        context = SimpleNamespace(
            protocol_version="2025-11-25",
            meta={},
            request=SimpleNamespace(headers={}),
            session=SimpleNamespace(
                _connection=SimpleNamespace(session_id=session_key),
            ),
        )

        result = await server._handle_call_tool(
            context,
            CallToolRequestParams(
                name="character_query",
                arguments={
                    "action": "get",
                    "campaign_id": campaign_id,
                    "character_id": "missing-actor",
                },
            ),
        )
        assert result.is_error is True
        assert result.structured_content == {
            "error": {
                "code": "not_found",
                "message": "actor target was not found in the exposure campaign",
                "retryable": False,
                "recovery": (
                    "List or query the relevant authorized records and retry with an "
                    "existing identifier."
                ),
            }
        }

    asyncio.run(exercise())
