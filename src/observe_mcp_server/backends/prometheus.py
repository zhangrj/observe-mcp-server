from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import httpx

from ..settings import PrometheusSettings


class PrometheusBackend:
    """Lightweight Prometheus HTTP client wrapper."""

    def __init__(self, settings: PrometheusSettings):
        self.settings = settings

    def _url(self, path: str) -> str:
        base = str(self.settings.url).rstrip("/")
        return f"{base}{path}"

    def _auth_header(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.settings.token:
            headers["Authorization"] = f"Bearer {self.settings.token.get_secret_value()}"
        elif self.settings.username and self.settings.password:
            # Basic auth via header
            import base64

            raw = f"{self.settings.username}:{self.settings.password.get_secret_value()}".encode("utf-8")
            token = base64.b64encode(raw).decode("ascii")
            headers["Authorization"] = f"Basic {token}"
        return headers

    async def list_metrics(self) -> List[str]:
        """Return list of metric names via /api/v1/label/__name__/values."""
        url = self._url("/api/v1/label/__name__/values")
        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds, verify=self.settings.verify_ssl,
                                     headers={**self._auth_header(), "Accept": "application/json"}) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                text = (resp.text or "")[:1000]
                raise RuntimeError(f"Prometheus list_metrics failed: HTTP {resp.status_code}: {text}")
            payload = resp.json()
            # expected: {status: "success", data: ["metric_a", ...]}
            return payload.get("data") or []

    async def series_for_metric(self, metric_name: str, start: Optional[float] = None, end: Optional[float] = None,
                                limit: int = 100) -> List[Dict[str, Any]]:
        """Query /api/v1/series?match[]=<metric>{...} to get series instances (used to infer labels).

        start/end are unix seconds; Prometheus API accepts RFC3339 or unix timestamps.
        """
        url = self._url("/api/v1/series")
        params: Dict[str, Any] = {"match[]": metric_name}
        if start is not None:
            params["start"] = str(int(start))
        if end is not None:
            params["end"] = str(int(end))

        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds, verify=self.settings.verify_ssl,
                                     headers={**self._auth_header(), "Accept": "application/json"}) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                text = (resp.text or "")[:1000]
                raise RuntimeError(f"Prometheus series_for_metric failed: HTTP {resp.status_code}: {text}")
            payload = resp.json()
            return payload.get("data") or []

    async def label_values(self, label_name: str, start: Optional[float] = None, end: Optional[float] = None) -> List[str]:
        """Return label values via /api/v1/label/<label_name>/values.

        Prometheus supports start/end parameters on this endpoint in newer versions.
        """
        url = self._url(f"/api/v1/label/{label_name}/values")
        params: Dict[str, Any] = {}
        if start is not None:
            params["start"] = str(int(start))
        if end is not None:
            params["end"] = str(int(end))

        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds, verify=self.settings.verify_ssl,
                                     headers={**self._auth_header(), "Accept": "application/json"}) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                text = (resp.text or "")[:1000]
                raise RuntimeError(f"Prometheus label_values failed: HTTP {resp.status_code}: {text}")
            payload = resp.json()
            return payload.get("data") or []

    async def query_instant(self, query: str, time: Optional[str] = None) -> Dict[str, Any]:
        url = self._url("/api/v1/query")
        params: Dict[str, Any] = {"query": query}
        if time:
            params["time"] = time

        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds, verify=self.settings.verify_ssl,
                                     headers={**self._auth_header(), "Accept": "application/json"}) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                text = (resp.text or "")[:1200]
                raise RuntimeError(f"Prometheus query_instant failed: HTTP {resp.status_code}: {text}")
            return resp.json()

    async def query_range(self, query: str, start: str, end: str, step: str) -> Dict[str, Any]:
        url = self._url("/api/v1/query_range")
        params = {"query": query, "start": start, "end": end, "step": step}
        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds, verify=self.settings.verify_ssl,
                                     headers={**self._auth_header(), "Accept": "application/json"}) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                text = (resp.text or "")[:1200]
                raise RuntimeError(f"Prometheus query_range failed: HTTP {resp.status_code}: {text}")
            return resp.json()
