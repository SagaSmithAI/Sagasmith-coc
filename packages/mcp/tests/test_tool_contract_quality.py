from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolRequestParams

from sagasmith_coc_mcp.config import McpConfig
from sagasmith_coc_mcp.server import create_server


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
        assert len(tools) == 51
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
