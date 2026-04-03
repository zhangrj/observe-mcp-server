from __future__ import annotations

import asyncio

import pytest
from pydantic import AnyHttpUrl

from observe_mcp_server.backends.prometheus import PrometheusBackend
from observe_mcp_server.settings import PrometheusSettings


class _FakeResponse:
    def __init__(self, status_code: int, json_obj: dict):
        self.status_code = status_code
        self._json = json_obj

    def json(self):
        return self._json

    @property
    def text(self):
        return str(self._json)


class _FakeAsyncClient:
    def __init__(self, routes):
        self._routes = routes

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        # match by path suffix
        for path, resp in self._routes.items():
            if url.endswith(path):
                return _FakeResponse(200, resp)
        return _FakeResponse(404, {"status": "error"})


def test_list_metrics_and_query(monkeypatch):
    settings = PrometheusSettings(url=AnyHttpUrl("http://prom.example"))

    routes = {
        "/api/v1/label/__name__/values": {"status": "success", "data": ["metric_a", "metric_b"]},
        "/api/v1/query": {"status": "success", "data": {"resultType": "vector", "result": []}},
    }

    async def fake_asyncclient(*args, **kwargs):
        return _FakeAsyncClient(routes)

    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: _FakeAsyncClient(routes))

    backend = PrometheusBackend(settings)

    loop = asyncio.get_event_loop()
    metrics = loop.run_until_complete(backend.list_metrics())
    assert "metric_a" in metrics

    resp = loop.run_until_complete(backend.query_instant("up"))
    assert resp.get("status") == "success"
