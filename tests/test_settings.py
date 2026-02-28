from __future__ import annotations

from observe_mcp_server.settings import MCPSettings
import pytest

def test_mcpsettings_reads_env(monkeypatch: "pytest.MonkeyPatch") -> None:
    monkeypatch.setenv("OBSERVE_MCP_TRANSPORT", "streamable-http")
    s = MCPSettings()
    assert s.transport == "streamable-http"
