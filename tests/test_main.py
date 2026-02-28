from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest
import observe_mcp_server.__main__ as mainmod


def test_main_uses_env_transport_when_no_cli(monkeypatch: "pytest.MonkeyPatch") -> None:
    monkeypatch.setenv("OBSERVE_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setattr(sys, "argv", ["observe-mcp-server"])

    called: dict = {}

    def fake_run(*_args, **kwargs):
        called.update(kwargs)

    monkeypatch.setattr(mainmod, "mcp", SimpleNamespace(run=fake_run))

    mainmod.main()

    assert called["transport"] == "streamable-http"


def test_main_prefers_cli_over_env(monkeypatch: "pytest.MonkeyPatch") -> None:
    monkeypatch.setenv("OBSERVE_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setattr(sys, "argv", ["observe-mcp-server", "--transport", "stdio"])

    called: dict = {}

    def fake_run(*_args, **kwargs):
        called.update(kwargs)

    monkeypatch.setattr(mainmod, "mcp", SimpleNamespace(run=fake_run))

    mainmod.main()

    assert called["transport"] == "stdio"
