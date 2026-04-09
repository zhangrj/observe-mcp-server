import asyncio

from pydantic import SecretStr, AnyHttpUrl

from observe_mcp_server.backends.skywalking import SkyWalkingBackend
from observe_mcp_server.settings import SkyWalkingSettings


def test_headers_and_duration_build():
    s = SkyWalkingSettings(base_url=AnyHttpUrl("http://sw"), token=SecretStr("tk"))
    b = SkyWalkingBackend(s)
    h = b._headers()
    assert "Authorization" in h and h["Authorization"].startswith("Bearer")

    assert b._build_duration(None, None, None) is None
    try:
        b._build_duration("a", None, "HOUR")
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass


def test_post_graphql_and_list_layers(monkeypatch):
    s = SkyWalkingSettings(base_url=AnyHttpUrl("http://sw"))
    b = SkyWalkingBackend(s)

    from tests.conftest import FakeResponse, FakeAsyncClient

    # success data
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(responses=[FakeResponse(status_code=200, json_data={"data": {"listLayers": ["HTTP"]}})]))
    res = asyncio.run(b.list_layers())
    assert "listLayers" in res and isinstance(res["listLayers"], list)

    # graphql error payload
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(responses=[FakeResponse(status_code=200, json_data={"errors": ["bad"]})]))
    try:
        asyncio.run(b.list_layers())
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass

    # http error
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(responses=[FakeResponse(status_code=500, json_data={}, text="fail")]))
    try:
        asyncio.run(b.list_layers())
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass


def test_query_traces_v1_and_v2(monkeypatch):
    s = SkyWalkingSettings(base_url=AnyHttpUrl("http://sw"))
    b = SkyWalkingBackend(s)

    from tests.conftest import FakeResponse, FakeAsyncClient

    # First simulate no v2 support -> V1 path
    # has_trace_v2_support returns False
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(responses=[FakeResponse(status_code=200, json_data={"data": {"hasQueryTracesV2Support": False}}), FakeResponse(status_code=200, json_data={"data": {"queryBasicTraces": {"traces": []}}})]))
    res1 = asyncio.run(b.query_traces(condition={"traceId": "t1"}))
    assert isinstance(res1, dict)

    # Now simulate v2 supported -> V2 path
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(responses=[FakeResponse(status_code=200, json_data={"data": {"hasQueryTracesV2Support": True}}), FakeResponse(status_code=200, json_data={"data": {"queryTraces": {"traces": []}}})]))
    # reset cached flag
    b._trace_v2_supported = None
    res2 = asyncio.run(b.query_traces(condition={"traceId": "t1"}))
    assert isinstance(res2, dict)
