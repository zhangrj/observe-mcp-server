from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from ..settings import SkyWalkingSettings


class SkyWalkingBackend:
    """Lightweight GraphQL client for SkyWalking OAP (minimal wrapper)."""

    def __init__(self, settings: SkyWalkingSettings):
        self.settings = settings

    def _url(self) -> str:
        base = str(self.settings.base_url).rstrip("/")
        # assume GraphQL endpoint is provided as base_url (may include /graphql)
        return base

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.settings.token:
            try:
                token = self.settings.token.get_secret_value()  # type: ignore
            except Exception:
                token = str(self.settings.token)
            if token:
                h["Authorization"] = f"Bearer {token}"
        return h

    async def _post_graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"query": query}
        if variables is not None:
            payload["variables"] = variables

        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
            resp = await client.post(self._url(), json=payload, headers=self._headers())
            if resp.status_code >= 400:
                text = (resp.text or "")[:1000]
                raise RuntimeError(f"SkyWalking GraphQL request failed: HTTP {resp.status_code}: {text}")
            data = resp.json()
            if "errors" in data:
                raise RuntimeError(f"SkyWalking GraphQL errors: {data['errors']}")
            return data.get("data", {})

    async def list_layers(self) -> Dict[str, Any]:
        query = """
        query ListLayers { listLayers { id name } }
        """
        return await self._post_graphql(query)

    async def list_services(self, layer: Optional[str] = None) -> Dict[str, Any]:
        query = """
        query ListServices($layer: String) { listServices(layer: $layer) { id name } }
        """
        vars = {"layer": layer} if layer else None
        return await self._post_graphql(query, variables=vars)

    async def list_instances(self, service_id: str, keyword: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        query = """
        query ListInstances($serviceId: ID!, $keyword: String, $limit: Int) { listInstances(serviceId: $serviceId, keyword: $keyword, limit: $limit) { id name } }
        """
        vars = {"serviceId": service_id, "keyword": keyword, "limit": limit}
        return await self._post_graphql(query, variables=vars)

    async def list_endpoints(self, service_id: str, keyword: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        query = """
        query ListEndpoints($serviceId: ID!, $keyword: String, $limit: Int) { searchEndpoints(serviceId: $serviceId, keyword: $keyword, limit: $limit) { id name } }
        """
        vars = {"serviceId": service_id, "keyword": keyword, "limit": limit}
        return await self._post_graphql(query, variables=vars)

    async def list_processes(self, service_id: str, keyword: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        query = """
        query ListProcesses($serviceId: ID!, $keyword: String, $limit: Int) { searchProcesses(serviceId: $serviceId, keyword: $keyword, limit: $limit) { id name } }
        """
        vars = {"serviceId": service_id, "keyword": keyword, "limit": limit}
        return await self._post_graphql(query, variables=vars)

    async def query_traces(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a trace query request (shape follows SkyWalking GraphQL API).

        The `request` is passed as GraphQL variables. This wrapper accepts a dict and forwards it.
        """
        query = """
        query QueryTraces($req: TracesQueryRequest) { queryTraces(condition: $req) { total results { traceId spans } } }
        """
        vars = {"req": request}
        return await self._post_graphql(query, variables=vars)

    async def get_trace_detail(self, trace_id: str) -> Dict[str, Any]:
        query = """
        query GetTrace($traceId: ID!) { trace(traceId: $traceId) { traceId spans } }
        """
        vars = {"traceId": trace_id}
        return await self._post_graphql(query, variables=vars)
