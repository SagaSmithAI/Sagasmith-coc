from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer

from sagasmith_coc_mcp.config import McpConfig
from sagasmith_coc_mcp.gateway import CocMcpClient, GatewayConfig, create_app

AUTH_CONTEXT_SECRET = "test-auth-context-secret-with-at-least-32-bytes"


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


def test_real_streamable_http_and_sticky_gateway(tmp_path: Path) -> None:
    port = _unused_loopback_port()
    environment = os.environ.copy()
    environment.update(
        {
            "SAGASMITH_COC_MCP_TRANSPORT": "streamable-http",
            "SAGASMITH_COC_MCP_HTTP_HOST": "127.0.0.1",
            "SAGASMITH_COC_MCP_HTTP_PORT": str(port),
            "SAGASMITH_COC_MCP_HOME": str(tmp_path / "home"),
            "SAGASMITH_COC_SKILLS_DIR": str(tmp_path / "coc-skills"),
            "SAGASMITH_MODULEGEN_SKILLS_DIR": str(tmp_path / "modulegen-skills"),
        }
    )
    process = subprocess.Popen(
        [sys.executable, "-m", "sagasmith_coc_mcp.server"],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_port(port, process)

        async def exercise() -> None:
            mcp = CocMcpClient(f"http://127.0.0.1:{port}/mcp", "system:local")
            await mcp.start()
            try:
                capabilities = await mcp.call_tool("server_capabilities", {})
                assert capabilities.isError is not True
                capability_value = dict(capabilities.structuredContent or {})
                capability_value = dict(capability_value.get("result") or capability_value)
                contract = capability_value["authoritative_contract"]
                assert contract["schema"] == "sagasmith.authoritative-mcp/v1"
                assert contract["transports"] == ["stdio", "streamable-http"]
                assert contract["shared_handlers"] is True
                created = await mcp.call_tool(
                    "campaign_change",
                    {
                        "action": "create",
                        "data": {"name": "HTTP Investigation", "idempotency_key": "http-coc"},
                    },
                )
                assert created.isError is not True
            finally:
                await mcp.stop()

            ui = tmp_path / "ui"
            ui.mkdir()
            (ui / "index.html").write_text("<h1>CoC Workbench</h1>", encoding="utf-8")
            gateway = TestClient(
                TestServer(
                    create_app(
                        GatewayConfig(
                            mcp_url=f"http://127.0.0.1:{port}/mcp",
                            ui_dist=ui,
                        )
                    )
                )
            )
            await gateway.start_server()
            try:
                response = await gateway.post(
                    "/api/coc/mcp/tool",
                    json={"tool": "campaign_query", "arguments": {"action": "list"}},
                )
                assert response.status == 200
                assert (await response.json())["ok"] is True
                workbench = await gateway.get("/")
                assert "CoC Workbench" in await workbench.text()
            finally:
                await gateway.close()

        asyncio.run(exercise())
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def test_non_loopback_streamable_http_requires_auth_context_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sagasmith_coc_mcp import server

    monkeypatch.setenv("SAGASMITH_COC_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("SAGASMITH_COC_MCP_HTTP_HOST", "0.0.0.0")
    monkeypatch.delenv("SAGASMITH_AUTH_CONTEXT_SECRET", raising=False)
    monkeypatch.setattr(
        server,
        "create_server",
        lambda config: pytest.fail("the insecure HTTP server was created"),
    )

    with pytest.raises(ValueError, match="non-loopback.*SAGASMITH_AUTH_CONTEXT_SECRET"):
        server.main()


def test_non_loopback_streamable_http_accepts_signed_auth_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sagasmith_coc_mcp import server

    transports: list[str] = []
    auth_context_secrets: list[str | None] = []

    class StubServer:
        def run(self, *, transport: str) -> None:
            transports.append(transport)

    def create_stub(config: McpConfig) -> StubServer:
        auth_context_secrets.append(config.auth_context_secret)
        return StubServer()

    monkeypatch.setenv("SAGASMITH_COC_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("SAGASMITH_COC_MCP_HTTP_HOST", "0.0.0.0")
    monkeypatch.setenv("SAGASMITH_AUTH_CONTEXT_SECRET", AUTH_CONTEXT_SECRET)
    monkeypatch.setattr(server, "create_server", create_stub)

    server.main()

    assert transports == ["streamable-http"]
    assert auth_context_secrets == [AUTH_CONTEXT_SECRET]
