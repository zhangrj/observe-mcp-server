import os

from observe_mcp_server import server as srv


def test_register_all_tools_calls_expected(monkeypatch):
    called = {"open": False, "prom": False, "sky": False}

    def ro(mcp, logger, tool_prefix=""):
        called["open"] = True

    def rp(mcp, logger, tool_prefix=""):
        called["prom"] = True

    def rs(mcp, logger, tool_prefix=""):
        called["sky"] = True

    monkeypatch.setattr(srv, "register_openobserve_tools", ro)
    monkeypatch.setattr(srv, "register_prometheus_tools", rp)
    monkeypatch.setattr(srv, "register_skywalking_tools", rs)

    # ensure env enables skywalking for this test
    monkeypatch.setenv("OBSERVE_ENABLE_SKYWALKING", "true")
    # call register_all_tools
    srv.register_all_tools()

    assert called["open"] is True
    assert called["prom"] is True
    assert called["sky"] is True
