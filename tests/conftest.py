import sys
import types
import asyncio
import pytest


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=''):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    async def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeAsyncClient:
    def __init__(self, responses=None):
        self._responses = list(responses or [])
        self._requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None, headers=None, timeout=None):
        self._requests.append(('get', url, params, headers))
        return self._responses.pop(0) if self._responses else FakeResponse()

    async def post(self, url, json=None, data=None, headers=None, timeout=None):
        self._requests.append(('post', url, json, headers))
        return self._responses.pop(0) if self._responses else FakeResponse()


@pytest.fixture(autouse=True)
def fake_fastmcp(monkeypatch):
    """Insert a stub `fastmcp` module to avoid import-time side effects."""
    mod = types.ModuleType('fastmcp')

    class FastMCP:
        def __init__(self, *args, **kwargs):
            pass

        def register_all_tools(self):
            return None

    mod.FastMCP = FastMCP  # type: ignore[attr-defined]
    sys.modules['fastmcp'] = mod
    # Ensure an event loop exists for tests that call asyncio.get_event_loop()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield
    finally:
        try:
            loop.close()
        except Exception:
            pass
        sys.modules.pop('fastmcp', None)


@pytest.fixture
def fake_httpx_client(monkeypatch):
    """Patch `httpx.AsyncClient` with a fake async client factory.

    Use by calling the returned factory with an optional list of FakeResponse
    instances, e.g. `client_factory([FakeResponse(json_data={...})])`.
    """

    def factory(responses=None):
        return FakeAsyncClient(responses=responses)

    monkeypatch.setattr('httpx.AsyncClient', FakeAsyncClient)
    return factory
