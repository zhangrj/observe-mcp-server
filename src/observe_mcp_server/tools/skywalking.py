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
            "{" + '"listLayers": [{"id":"L1","name":"HTTP"}]' + "}"
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
            "[SkyWalking] List services in SkyWalking OAP, optionally filtered by `layer`.\n"
            "A service is a logical application or component monitored by SkyWalking.\n\n"
            "Workflow:\n"
            "1. Call `list_layers` to discover available layers.\n"
            "2. Call `list_services` with a layer to obtain service objects containing `id` and `name`.\n\n"
            "Notes:\n"
            "- Use the returned `id` when calling `list_instances`, `list_endpoints` or trace queries.\n"
            "- Responses include `id` and `name` fields for programmatic use.\n\n"
            "Examples:\n"
            "- {\"layer\": \"GENERAL\"} — list services in GENERAL layer"
        ),
        annotations={"title": "SkyWalking: List Services", "readOnlyHint": True},
        tags={"skywalking", "metadata"},
        meta={"backend": "skywalking"},
    )
    async def list_services(layer: Annotated[Optional[str], Field(description="Layer name, optional")]=None) -> Dict[str, Any]:
        try:
            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.list_services(layer=layer)
            return {"data": data}
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
            "2. Call `list_instances` with that `service_id` and optional `start`/`end` duration to narrow results.\n\n"
            "Parameters:\n"
            "- `service_id` (required): SkyWalking service ID.\n"
            "- `keyword` (optional): text filter on instance name.\n"
            "- `limit` (optional): max results (default 100).\n\n"
            "Example:\n"
            "- {\"service_id\": \"S1\", \"start\": \"-1h\"}"
        ),
        annotations={"title": "SkyWalking: List Instances", "readOnlyHint": True},
        tags={"skywalking", "metadata"},
        meta={"backend": "skywalking"},
    )
    async def list_instances(
        service_id: Annotated[str, Field(description="Service ID")],
        keyword: Annotated[Optional[str], Field(description="Optional search keyword")] = None,
        limit: Annotated[int, Field(description="Max results (default 100)")] = 100,
    ) -> Dict[str, Any]:
        try:
            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.list_instances(service_id=service_id, keyword=keyword, limit=limit)
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
            "2. Call `list_endpoints` with `service_id` (optionally `keyword`) to find endpoint ids.\n\n"
            "Parameters & examples:\n"
            "- {\"service_id\": \"S1\"} — list endpoints for service S1\n"
            "- {\"service_id\": \"S1\", \"keyword\": \"/api/users\"} — search by path substring"
        ),
        annotations={"title": "SkyWalking: List Endpoints", "readOnlyHint": True},
        tags={"skywalking", "metadata"},
        meta={"backend": "skywalking"},
    )
    async def list_endpoints(
        service_id: Annotated[str, Field(description="Service ID")],
        keyword: Annotated[Optional[str], Field(description="Optional search keyword")] = None,
        limit: Annotated[int, Field(description="Max results (default 100)")] = 100,
    ) -> Dict[str, Any]:
        try:
            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.list_endpoints(service_id=service_id, keyword=keyword, limit=limit)
            return {"data": data}
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
            "3. Call `list_processes` with `service_id` (and optional time range) to retrieve process metadata.\n\n"
            "Notes: results include process id, agentId, labels and attributes useful for debugging."
        ),
        annotations={"title": "SkyWalking: List Processes", "readOnlyHint": True},
        tags={"skywalking", "metadata"},
        meta={"backend": "skywalking"},
    )
    async def list_processes(
        service_id: Annotated[str, Field(description="Service ID")],
        keyword: Annotated[Optional[str], Field(description="Optional search keyword")] = None,
        limit: Annotated[int, Field(description="Max results (default 100)")] = 100,
    ) -> Dict[str, Any]:
        try:
            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.list_processes(service_id=service_id, keyword=keyword, limit=limit)
            return {"data": data}
        except Exception as e:
            logger.error("list_processes failed", error=str(e))
            raise ToolError(f"list_processes failed: {e}")

    @mcp.tool(
        name=tool_name("query_traces"),
        description=(
            "[SkyWalking] Query traces using SkyWalking GraphQL `queryTraces` protocol. Accepts a request dict matching common TraceQueryRequest fields.\n\n"
            "Recommended workflow:\n"
            "1. Narrow scope: call `list_layers` -> `list_services` -> (`list_instances` / `list_endpoints`) to obtain IDs.\n"
            "2. Call `query_traces` with `service_id`/`instance_id`/`endpoint_id` and a time range (`start`/`end`) or `trace_id`.\n"
            "3. Use `view` parameter to choose result format: `full` (raw), `summary` (aggregated insight), `errors_only` (error traces).\n\n"
            "Key notes and safeguards:\n"
            "- SkyWalking requires either a time range or `trace_id`; prefer specifying `start`/`end` to avoid broad queries.\n"
            "- Use `page_size` to limit returned traces (default limited to prevent large payloads).\n\n"
            "Examples:\n"
            "- {\"service_id\": \"S1\", \"start\": \"-1h\", \"view\": \"summary\"}\n"
            "- {\"trace_id\": \"<trace-id>\"} — fetch a single trace by id"
        ),
        annotations={"title": "SkyWalking: Query Traces", "readOnlyHint": True},
        tags={"skywalking", "traces"},
        meta={"backend": "skywalking"},
    )
    async def query_traces(request: Annotated[Dict[str, Any], Field(description="Trace query request dict")]) -> Dict[str, Any]:
        # Guardrails: require either a trace_id or both start and end times to avoid broad queries.
        try:
            trace_id = request.get("trace_id") if isinstance(request, dict) else None
            start = request.get("start") if isinstance(request, dict) else None
            end = request.get("end") if isinstance(request, dict) else None

            if not trace_id and not (start and end):
                raise ValidationError("query_traces requires either 'trace_id' or both 'start' and 'end' to be specified")

            # page_size caps to prevent large payloads
            page_size = None
            if isinstance(request, dict):
                page_size = request.get("page_size")
                if isinstance(page_size, int):
                    if page_size <= 0:
                        request["page_size"] = 20
                    elif page_size > 100:
                        request["page_size"] = 100

            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.query_traces(request)
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
            "2. Call `get_trace_detail` with `trace_id` to obtain spans, logs, tags and attached events for deep debugging.\n\n"
            "Example: {\"trace_id\": \"t1\"}"
        ),
        annotations={"title": "SkyWalking: Trace Detail", "readOnlyHint": True},
        tags={"skywalking", "traces"},
        meta={"backend": "skywalking"},
    )
    async def get_trace_detail(trace_id: Annotated[str, Field(description="Trace ID")]) -> Dict[str, Any]:
        if not trace_id:
            raise ValidationError("trace_id is required")
        try:
            settings = SkyWalkingSettings()  # type: ignore
            backend = SkyWalkingBackend(settings)
            data = await backend.get_trace_detail(trace_id=trace_id)
            return {"data": data}
        except Exception as e:
            logger.error("get_trace_detail failed", error=str(e))
            raise ToolError(f"get_trace_detail failed: {e}")
