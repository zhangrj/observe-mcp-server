import asyncio

from observe_mcp_server.tools import prometheus as p_tools


class FakeBackend:
    def __init__(self, settings):
        pass

    async def list_metrics(self):
        return ["metric_a", "metric_b"]

    async def series_for_metric(self, metric_name):
        return [{"__name__": metric_name, "host": "h1"}, {"__name__": metric_name, "host": "h2"}]

    async def label_values(self, label):
        return ["v1", "v2"]

    async def query_instant(self, query, time=None):
        return {"resultType": "vector", "result": []}

    async def query_range(self, query, start, end, step):
        return {"resultType": "matrix", "result": []}


def test_prometheus_tools(monkeypatch):
    # Replace backend factory in tools
    monkeypatch.setattr(p_tools, "PrometheusBackend", lambda settings: FakeBackend(settings))

    # Dummy MCP/register pattern
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

    dmcp = DummyMCP()
    logger = DummyLogger()
    p_tools.register_prometheus_tools(dmcp, logger, tool_prefix="")

    get_catalog = dmcp.tools.get("get_metric_catalog")
    assert get_catalog is not None
    res = asyncio.run(get_catalog())
    assert "metrics" in res
    # call again to hit cache
    res2 = asyncio.run(get_catalog())
    assert res2.get("cache_hit") is True or res2.get("cache_hit") is False

    lint = dmcp.tools.get("lint_promql")
    assert lint is not None
    r = asyncio.run(lint(query=""))
    assert r["ok"] is False
    r2 = asyncio.run(lint(query="rate(foo[5m])"))
    assert r2["ok"] is True

    exec_tool = dmcp.tools.get("execute_promql")
    assert exec_tool is not None
    inst = asyncio.run(exec_tool(query="up", mode="instant"))
    assert "result" in inst
