import pytest
import asyncio

from observe_mcp_server.tools import openobserve as oo_tools


class FakeBackend:
    def __init__(self, settings):
        pass

    async def field_values(self, **kwargs):
        return {
            "took": 1,
            "hits": [
                {"field": "service_name", "values": [{"zo_sql_key": "svc", "zo_sql_num": 10}]}
            ],
            "total": 1,
            "from": 0,
            "size": 1,
            "scan_size": 0,
        }

    async def list_stream_schema(self, stream, stream_type):
        return {"schema": [{"name": "service_name"}, {"name": "status_code"}, {"name": "message"}]}


def test_openobserve_field_values_calls_backend(monkeypatch):
    monkeypatch.setattr(oo_tools, "OpenObserveBackend", lambda settings: FakeBackend(settings))

    # Register tools into a dummy MCP to extract the tool functions
    class DummyMCP:
        def __init__(self):
            self.tools = {}

        def tool(self, **kwargs):
            name = kwargs.get("name")

            def decorator(func):
                self.tools[name] = func
                return func

            return decorator

    class DummyLogger:
        def bind(self, **kwargs):
            return self

        def info(self, *a, **k):
            pass

        def error(self, *a, **k):
            pass

        def debug(self, *a, **k):
            pass

    dmcp = DummyMCP()
    logger = DummyLogger()
    oo_tools.register_openobserve_tools(dmcp, logger, tool_prefix="")

    func = dmcp.tools.get("openobserve_field_values")
    assert func is not None

    res = asyncio.run(func(
        stream="s",
        fields="service_name",
        start_time_us=1,
        end_time_us=2,
        size=5,
    ))

    assert isinstance(res, dict)
    assert "data" in res
    assert isinstance(res["data"], dict)
    assert "hits" in res["data"]


def test_openobserve_sql_lint_detects_issues(monkeypatch):
    monkeypatch.setattr(oo_tools, "OpenObserveBackend", lambda settings: FakeBackend(settings))

    dmcp = type("DM", (), {})()
    # reuse DummyMCP pattern to register and extract the lint tool
    class DummyMCP:
        def __init__(self):
            self.tools = {}

        def tool(self, **kwargs):
            name = kwargs.get("name")

            def decorator(func):
                self.tools[name] = func
                return func

            return decorator

    class DummyLogger:
        def bind(self, **kwargs):
            return self

        def info(self, *a, **k):
            pass

        def error(self, *a, **k):
            pass

        def debug(self, *a, **k):
            pass

    dmcp = DummyMCP()
    logger = DummyLogger()
    oo_tools.register_openobserve_tools(dmcp, logger, tool_prefix="")

    lint_func = dmcp.tools.get("openobserve_sql_lint")
    assert lint_func is not None

    res = asyncio.run(lint_func(
        stream="s",
        sql="SELECT * FROM s",
        start_time_us=None,
        end_time_us=None,
    ))

    assert res["valid"] is False
    assert any("Missing time window" in m for m in res["messages"]) or any("time window" in m for m in res["messages"]) 
    assert any("Avoid SELECT *" in m or "Avoid SELECT *" in m for m in res["messages"]) or "suggested_sql" in res
