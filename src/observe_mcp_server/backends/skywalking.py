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
        # Some SkyWalking versions return a list of strings for listLayers,
        # while others return objects. Request the scalar and normalize.
        query = """
        query ListLayers { listLayers }
        """
        data = await self._post_graphql(query)
        if not data:
            return {"listLayers": []}
        raw = data.get("listLayers")
        if isinstance(raw, list) and raw and isinstance(raw[0], str):
            # normalize to list of objects with id/name for downstream tools
            normalized = [{"id": v, "name": v} for v in raw]
            return {"listLayers": normalized}
        return data

    async def list_services(self, layer: Optional[str] = None) -> Dict[str, Any]:
        # SkyWalking's listServices often requires a non-null layer argument (String!).
        if not layer:
            raise RuntimeError("SkyWalking list_services requires a 'layer' argument")
        query = """
        query ListServices($layer: String!) { listServices(layer: $layer) { id name } }
        """
        vars = {"layer": layer}
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
        """Send a trace query request using SkyWalking's TraceQueryCondition GraphQL input type.

        The `request` dict will be forwarded as the GraphQL variable named `condition`.
        """
        query = """
        query QueryTraces($condition: TraceQueryCondition) { queryTraces(condition: $condition) { total results { traceId spans } } }
        """
        vars = {"condition": request}
        return await self._post_graphql(query, variables=vars)

    async def get_trace_detail(self, trace_id: str) -> Dict[str, Any]:
        query = """
        query GetTrace($traceId: ID!) { trace(traceId: $traceId) { traceId spans } }
        """
        vars = {"traceId": trace_id}
        return await self._post_graphql(query, variables=vars)
