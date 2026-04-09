import asyncio
import json
import tempfile

from pydantic import AnyHttpUrl

from observe_mcp_server.tools import prometheus as p_tools


class FakeBackend2:
    def __init__(self, settings):
        pass

    async def series_for_metric(self, metric_name):
        return [{"__name__": metric_name, "lbl": "v1"}, {"__name__": metric_name, "lbl": "v2"}]

    async def label_values(self, label):
        # simulate failure for label_values to trigger fallback in search_label_values
        raise RuntimeError("no label_values")


def test_search_label_values_fallback(monkeypatch):
    monkeypatch.setattr(p_tools, "PrometheusBackend", lambda settings: FakeBackend2(settings))

    class DummyMCP:
        def __init__(self):
            self.tools = {}

        def tool(self, **kwargs):
            name = kwargs.get("name")

            def decorator(func):
                self.tools[name] = func
                return func

            return decorator

    dmcp = DummyMCP()
    logger = type("L", (), {"bind": lambda *a, **k: type("LL", (), {"info": lambda *a, **k: None, "error": lambda *a, **k: None})()})()
    p_tools.register_prometheus_tools(dmcp, logger, tool_prefix="")

    search = dmcp.tools.get("search_label_values")
    assert search is not None
    res = asyncio.run(search(metric_name="m", label_name="lbl", limit=10))
    assert "preview" in res
    assert isinstance(res["preview"], list)


def test_resolve_alias_reads_file(monkeypatch):
    # create temporary alias json
    aliases = {"错误率": {"promql": "sum(rate(errors[5m]))"}}
    tf = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
    tf.write(json.dumps(aliases))
    tf.flush()
    tf.close()

    # monkeypatch PrometheusSettings used inside tools to return a settings object with alias_path
    class FakeSettings:
        alias_path = tf.name
        alias_ttl_seconds = 1
        catalog_ttl_seconds = 1
        schema_ttl_seconds = 1

    monkeypatch.setattr(p_tools, "PrometheusSettings", lambda: FakeSettings())

    class DummyMCP:
        def __init__(self):
            self.tools = {}

        def tool(self, **kwargs):
            name = kwargs.get("name")

            def decorator(func):
                self.tools[name] = func
                return func

            return decorator

    dmcp = DummyMCP()
    logger = type("L", (), {"bind": lambda *a, **k: type("LL", (), {"info": lambda *a, **k: None, "error": lambda *a, **k: None})()})()
    p_tools.register_prometheus_tools(dmcp, logger, tool_prefix="")

    resolve = dmcp.tools.get("resolve_alias")
    assert resolve is not None
    r = asyncio.run(resolve("错误率"))
    assert r.get("count", 0) >= 1
