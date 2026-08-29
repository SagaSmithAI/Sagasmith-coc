from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters
from sagasmith_core.auth_context import (
    AUTH_CONTEXT_META_KEY,
    sign_auth_context,
    sign_delegated_auth_context,
)

from sagasmith_coc_mcp.config import McpConfig
from sagasmith_coc_mcp.server import create_server

AUTH_CONTEXT_SECRET = "transport-identity-secret-with-at-least-32-bytes"
SERVICE = "sagasmith-coc-mcp"


def _unused_loopback_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _wait_for_port(port: int, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(
                f"CoC MCP exited before startup ({process.returncode}):\n{stdout}\n{stderr}"
            )
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return
        except OSError:
            time.sleep(0.1)
    raise AssertionError("CoC MCP streamable HTTP endpoint did not start")


def _environment(
    tmp_path: Path,
    *,
    transport: str,
    port: int | None = None,
    authenticated: bool = False,
) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "SAGASMITH_COC_MCP_TRANSPORT": transport,
            "SAGASMITH_COC_MCP_HOME": str(tmp_path / f"home-{transport}"),
            "SAGASMITH_COC_SKILLS_DIR": str(tmp_path / "coc-skills"),
            "SAGASMITH_MODULEGEN_SKILLS_DIR": str(tmp_path / "modulegen-skills"),
        }
    )
    if port is not None:
        environment.update(
            {
                "SAGASMITH_COC_MCP_HTTP_HOST": "127.0.0.1",
                "SAGASMITH_COC_MCP_HTTP_PORT": str(port),
            }
        )
    if authenticated:
        environment["SAGASMITH_AUTH_CONTEXT_SECRET"] = AUTH_CONTEXT_SECRET
    return environment


async def _seed_identity_campaigns(tmp_path: Path, transport: str) -> tuple[str, str]:
    server = create_server(
        McpConfig(
            home=tmp_path / f"home-{transport}",
            database_url=None,
            coc_skills_dir=tmp_path / "coc-skills",
            modulegen_skills_dir=tmp_path / "modulegen-skills",
        )
    )
    allowed = await server.call_tool(
        "campaign_change",
        {
            "action": "create",
            "principal_id": "discord:user:owner",
            "data": {
                "name": "Transport requester case",
                "idempotency_key": f"transport-allowed-{transport}",
            },
        },
    )
    assert not allowed.is_error
    allowed_id = allowed.structured_content["id"]
    granted = await server.call_tool(
        "campaign_change",
        {
            "action": "grant_campaign",
            "campaign_id": allowed_id,
            "principal_id": "discord:user:owner",
            "data": {
                "target_principal_id": "discord:user:player",
                "role": "player",
            },
        },
    )
    assert not granted.is_error
    denied = await server.call_tool(
        "campaign_change",
        {
            "action": "create",
            "principal_id": "discord:user:owner",
            "data": {
                "name": "Transport owner-only case",
                "idempotency_key": f"transport-denied-{transport}",
            },
        },
    )
    assert not denied.is_error
    return allowed_id, denied.structured_content["id"]


def _identity_meta(mode: str, *, campaign_id: str, nonce: str) -> dict[str, object]:
    if mode == "2026-07-28":
        envelope = sign_delegated_auth_context(
            secret=AUTH_CONTEXT_SECRET,
            issuer="sagasmith-web",
            target_service=SERVICE,
            caller_principal="workload:sagasmith-agent",
            workload_identity="deployment:sagasmith-agent/test",
            requester_principal="discord:user:player",
            resource_owner_principal="discord:user:owner",
            acting_host_principal="workload:sagasmith-agent",
            acting_character_id="character:investigator",
            authorized_audience=SERVICE,
            allowed_operations=["campaign_query"],
            conversation_principal="discord:room:transport",
            campaign_id=campaign_id,
            room_turn_id=f"turn:{nonce}",
            base_revision=0,
            nonce=nonce,
        )
    else:
        envelope = sign_auth_context(
            secret=AUTH_CONTEXT_SECRET,
            host="test-host",
            channel="discord",
            actor_principal="discord:user:player",
            conversation_principal="discord:room:transport",
            campaign_id=campaign_id,
            session_id=f"session:{nonce}",
            nonce=nonce,
        )
    return {AUTH_CONTEXT_META_KEY: envelope}


