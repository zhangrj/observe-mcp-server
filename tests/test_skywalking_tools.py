import asyncio

from observe_mcp_server.tools import skywalking as sw_tools


class FakeBackend:
    def __init__(self, settings):
        pass

    async def list_layers(self):
        return {"listLayers": [{"id": "L1", "name": "HTTP"}]}

    async def list_services(self, layer=None):
        return {"listServices": [{"id": "S1", "name": "usersvc"}]}

    async def query_traces(self, request):
        return {"queryTraces": {"total": 1, "results": [{"traceId": "t1", "spans": []}]}}

    async def get_trace_detail(self, trace_id: str, start: str, end: str, step: str):
        return {"trace": {"traceId": trace_id, "spans": []}}


def test_list_layers_and_query_traces(monkeypatch):
    # Patch the backend factory used in tools to return FakeBackend
    monkeypatch.setattr(sw_tools, "SkyWalkingBackend", lambda settings: FakeBackend(settings))

    # Dummy MCP/register pattern to extract tool funcs
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
    sw_tools.register_skywalking_tools(dmcp, logger, tool_prefix="")

    list_layers_func = dmcp.tools.get("list_layers")
    assert list_layers_func is not None
    res = asyncio.run(list_layers_func())
    assert isinstance(res, dict)
    assert "data" in res

    query_func = dmcp.tools.get("query_traces")
    assert query_func is not None
    qres = asyncio.run(query_func({"serviceId": "S1", "start": "-1h", "end": "now"}))
    assert isinstance(qres, dict)
    assert "data" in qres

    detail_func = dmcp.tools.get("get_trace_detail")
    assert detail_func is not None
    # provide required duration params: step=HOUR and matching start/end formats
    dres = asyncio.run(detail_func("t1", "2017-11-08 09", "2017-11-08 19", "HOUR"))
    assert dres["data"]["trace"]["traceId"] == "t1"
