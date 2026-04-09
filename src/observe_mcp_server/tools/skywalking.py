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
            "[SkyWalking] List available layers.\n"
            "Use this first, then call `list_services` with one returned layer.\n\n"
            "Example response:\n"
            '{"listLayers": [{"id":"GENERAL","name":"GENERAL"}]}'
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
            "[SkyWalking] List services for a required `layer`.\n"
            "Workflow: `list_layers` -> `list_services` -> use returned service `id` in other tools.\n\n"
            'Example: {"layer": "GENERAL"}'
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
            "[SkyWalking] List instances for `service_id` in a required duration (`start_utc`,`end_utc`,`step`).\n"
            "Use `list_services` first to get `service_id`.\n\n"
            "Duration formats:\n"
            "MONTH=yyyy-MM, DAY=yyyy-MM-dd, HOUR=yyyy-MM-dd HH, MINUTE=yyyy-MM-dd HHmm, SECOND=yyyy-MM-dd HHmmss\n\n"
            'Example: {"service_id": "S1", "step": "HOUR", "start_utc": "2017-11-08 09", "end_utc": "2017-11-08 19"}'
        ),
        annotations={"title": "SkyWalking: List Instances", "readOnlyHint": True},
        tags={"skywalking", "metadata"},
        meta={"backend": "skywalking"},
    )
    async def list_instances(
        start_utc: Annotated[str, Field(description="UTC duration start string. Format depends on `step`: MONTH=yyyy-MM, DAY=yyyy-MM-dd, HOUR=yyyy-MM-dd HH, MINUTE=yyyy-MM-dd HHmm, SECOND=yyyy-MM-dd HHmmss")],
        end_utc: Annotated[str, Field(description="UTC duration end string. Same format as `start_utc` for the chosen `step`")],
        step: Annotated[str, Field(description="Duration step: one of MONTH, DAY, HOUR, MINUTE, SECOND. Controls start_utc/end_utc format and aggregation granularity")],
        service_id: Annotated[str, Field(description="Service ID")],
    ) -> Dict[str, Any]:
        try:
            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.list_instances(start=start_utc, end=end_utc, step=step, service_id=service_id)
            return {"data": data}
        except Exception as e:
            logger.error("list_instances failed", error=str(e))
            raise ToolError(f"list_instances failed: {e}")

    @mcp.tool(
        name=tool_name("list_endpoints"),
        description=(
            "[SkyWalking] List/search endpoints for `service_id`.\n"
            "Optional filters: `keyword`, `start_utc`, `end_utc`, `step`.\n"
            "Use `list_services` first to get `service_id`.\n\n"
            'Examples:\n'
            '- {"service_id": "S1"}\n'
            '- {"service_id": "S1", "keyword": "/api/users", "step": "DAY", "start_utc": "2023-01-01", "end_utc": "2023-01-07"}'
        ),
        annotations={"title": "SkyWalking: List Endpoints", "readOnlyHint": True},
        tags={"skywalking", "metadata"},
        meta={"backend": "skywalking"},
    )
    async def list_endpoints(
        service_id: Annotated[str, Field(description="Service ID")],
        start_utc: Annotated[Optional[str], Field(description="Optional UTC duration start string. Format depends on `step`: MONTH=yyyy-MM, DAY=yyyy-MM-dd, HOUR=yyyy-MM-dd HH, MINUTE=yyyy-MM-dd HHmm, SECOND=yyyy-MM-dd HHmmss")] = None,
        end_utc: Annotated[Optional[str], Field(description="Optional UTC duration end string. Same format as `start_utc` for the chosen `step`")] = None,
        step: Annotated[Optional[str], Field(description="Optional duration step (MONTH|DAY|HOUR|MINUTE|SECOND)")] = None,
        keyword: Annotated[Optional[str], Field(description="Optional search keyword")] = None,
        limit: Annotated[int, Field(description="Max results (default 100)")] = 100,
    ) -> Dict[str, Any]:
        try:
            if (start_utc is None) ^ (end_utc is None) or (start_utc is None) ^ (step is None):
                raise ValidationError("start_utc, end_utc, step must be provided together, or all omitted")

            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.list_endpoints(
                service_id=service_id,
                keyword=keyword,
                limit=limit,
                start=start_utc,
                end=end_utc,
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
            "[SkyWalking] List processes for `instance_id` in a required duration (`start_utc`,`end_utc`,`step`).\n"
            "Workflow: `list_services` -> `list_instances` -> `list_processes`.\n\n"
            "Duration formats are the same as `list_instances`."
        ),
        annotations={"title": "SkyWalking: List Processes", "readOnlyHint": True},
        tags={"skywalking", "metadata"},
        meta={"backend": "skywalking"},
    )
    async def list_processes(
        start_utc: Annotated[str, Field(description="Duration UTC start string. Format depends on `step`: MONTH=yyyy-MM, DAY=yyyy-MM-dd, HOUR=yyyy-MM-dd HH, MINUTE=yyyy-MM-dd HHmm, SECOND=yyyy-MM-dd HHmmss")],
        end_utc: Annotated[str, Field(description="Duration UTC end string. Same format as `start_utc` for the chosen `step`")],
        step: Annotated[str, Field(description="Duration step: one of MONTH, DAY, HOUR, MINUTE, SECOND. Controls start_utc/end_utc format and aggregation granularity")],
        instance_id: Annotated[str, Field(description="Instance ID")],
    ) -> Dict[str, Any]:
        try:
            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.list_processes(start=start_utc, end=end_utc, step=step, instance_id=instance_id)
            return {"data": data}
        except Exception as e:
            logger.error("list_processes failed", error=str(e))
            raise ToolError(f"list_processes failed: {e}")

    @mcp.tool(
        name=tool_name("query_traces"),
        description=(
            "[SkyWalking] Query traces. Auto-detects Trace V2 support; otherwise uses Trace V1.\n"
            "Provide either `trace_id` or all of `start_utc`,`end_utc`,`step`.\n"
            "Recommended workflow: `list_layers` -> `list_services` -> (`list_instances`/`list_endpoints`) -> `query_traces`.\n\n"
            'Examples:\n'
            '- {"service_id": "S1", "step": "MINUTE", "start_utc": "2026-04-08 0201", "end_utc": "2026-04-08 0231", "page_num": 1, "page_size": 20}\n'
            '- {"trace_id": "<trace-id>"}'
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
        start_utc: Annotated[Optional[str], Field(description="Duration UTC start string. Format depends on `step`: MONTH=yyyy-MM, DAY=yyyy-MM-dd, HOUR=yyyy-MM-dd HH, MINUTE=yyyy-MM-dd HHmm, SECOND=yyyy-MM-dd HHmmss (optional)")] = None,
        end_utc: Annotated[Optional[str], Field(description="Duration UTC end string. Same format as `start_utc` for the chosen `step` (optional)")] = None,
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
            if (start_utc is None) ^ (end_utc is None) or (start_utc is None) ^ (step is None):
                raise ValidationError("start_utc, end_utc, step must be provided together")

            condition: Dict[str, Any] = {}
            if service_id is not None:
                condition["serviceId"] = service_id
            if service_instance_id is not None:
                condition["serviceInstanceId"] = service_instance_id
            if endpoint_id is not None:
                condition["endpointId"] = endpoint_id
            if trace_id is not None:
                condition["traceId"] = trace_id

            if start_utc is not None and end_utc is not None and step is not None:
                condition["queryDuration"] = {"start": start_utc, "end": end_utc, "step": step}

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
                raise ValidationError("query_traces requires either 'trace_id' or all of 'start_utc', 'end_utc', and 'step'")

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
            "[SkyWalking] Get full trace detail for `trace_id`.\n"
            "Optional: `start_utc`,`end_utc`,`step`.\n"
            "Use `query_traces` first to find trace ids.\n\n"
            'Example: {"trace_id": "t1", "step": "MINUTE", "start_utc": "2023-01-01 1200", "end_utc": "2023-01-01 1230"}'
        ),
        annotations={"title": "SkyWalking: Trace Detail", "readOnlyHint": True},
        tags={"skywalking", "traces"},
        meta={"backend": "skywalking"},
    )
    async def get_trace_detail(
        trace_id: Annotated[str, Field(description="Trace ID")],
        start_utc: Annotated[Optional[str], Field(description="Optional duration UTC start string. If provided, end_utc and step must also be provided")] = None,
        end_utc: Annotated[Optional[str], Field(description="Optional duration UTC end string. If provided, start_utc and step must also be provided")] = None,
        step: Annotated[Optional[str], Field(description="Optional duration step (MONTH|DAY|HOUR|MINUTE|SECOND). If provided, start_utc and end_utc must also be provided")] = None,
        debug: Annotated[Optional[bool], Field(description="If true, enable OAP debug tracing for this trace detail query (optional)")] = False,
    ) -> Dict[str, Any]:
        if not trace_id:
            raise ValidationError("trace_id is required")
        if (start_utc is None) ^ (end_utc is None) or (start_utc is None) ^ (step is None):
            raise ValidationError("start_utc, end_utc, step must be provided together, or all omitted")

        try:
            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.get_trace_detail(
                trace_id=trace_id,
                start=start_utc,
                end=end_utc,
                step=step,
                debug=bool(debug),
            )
            return {"data": data}
        except Exception as e:
            logger.error("get_trace_detail failed", error=str(e))
            raise ToolError(f"get_trace_detail failed: {e}")