async def _assert_identity_contract(
    client: Client,
    mode: str,
    *,
    allowed_campaign_id: str,
    denied_campaign_id: str,
) -> None:
    supplied_principal = (
        "discord:user:owner" if mode == "2026-07-28" else "discord:user:player"
    )
    accepted = await client.call_tool(
        "campaign_query",
        {
            "action": "get",
            "campaign_id": allowed_campaign_id,
            "principal_id": supplied_principal,
        },
        meta=_identity_meta(mode, campaign_id=allowed_campaign_id, nonce=f"accepted-{mode}"),
    )
    assert not accepted.is_error
    receipt = accepted.content[0].meta["sagasmith_auth_context_receipt"]
    if mode == "2026-07-28":
        assert receipt["requester_principal"] == "discord:user:player"
        assert receipt["resource_owner_principal"] == "discord:user:owner"
        assert receipt["acting_host_principal"] == "workload:sagasmith-agent"
        denied = await client.call_tool(
            "campaign_query",
            {
                "action": "get",
                "campaign_id": denied_campaign_id,
                "principal_id": "discord:user:owner",
            },
            meta=_identity_meta(
                mode,
                campaign_id=denied_campaign_id,
                nonce=f"denied-{mode}",
            ),
        )
        assert denied.is_error
        assert "cannot access campaign" in denied.content[0].text
    else:
        assert receipt["actor_principal"] == "discord:user:player"
        forged = await client.call_tool(
            "campaign_query",
            {
                "action": "get",
                "campaign_id": allowed_campaign_id,
                "principal_id": "discord:user:owner",
            },
            meta=_identity_meta(
                mode,
                campaign_id=allowed_campaign_id,
                nonce=f"forged-{mode}",
            ),
        )
        assert forged.is_error
        assert "actor does not match" in forged.content[0].text


async def _assert_contract(client: Client, mode: str) -> None:
    catalog = await client.list_tools()
    names = [tool.name for tool in catalog.tools]
    assert names == sorted(names)
    assert len(names) == (52 if mode == "2026-07-28" else 7)
    assert all(tool.description for tool in catalog.tools)
    assert all(tool.output_schema for tool in catalog.tools)

    result = await client.call_tool("campaign_query", {"action": "list", "limit": 1})
    assert result.is_error is False
    assert result.structured_content == {
        "campaigns": [],
        "next_cursor": None,
        "has_more": False,
    }

    invalid = await client.call_tool("campaign_query", {"action": "unsupported"})
    assert invalid.is_error is True
    assert invalid.structured_content["error"]["code"] == "invalid_argument"


@pytest.mark.parametrize("mode", ["legacy", "2026-07-28"])
def test_stdio_legacy_modern_contract_parity(tmp_path: Path, mode: str) -> None:
    async def exercise() -> None:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "sagasmith_coc_mcp.server"],
            env=_environment(tmp_path, transport="stdio"),
        )
        async with Client(parameters, mode=mode) as client:
            await _assert_contract(client, mode)

    asyncio.run(exercise())


@pytest.mark.parametrize("mode", ["legacy", "2026-07-28"])
def test_streamable_http_legacy_modern_contract_parity(tmp_path: Path, mode: str) -> None:
    port = _unused_loopback_port()
    process = subprocess.Popen(
        [sys.executable, "-m", "sagasmith_coc_mcp.server"],
        env=_environment(tmp_path, transport="streamable-http", port=port),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_port(port, process)

        async def exercise() -> None:
            async with Client(f"http://127.0.0.1:{port}/mcp", mode=mode) as client:
                await _assert_contract(client, mode)

        asyncio.run(exercise())
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@pytest.mark.parametrize("mode", ["legacy", "2026-07-28"])
@pytest.mark.parametrize("transport", ["stdio", "streamable-http"])
def test_transport_identity_attribution_and_legacy_compatibility(
    tmp_path: Path,
    mode: str,
    transport: str,
) -> None:
    allowed_campaign_id, denied_campaign_id = asyncio.run(
        _seed_identity_campaigns(tmp_path, transport)
    )

    async def exercise(client: Client) -> None:
        await _assert_identity_contract(
            client,
            mode,
            allowed_campaign_id=allowed_campaign_id,
            denied_campaign_id=denied_campaign_id,
        )

    if transport == "stdio":
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "sagasmith_coc_mcp.server"],
            env=_environment(tmp_path, transport=transport, authenticated=True),
        )

        async def run_stdio() -> None:
            async with Client(parameters, mode=mode) as client:
                await exercise(client)

        asyncio.run(run_stdio())
        return

    port = _unused_loopback_port()
    process = subprocess.Popen(
        [sys.executable, "-m", "sagasmith_coc_mcp.server"],
        env=_environment(
            tmp_path,
            transport=transport,
            port=port,
            authenticated=True,
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_port(port, process)

        async def run_http() -> None:
            async with Client(f"http://127.0.0.1:{port}/mcp", mode=mode) as client:
                await exercise(client)

        asyncio.run(run_http())
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
