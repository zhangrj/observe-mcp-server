import asyncio

from pydantic import SecretStr
from pydantic import AnyHttpUrl

from observe_mcp_server.backends.prometheus import PrometheusBackend
from observe_mcp_server.settings import PrometheusSettings


def test_auth_header_token_and_basic():
    s_token = PrometheusSettings(url=AnyHttpUrl("http://prom"), token=SecretStr("t"))
    b = PrometheusBackend(s_token)
    h = b._auth_header()
    assert "Authorization" in h and h["Authorization"].startswith("Bearer")

    s_basic = PrometheusSettings(url=AnyHttpUrl("http://prom"), username="u", password=SecretStr("p"))
    b2 = PrometheusBackend(s_basic)
    h2 = b2._auth_header()
    assert "Authorization" in h2 and h2["Authorization"].startswith("Basic")


def test_list_metrics_and_query(monkeypatch):
    settings = PrometheusSettings(url=AnyHttpUrl("http://prom"))

    from tests.conftest import FakeResponse, FakeAsyncClient

    # list_metrics success
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(responses=[FakeResponse(status_code=200, json_data={"status": "success", "data": ["m1", "m2"]})]))
    backend = PrometheusBackend(settings)
    res = asyncio.run(backend.list_metrics())
    assert isinstance(res, list) and "m1" in res

    # list_metrics error
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(responses=[FakeResponse(status_code=500, json_data={"error": "x"}, text="oops")]))
    try:
        asyncio.run(backend.list_metrics())
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass

    # query_instant success
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(responses=[FakeResponse(status_code=200, json_data={"status": "success", "data": {}})]))
    qi = asyncio.run(backend.query_instant(query="up"))
    assert isinstance(qi, dict)
