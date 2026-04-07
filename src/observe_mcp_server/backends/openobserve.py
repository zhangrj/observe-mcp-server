from __future__ import annotations

import base64
from typing import Any, Dict, Optional

import httpx

from ..settings import OpenObserveSettings
from ..models import StreamType


class OpenObserveBackend:
    """HTTP client wrapper for OpenObserve APIs (Basic Auth)."""

    def __init__(self, settings: OpenObserveSettings):
        self.settings = settings

    def _url(self, path: str) -> str:
        base = str(self.settings.base_url).rstrip("/")
        return f"{base}{path}"

    def _auth_header(self) -> Dict[str, str]:
        raw = f"{self.settings.username}:{self.settings.password.get_secret_value()}".encode("utf-8")
        token = base64.b64encode(raw).decode("ascii")
        # OpenObserve uses HTTP Basic Authentication.
        return {"Authorization": f"Basic {token}"}

    async def list_streams(self, stream_type: StreamType, fetch_schema: bool) -> Dict[str, Any]:
        # GET /api/{organization}/streams?fetchSchema=false&type={StreamType} [1](https://openobserve.ai/docs/api/stream/list/)
        url = self._url(f"/api/{self.settings.org}/streams")
        params = {
            "fetchSchema": "true" if fetch_schema else "false",
            "type": stream_type.value,
        }

        async with httpx.AsyncClient(
            timeout=self.settings.timeout_seconds,
            verify=self.settings.verify_ssl,
            headers={**self._auth_header(), "Accept": "application/json"},
        ) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                text = (resp.text or "")[:1000]
                raise RuntimeError(f"OpenObserve list_streams failed: HTTP {resp.status_code}: {text}")
            return resp.json()

    async def search(self, body: Dict[str, Any]) -> Dict[str, Any]:
        # POST /api/{organization}/_search [2](https://openobserve.ai/docs/api/search/search/)
        url = self._url(f"/api/{self.settings.org}/_search")

        async with httpx.AsyncClient(
            timeout=self.settings.timeout_seconds,
            verify=self.settings.verify_ssl,
            headers={**self._auth_header(), "Content-Type": "application/json", "Accept": "application/json"},
        ) as client:
            resp = await client.post(url, json=body)
            if resp.status_code >= 400:
                text = (resp.text or "")[:1200]
                raise RuntimeError(f"OpenObserve search failed: HTTP {resp.status_code}: {text}")
            return resp.json()
        
    async def list_stream_schema(self, stream_name: str, stream_type: StreamType) -> Dict[str, Any]:
        # GET /api/{organization}/streams/{streamName}/schema?type={StreamType} [3](https://openobserve.ai/docs/api/stream/schema/)
        url = self._url(f"/api/{self.settings.org}/streams/{stream_name}/schema")
        params = {"type": stream_type.value}

        async with httpx.AsyncClient(
            timeout=self.settings.timeout_seconds,
            verify=self.settings.verify_ssl,
            headers={**self._auth_header(), "Accept": "application/json"},
        ) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                text = (resp.text or "")[:1000]
                raise RuntimeError(f"OpenObserve list_stream_schema failed: HTTP {resp.status_code}: {text}")
            return resp.json()

    async def field_values(
        self,
        stream: str,
        fields: str,
        start_time: int = 0,
        end_time: int = 0,
        size: int = 10,
        keyword: Optional[str] = None,
        no_count: bool = False,
    ) -> Dict[str, Any]:
        """
        GET /api/{organization}/{stream}/_values

        Params: fields (comma separated), start_time (us), end_time (us), size, keyword, no_count
        """
        url = self._url(f"/api/{self.settings.org}/{stream}/_values")
        params: Dict[str, Any] = {
            "fields": fields,
            "start_time": start_time,
            "end_time": end_time,
            "size": size,
            "no_count": "true" if no_count else "false",
        }
        if keyword is not None:
            params["keyword"] = keyword

        async with httpx.AsyncClient(
            timeout=self.settings.timeout_seconds,
            verify=self.settings.verify_ssl,
            headers={**self._auth_header(), "Accept": "application/json"},
        ) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                text = (resp.text or "")[:1000]
                raise RuntimeError(f"OpenObserve field_values failed: HTTP {resp.status_code}: {text}")
            return resp.json()