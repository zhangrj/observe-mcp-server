import asyncio
from pydantic import AnyHttpUrl, SecretStr

from observe_mcp_server.backends.openobserve import OpenObserveBackend
from observe_mcp_server.settings import OpenObserveSettings
from observe_mcp_server.models import StreamType


def test_list_streams_and_field_values(monkeypatch):
    settings = OpenObserveSettings(base_url=AnyHttpUrl("http://oo"), org="o", username="u", password=SecretStr("p"))

    # success response for list_streams
    good = {"list": [{"name": "s1"}]}

    from tests.conftest import FakeResponse, FakeAsyncClient

    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda *a, **k: FakeAsyncClient(responses=[FakeResponse(status_code=200, json_data=good)]) ,
    )

    backend = OpenObserveBackend(settings)
    res = asyncio.run(backend.list_streams(StreamType.logs, fetch_schema=False))
    assert isinstance(res, dict)

    # error response
    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda *a, **k: FakeAsyncClient(responses=[FakeResponse(status_code=500, json_data={"err":"x"}, text="oops")]),
    )

    try:
        asyncio.run(backend.list_streams(StreamType.logs, fetch_schema=False))
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass

    # field_values success
    vals = {"values": [{"a": 1}]}
    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda *a, **k: FakeAsyncClient(responses=[FakeResponse(status_code=200, json_data=vals)]),
    )
    fv = asyncio.run(backend.field_values(stream="s1", fields="a"))
    assert isinstance(fv, dict)
