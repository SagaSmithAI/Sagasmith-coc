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


def _environment(tmp_path: Path, *, transport: str, port: int | None = None) -> dict[str, str]:
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
    return environment


async def _assert_contract(client: Client, mode: str) -> None:
    catalog = await client.list_tools()
    names = [tool.name for tool in catalog.tools]
    assert names == sorted(names)
    assert len(names) == (51 if mode == "2026-07-28" else 7)
    assert all(tool.description for tool in catalog.tools)
    assert all(tool.output_schema for tool in catalog.tools)

    result = await client.call_tool("campaign_query", {"action": "list", "limit": 1})
    assert result.is_error is False
    assert result.structured_content == {"campaigns": [], "next_cursor": None}

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
