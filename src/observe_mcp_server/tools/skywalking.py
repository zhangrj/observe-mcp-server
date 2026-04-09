from __future__ import annotations

from typing import Any, Dict, Optional

from fastmcp.exceptions import ToolError, ValidationError
from pydantic import Field
from typing_extensions import Annotated

from ..backends.skywalking import SkyWalkingBackend
from ..settings import SkyWalkingSettings


def register_skywalking_tools(mcp, logger, tool_prefix: str = "") -> None:
    def tool_name(name: str) -> str:
        return f"{tool_prefix}{name}" if tool_prefix else name

    @mcp.tool(
        name=tool_name("list_layers"),
        description=(
            "[SkyWalking] List available layers registered in SkyWalking OAP.\n"
            "A layer represents a technology or deployment environment (for example: GENERAL, MESH, K8S, OS_LINUX).\n"
            "Use this tool as the first discovery step to identify which layer to query services from.\n\n"
            "Workflow:\n"
            "1. Call `list_layers` to obtain layer names.\n"
            "2. Use a selected layer with `list_services` to find service IDs.\n\n"
            "Example response:\n"
            "{" + '"listLayers": [{"id":"GENERAL","name":"GENERAL"}]' + "}"
        ),
        annotations={"title": "SkyWalking: List Layers", "readOnlyHint": True},
        tags={"skywalking", "metadata"},
        meta={"backend": "skywalking"},
    )
    async def list_layers() -> Dict[str, Any]:
        try:
            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.list_layers()
            return {"data": data}
        except Exception as e:
            logger.error("list_layers failed", error=str(e))
            raise ToolError(f"list_layers failed: {e}")

    @mcp.tool(
        name=tool_name("list_services"),
        description=(
            "[SkyWalking] List services in SkyWalking OAP for a given `layer`.\n"
            "A service is a logical application or component monitored by SkyWalking.\n\n"
            "Workflow:\n"
            "1. Call `list_layers` to discover available layers.\n"
            "2. Call `list_services` with a layer to obtain service objects containing `id` and `name`.\n\n"
            "Notes:\n"
            "- `layer` is required for this tool.\n"
            "- Use the returned `id` when calling `list_instances`, `list_endpoints` or trace queries.\n"
            "- Responses include `id` and `name` fields for programmatic use.\n\n"
            "Examples:\n"
            '- {"layer": "GENERAL"} — list services in GENERAL layer'
        ),
        annotations={"title": "SkyWalking: List Services", "readOnlyHint": True},
        tags={"skywalking", "metadata"},
        meta={"backend": "skywalking"},
    )
    async def list_services(
        layer: Annotated[str, Field(description="Layer name (required), e.g. GENERAL, MESH, K8S")]
    ) -> Dict[str, Any]:
        try:
            if not layer:
                raise ValidationError("layer is required")
            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.list_services(layer=layer)
            return {"data": data}
        except ValidationError:
            raise
        except Exception as e:
            logger.error("list_services failed", error=str(e))
            raise ToolError(f"list_services failed: {e}")

    @mcp.tool(
        name=tool_name("list_instances"),
        description=(
            "[SkyWalking] List service instances for a given `service_id`.\n"
            "A service instance represents a running process (e.g., a pod or JVM).\n\n"
            "Workflow:\n"
            "1. Use `list_services` to obtain a `service_id`.\n"
            "2. Call `list_instances` with that `service_id` and a duration defined by `start`, `end`, `step`.\n\n"
            "Duration:\n"
            "- `step` selects time precision and the required format for `start`/`end`:\n"
            "  - MONTH  -> yyyy-MM (e.g. 2017-11)\n"
            "  - DAY    -> yyyy-MM-dd (e.g. 2017-11-08)\n"
            "  - HOUR   -> yyyy-MM-dd HH (e.g. 2017-11-08 09)\n"
            "  - MINUTE -> yyyy-MM-dd HHmm (e.g. 2017-11-08 0930), use MINUTE preferentially\n"
            "  - SECOND -> yyyy-MM-dd HHmmss (e.g. 2017-11-08 093015)\n"
            "- `start` and `end` must match the chosen `step` format exactly.\n\n"
            "Parameters:\n"
            "- `service_id` (required): SkyWalking service ID.\n"
            "- `start`,`end`,`step` (required): duration fields as described above.\n\n"
            "Example:\n"
            '- {"service_id": "S1", "step": "MINUTE", "start": "2017-11-08 09", "end": "2017-11-08 19"}'
        ),
        annotations={"title": "SkyWalking: List Instances", "readOnlyHint": True},
        tags={"skywalking", "metadata"},
        meta={"backend": "skywalking"},
    )
    async def list_instances(
        start: Annotated[str, Field(description="Duration start string. Format depends on `step`: MONTH=yyyy-MM, DAY=yyyy-MM-dd, HOUR=yyyy-MM-dd HH, MINUTE=yyyy-MM-dd HHmm, SECOND=yyyy-MM-dd HHmmss")],
        end: Annotated[str, Field(description="Duration end string. Same format as `start` for the chosen `step`")],
        step: Annotated[str, Field(description="Duration step: one of MONTH, DAY, HOUR, MINUTE, SECOND. Controls start/end format and aggregation granularity")],
        service_id: Annotated[str, Field(description="Service ID")],
    ) -> Dict[str, Any]:
        try:
            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.list_instances(start=start, end=end, step=step, service_id=service_id)
            return {"data": data}
        except Exception as e:
            logger.error("list_instances failed", error=str(e))
            raise ToolError(f"list_instances failed: {e}")

    @mcp.tool(
        name=tool_name("list_endpoints"),
        description=(
            "[SkyWalking] Search or list endpoints (API paths) for a given `service_id`.\n"
            "Endpoints are useful to narrow trace queries to a specific operation.\n\n"
            "Workflow:\n"
            "1. Use `list_services` to get a `service_id`.\n"
            "2. Call `list_endpoints` with `service_id` and optional duration (`start`,`end`,`step`) to scope results.\n\n"
            "Duration: same `step`/format rules as `list_instances` (see list_instances).\n\n"
            "Parameters & examples:\n"
            '- {"service_id": "S1"} — list endpoints for service S1\n'
            '- {"service_id": "S1", "keyword": "/api/users", "step": "MINUTE", "start": "2023-01-01", "end": "2023-01-07"}'
        ),
        annotations={"title": "SkyWalking: List Endpoints", "readOnlyHint": True},
        tags={"skywalking", "metadata"},
        meta={"backend": "skywalking"},
    )
    async def list_endpoints(
        service_id: Annotated[str, Field(description="Service ID")],
        start: Annotated[Optional[str], Field(description="Optional duration start string. Format depends on `step`: MONTH=yyyy-MM, DAY=yyyy-MM-dd, HOUR=yyyy-MM-dd HH, MINUTE=yyyy-MM-dd HHmm, SECOND=yyyy-MM-dd HHmmss")] = None,
        end: Annotated[Optional[str], Field(description="Optional duration end string. Same format as `start` for the chosen `step`")] = None,
        step: Annotated[Optional[str], Field(description="Optional duration step (MONTH|DAY|HOUR|MINUTE|SECOND)")] = None,
        keyword: Annotated[Optional[str], Field(description="Optional search keyword")] = None,
        limit: Annotated[int, Field(description="Max results (default 100)")] = 100,
    ) -> Dict[str, Any]:
        try:
            if (start is None) ^ (end is None) or (start is None) ^ (step is None):
                raise ValidationError("start, end, step must be provided together, or all omitted")

            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.list_endpoints(
                service_id=service_id,
                keyword=keyword,
                limit=limit,
                start=start,
                end=end,
                step=step,
            )
            return {"data": data}
        except ValidationError:
            raise
        except Exception as e:
            logger.error("list_endpoints failed", error=str(e))
            raise ToolError(f"list_endpoints failed: {e}")

    @mcp.tool(
        name=tool_name("list_processes"),
        description=(
            "[SkyWalking] List processes associated with a service. Use after `list_instances` to select an instance.\n\n"
            "Workflow:\n"
            "1. Find `service_id` via `list_services`.\n"
            "2. Optionally call `list_instances` to find an `instance_id`.\n"
            "3. Call `list_processes` with `instance_id` and required duration (`start`,`end`,`step`) to retrieve process metadata.\n\n"
            "Duration: same `step`/format rules as `list_instances` (see list_instances).\n\n"
            "Notes: results include process id, agentId, labels and attributes useful for debugging."
        ),
        annotations={"title": "SkyWalking: List Processes", "readOnlyHint": True},
        tags={"skywalking", "metadata"},
        meta={"backend": "skywalking"},
    )
    async def list_processes(
        start: Annotated[str, Field(description="Duration start string. Format depends on `step`: MONTH=yyyy-MM, DAY=yyyy-MM-dd, HOUR=yyyy-MM-dd HH, MINUTE=yyyy-MM-dd HHmm, SECOND=yyyy-MM-dd HHmmss")],
        end: Annotated[str, Field(description="Duration end string. Same format as `start` for the chosen `step`")],
        step: Annotated[str, Field(description="Duration step: one of MONTH, DAY, HOUR, MINUTE, SECOND. Controls start/end format and aggregation granularity")],
        instance_id: Annotated[str, Field(description="Instance ID")],
    ) -> Dict[str, Any]:
        try:
            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.list_processes(start=start, end=end, step=step, instance_id=instance_id)
            return {"data": data}
        except Exception as e:
            logger.error("list_processes failed", error=str(e))
            raise ToolError(f"list_processes failed: {e}")

    @mcp.tool(
        name=tool_name("query_traces"),
        description=(
            "[SkyWalking] Query traces using SkyWalking GraphQL trace APIs. "
            "This tool auto-detects whether the backend supports Trace V2 (`queryTraces`) and otherwise uses Trace V1 (`queryBasicTraces`). "
            "Use explicit parameters rather than a raw request dict.\n\n"
            "Recommended workflow:\n"
            "1. Narrow scope: call `list_layers` -> `list_services` -> (`list_instances` / `list_endpoints`) to obtain IDs.\n"
            "2. Call `query_traces` with explicit params (e.g. `service_id`, `start`, `end`, `step`) or `trace_id`.\n"
            "3. Control pagination with `page_num`/`page_size`.\n\n"
            "Key notes and safeguards:\n"
            "- Provide either a `trace_id` or all of `start`, `end`, and `step` to avoid broad queries.\n"
            "- `start`/`end`/`step` use the same Duration formats as other SkyWalking tools:\n"
            "  - MONTH  -> yyyy-MM (e.g. 2017-11)\n"
            "  - DAY    -> yyyy-MM-dd (e.g. 2017-11-08)\n"
            "  - HOUR   -> yyyy-MM-dd HH (e.g. 2017-11-08 09)\n"
            "  - MINUTE -> yyyy-MM-dd HHmm (e.g. 2017-11-08 0201)\n"
            "  - SECOND -> yyyy-MM-dd HHmmss (e.g. 2017-11-08 093015)\n"
            "- Use `page_size` to limit returned traces (default 20, max 100).\n\n"
            "Examples:\n"
            '- {"service_id": "S1", "step": "MINUTE", "start": "2026-04-08 0201", "end": "2026-04-08 0231", "page_num": 1, "page_size": 20}\n'
            '- {"trace_id": "<trace-id>"} — fetch traces by a specific trace id'
        ),
        annotations={"title": "SkyWalking: Query Traces", "readOnlyHint": True},
        tags={"skywalking", "traces"},
        meta={"backend": "skywalking"},
    )
    async def query_traces(
        service_id: Annotated[Optional[str], Field(description="Service ID (use 0 or omit for all services)")] = None,
        service_instance_id: Annotated[Optional[str], Field(description="Service instance ID (optional)")] = None,
        endpoint_id: Annotated[Optional[str], Field(description="Endpoint ID (optional)")] = None,
        trace_id: Annotated[Optional[str], Field(description="Specific traceId to fetch (optional)")] = None,
        start: Annotated[Optional[str], Field(description="Duration start string. Format depends on `step`: MONTH=yyyy-MM, DAY=yyyy-MM-dd, HOUR=yyyy-MM-dd HH, MINUTE=yyyy-MM-dd HHmm, SECOND=yyyy-MM-dd HHmmss (optional)")] = None,
        end: Annotated[Optional[str], Field(description="Duration end string. Same format as `start` for the chosen `step` (optional)")] = None,
        step: Annotated[Optional[str], Field(description="Duration step (MONTH|DAY|HOUR|MINUTE|SECOND) (optional)")] = None,
        min_trace_duration: Annotated[Optional[int], Field(description="Minimum trace duration (ms) to filter, optional")] = None,
        max_trace_duration: Annotated[Optional[int], Field(description="Maximum trace duration (ms) to filter, optional")] = None,
        trace_state: Annotated[Optional[str], Field(description="TraceState: ALL, SUCCESS, or ERROR (optional)")] = "ALL",
        query_order: Annotated[Optional[str], Field(description="QueryOrder: BY_START_TIME or BY_DURATION (optional)")] = "BY_START_TIME",
        tags: Annotated[Optional[Any], Field(description='List of span tags to filter, e.g. [{"key": "http.method", "value": "GET"}] (optional)')] = None,
        page_num: Annotated[Optional[int], Field(description="Pagination page number (default 1)")] = 1,
        page_size: Annotated[Optional[int], Field(description="Pagination page size (default 20, max 100)")] = 20,
        debug: Annotated[Optional[bool], Field(description="If true, enable OAP debug tracing for the query (optional)")] = False,
    ) -> Dict[str, Any]:
        try:
            if (start is None) ^ (end is None) or (start is None) ^ (step is None):
                raise ValidationError("start, end, step must be provided together")

            condition: Dict[str, Any] = {}
            if service_id is not None:
                condition["serviceId"] = service_id
            if service_instance_id is not None:
                condition["serviceInstanceId"] = service_instance_id
            if endpoint_id is not None:
                condition["endpointId"] = endpoint_id
            if trace_id is not None:
                condition["traceId"] = trace_id

            if start is not None and end is not None and step is not None:
                condition["queryDuration"] = {"start": start, "end": end, "step": step}

            if min_trace_duration is not None:
                condition["minTraceDuration"] = min_trace_duration
            if max_trace_duration is not None:
                condition["maxTraceDuration"] = max_trace_duration

            condition["traceState"] = trace_state or "ALL"
            condition["queryOrder"] = query_order or "BY_START_TIME"

            if tags is not None:
                condition["tags"] = tags

            condition["paging"] = {
                "pageNum": max(1, page_num or 1),
                "pageSize": min(max(1, page_size or 20), 100),
            }

            trace_id_present = condition.get("traceId")
            qd = condition.get("queryDuration")
            if not trace_id_present and not (qd and qd.get("start") and qd.get("end") and qd.get("step")):
                raise ValidationError("query_traces requires either 'trace_id' or all of 'start', 'end', and 'step'")

            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.query_traces(condition, debug=bool(debug))
            return {"data": data}
        except ValidationError:
            raise
        except Exception as e:
            logger.error("query_traces failed", error=str(e))
            raise ToolError(f"query_traces failed: {e}")

    @mcp.tool(
        name=tool_name("get_trace_detail"),
        description=(
            "[SkyWalking] Retrieve full trace details for a given `trace_id`.\n\n"
            "Usage:\n"
            "1. Call `query_traces` to find candidate trace IDs.\n"
            "2. Call `get_trace_detail` with `trace_id` and optional `start`,`end`,`step`.\n\n"
            "Duration: if provided, `start`/`end` must match `step` format (see list_instances).\n\n"
            'Example: {"trace_id": "t1", "step": "MINUTE", "start": "2023-01-01 1200", "end": "2023-01-01 1230"}'
        ),
        annotations={"title": "SkyWalking: Trace Detail", "readOnlyHint": True},
        tags={"skywalking", "traces"},
        meta={"backend": "skywalking"},
    )
    async def get_trace_detail(
        trace_id: Annotated[str, Field(description="Trace ID")],
        start: Annotated[Optional[str], Field(description="Optional duration start string. If provided, end and step must also be provided")] = None,
        end: Annotated[Optional[str], Field(description="Optional duration end string. If provided, start and step must also be provided")] = None,
        step: Annotated[Optional[str], Field(description="Optional duration step (MONTH|DAY|HOUR|MINUTE|SECOND). If provided, start and end must also be provided")] = None,
        debug: Annotated[Optional[bool], Field(description="If true, enable OAP debug tracing for this trace detail query (optional)")] = False,
    ) -> Dict[str, Any]:
        if not trace_id:
            raise ValidationError("trace_id is required")
        if (start is None) ^ (end is None) or (start is None) ^ (step is None):
            raise ValidationError("start, end, step must be provided together, or all omitted")

        try:
            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.get_trace_detail(
                trace_id=trace_id,
                start=start,
                end=end,
                step=step,
                debug=bool(debug),
            )
            return {"data": data}
        except Exception as e:
            logger.error("get_trace_detail failed", error=str(e))
            raise ToolError(f"get_trace_detail failed: {e}")
