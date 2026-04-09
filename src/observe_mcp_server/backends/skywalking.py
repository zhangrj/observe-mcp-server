from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from ..settings import SkyWalkingSettings


class SkyWalkingBackend:
    """GraphQL client for SkyWalking v9.0

    - Metadata: use V2 APIs only
    - Trace:
        - detect support via hasQueryTracesV2Support
        - use queryTraces (V2) if supported
        - otherwise use queryBasicTraces / queryTrace (V1)
    """

    def __init__(self, settings: SkyWalkingSettings):
        self.settings = settings
        self._trace_v2_supported: Optional[bool] = None

    def _url(self) -> str:
        base = str(self.settings.base_url).rstrip("/")
        return base

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
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

    @staticmethod
    def _build_duration(start: Optional[str], end: Optional[str], step: Optional[str]) -> Optional[Dict[str, Any]]:
        if start is None and end is None and step is None:
            return None
        if start is None or end is None or step is None:
            raise RuntimeError("start, end, step must be all provided together")
        return {"start": start, "end": end, "step": step}

    async def has_trace_v2_support(self) -> bool:
        if self._trace_v2_supported is not None:
            return self._trace_v2_supported

        query = """
        query HasTraceV2Support {
          hasQueryTracesV2Support
        }
        """
        try:
            data = await self._post_graphql(query)
            self._trace_v2_supported = bool(data.get("hasQueryTracesV2Support"))
        except Exception:
            self._trace_v2_supported = False

        return self._trace_v2_supported

    # ---------- Metadata V2 ----------

    async def list_layers(self) -> Dict[str, Any]:
        query = """
        query ListLayers {
          listLayers
        }
        """
        data = await self._post_graphql(query)
        raw = data.get("listLayers", [])

        # normalize to list of objects for downstream LLM/tool use
        if isinstance(raw, list):
            return {"listLayers": [{"id": v, "name": v} for v in raw]}
        return {"listLayers": []}

    async def list_services(self, layer: str) -> Dict[str, Any]:
        if not layer:
            raise RuntimeError("SkyWalking list_services requires a 'layer' argument")

        query = """
        query ListServices($layer: String) {
          listServices(layer: $layer) {
            id
            name
          }
        }
        """
        vars_ = {"layer": layer}
        return await self._post_graphql(query, variables=vars_)

    async def list_instances(self, start: str, end: str, step: str, service_id: str) -> Dict[str, Any]:
        query = """
        query ListInstances($duration: Duration!, $serviceId: ID!) {
          listInstances(duration: $duration, serviceId: $serviceId) {
            id
            name
          }
        }
        """
        vars_ = {
            "duration": {"start": start, "end": end, "step": step},
            "serviceId": service_id,
        }
        return await self._post_graphql(query, variables=vars_)

    async def list_endpoints(
        self,
        service_id: str,
        keyword: Optional[str] = None,
        limit: int = 100,
        start: Optional[str] = None,
        end: Optional[str] = None,
        step: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = """
        query FindEndpoints($keyword: String, $serviceId: ID!, $limit: Int!, $duration: Duration) {
          findEndpoint(keyword: $keyword, serviceId: $serviceId, limit: $limit, duration: $duration) {
            id
            name
          }
        }
        """
        duration = self._build_duration(start, end, step)
        vars_: Dict[str, Any] = {
            "serviceId": service_id,
            "keyword": keyword,
            "limit": limit,
            "duration": duration,
        }
        return await self._post_graphql(query, variables=vars_)

    async def list_processes(self, start: str, end: str, step: str, instance_id: str) -> Dict[str, Any]:
        query = """
        query ListProcesses($duration: Duration!, $instanceId: ID!) {
          listProcesses(duration: $duration, instanceId: $instanceId) {
            id
            name
          }
        }
        """
        vars_ = {
            "duration": {"start": start, "end": end, "step": step},
            "instanceId": instance_id,
        }
        return await self._post_graphql(query, variables=vars_)

    # ---------- Trace ----------

    async def query_traces(self, condition: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
        if await self.has_trace_v2_support():
            return await self._query_traces_v2(condition=condition, debug=debug)
        return await self._query_traces_v1(condition=condition, debug=debug)

    async def _query_traces_v1(self, condition: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
        query = """
        query QueryBasicTraces($condition: TraceQueryCondition, $debug: Boolean) {
          queryBasicTraces(condition: $condition, debug: $debug) {
            traces {
              segmentId
              endpointNames
              duration
              start
              isError
              traceIds
            }
          }
        }
        """
        vars_ = {"condition": condition, "debug": debug}
        return await self._post_graphql(query, variables=vars_)

    async def _query_traces_v2(self, condition: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
        query = """
        query QueryTraces($condition: TraceQueryCondition, $debug: Boolean) {
          queryTraces(condition: $condition, debug: $debug) {
            traces {
              spans {
                traceId
                segmentId
                spanId
                parentSpanId
                startTime
                endTime
                endpointName
                isError
              }
            }
            retrievedTimeRange {
              startTime
              endTime
            }
          }
        }
        """
        vars_ = {"condition": condition, "debug": debug}
        return await self._post_graphql(query, variables=vars_)

    async def get_trace_detail(
        self,
        trace_id: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        step: Optional[str] = None,
        debug: bool = False,
    ) -> Dict[str, Any]:
        duration = self._build_duration(start, end, step)

        query = """
        query GetTrace($traceId: ID!, $duration: Duration, $debug: Boolean) {
          queryTrace(traceId: $traceId, duration: $duration, debug: $debug) {
            spans {
              traceId
              segmentId
              spanId
              parentSpanId
              refs {
                traceId
                parentSegmentId
                parentSpanId
                type
              }
              serviceCode
              serviceInstanceName
              startTime
              endTime
              endpointName
              type
              peer
              component
              isError
              layer
              tags {
                key
                value
              }
              logs {
                time
                data {
                  key
                  value
                }
              }
              attachedEvents {
                startTime {
                  seconds
                  nanos
                }
                event
                endTime {
                  seconds
                  nanos
                }
                tags {
                  key
                  value
                }
                summary {
                  key
                  value
                }
              }
            }
          }
        }
        """
        vars_: Dict[str, Any] = {
            "traceId": trace_id,
            "duration": duration,
            "debug": debug,
        }
        return await self._post_graphql(query, variables=vars_)