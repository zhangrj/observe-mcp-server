from __future__ import annotations

import uuid
import json
from typing import Any, Dict, Optional

from fastmcp.exceptions import ValidationError, ToolError
from pydantic import Field
from typing_extensions import Annotated

from ..backends.openobserve import OpenObserveBackend
from ..models import StreamType
from ..settings import OpenObserveSettings


def _build_sql(
    stream: str,
    where: Optional[str],
    order_by: Optional[str],
    sql: Optional[str],
) -> str:
    """Build SQL for OpenObserve search.

    If `sql` is provided, it is used as-is.
    Otherwise, we build: SELECT * FROM {stream} [WHERE ...] [ORDER BY ...]
    """
    if sql:
        return sql
    q = f"SELECT * FROM {stream}"
    if where:
        q += f" WHERE {where}"
    if order_by:
        q += f" ORDER BY {order_by}"
    return q


def _load_stream_catalog(path: str) -> Dict[str, Any]:
    """
    Load stream catalog mapping from a JSON file if configured.

    Set env OPENOBSERVE_STREAM_CATALOG_PATH to a JSON file path.
    Expected format:
      {
        "dev_log": {"env":"dev","project":"projectname","kind":"business-log","description":"dev log"},
        ...
      }
    """
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def register_openobserve_tools(mcp, logger, tool_prefix: str = "") -> None:
    """
    Register Phase-1 OpenObserve tools.

    Tools:
      - {prefix}openobserve_stream_list
      - {prefix}openobserve_logs_query
    """

    def tool_name(name: str) -> str:
        return f"{tool_prefix}{name}" if tool_prefix else name

    @mcp.tool(
        name=tool_name("openobserve_stream_list"),
        description=(
            "[OpenObserve] List Streams (logs/metrics/traces).\n"
            "Maps to the OpenObserve Streams API: GET /api/{org}/streams?fetchSchema=false&type={StreamType}.\n"
            "Returns the raw OpenObserve response structure: "
            "{ list: [ {name, storage_type, stream_type, stats, (schema?), settings} ... ] }.\n"
            "This tool may also return a catalog mapping (if configured) to provide human-friendly meaning for stream names."
            "Use cases: discover available stream names before querying, or inspect stream stats / "
            "full-text index field configuration.\n"
        ),
        annotations={
            "title": "OpenObserve: List Streams",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
        tags={"openobserve", "streams", "discovery"},
        meta={"backend": "openobserve", "phase": "1"},
    )
    async def openobserve_stream_list(
        stream_type: Annotated[
            StreamType, Field(description="Stream type: logs | metrics | traces")
        ] = StreamType.logs,
        fetch_schema: Annotated[
            bool, Field(description="Whether to include the schema field for each stream")
        ] = False,
    ) -> Dict[str, Any]:
        """
        OpenObserve Streams List.

        - Endpoint: GET /api/{organization}/streams?fetchSchema=false&type={StreamType}
        - Notes:
          - When fetchSchema=true, the response includes schema (field names/types).
          - type supports logs/metrics/traces; default is logs.
        """
        req_id = str(uuid.uuid4())
        log = logger.bind(req_id=req_id, tool="openobserve_stream_list")
        log.info("request", stream_type=stream_type.value, fetch_schema=fetch_schema)

        try:
            settings = OpenObserveSettings() # type: ignore
            backend = OpenObserveBackend(settings)
            data = await backend.list_streams(stream_type=stream_type, fetch_schema=fetch_schema)

            catalog = _load_stream_catalog(settings.stream_catalog_path)
            # only keep entries that exist in returned streams
            try:
                stream_names = {s.get("name") for s in data.get("list", []) if isinstance(s, dict)}
                catalog = {k: v for k, v in catalog.items() if k in stream_names}
            except Exception:
                pass

            log.info("success")
            return {"data": data, "catalog": catalog}
        except Exception as e:
            log.error("failure", error=str(e))
            raise ToolError(f"openobserve_stream_list failed: {e}")

    @mcp.tool(
        name=tool_name("openobserve_logs_query"),
        description=(
            "[OpenObserve] Query log data (Phase-1 supports logs only).\n"
            "Maps to the OpenObserve Search API: POST /api/{org}/_search.\n"
            "Key parameters:\n"
            "  - stream: log stream name (e.g., k8s)\n"
            "  - start_time_us / end_time_us: microsecond timestamps (required; OpenObserve docs emphasize "
            "providing a time range to avoid scanning the entire dataset)\n"
            "  - sql: optional full SQL; if omitted, it is composed from stream/where/order_by. SQL is PostgreSQL-like.\n"
            "  - offset(size/from): pagination\n"
            "Returns fields: took/hits/total/from/size/scan_size (raw OpenObserve structure).\n"
            "This tool also returns an additional page object with next_offset and has_more derived from OpenObserve total/from/size."
            "Safety/cost guardrails: caps size to OPENOBSERVE_MAX_PAGE_SIZE to avoid overly large responses.\n"
        ),
        annotations={
            "title": "OpenObserve: Query Logs",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
        tags={"openobserve", "logs", "query"},
        meta={"backend": "openobserve", "phase": "1"},
    )
    async def openobserve_logs_query(
        stream: Annotated[
            str, Field(description="Log stream name, e.g., k8s (from openobserve_stream_list)")
        ],
        start_time_us: Annotated[
            int, Field(description="Start time (microsecond timestamp, required)")
        ],
        end_time_us: Annotated[
            int, Field(description="End time (microsecond timestamp, required)")
        ],
        offset: Annotated[
            int, Field(description="Pagination offset; maps to OpenObserve query.from")
        ] = 0,
        size: Annotated[
            int, Field(description="Pagination limit; maps to OpenObserve query.size")
        ] = 50,
        where: Annotated[
            Optional[str],
            Field(
                description=(
                    "Optional WHERE clause (without the WHERE keyword), "
                    "e.g., kubernetes.namespace_name='default' AND code=200"
                )
            ),
        ] = None,
        order_by: Annotated[
            Optional[str],
            Field(
                description=(
                    "Optional ORDER BY clause (without the ORDER BY keyword); default is _timestamp DESC"
                )
            ),
        ] = "_timestamp DESC",
        sql: Annotated[
            Optional[str],
            Field(
                description=(
                    "Optional full SQL; when provided, it overrides the auto-composed SQL from "
                    "stream/where/order_by"
                )
            ),
        ] = None,
        search_type: Annotated[
            str, Field(description="search_type: ui | dashboards | reports | alerts")
        ] = "ui",
        timeout: Annotated[
            int, Field(description="timeout: 0 means use the server default")
        ] = 0,
    ) -> Dict[str, Any]:
        """
        OpenObserve Search (logs query).

        - Endpoint: POST /api/{organization}/_search
        - Request body:
          {
            "query": {
              "sql": "...",
              "start_time": <microseconds>,
              "end_time": <microseconds>,
              "from": <offset>,
              "size": <limit>
            },
            "search_type": "ui",
            "timeout": 0
          } https://openobserve.ai/docs/api/search/search/

        Constraints:
          - start_time/end_time must be provided in microseconds; the docs emphasize providing a time range.
        """
        req_id = str(uuid.uuid4())
        log = logger.bind(req_id=req_id, tool="openobserve_logs_query")
        log.info(
            "request",
            stream=stream,
            start_time_us=start_time_us,
            end_time_us=end_time_us,
            offset=offset,
            size=size,
        )

        settings = OpenObserveSettings() # type: ignore

        # Guardrails
        if start_time_us <= 0 or end_time_us <= 0:
            raise ValidationError("start_time_us/end_time_us must be provided in microseconds (us) and > 0")
        if end_time_us < start_time_us:
            raise ValidationError("end_time_us must be >= start_time_us")
        if size <= 0:
            raise ValidationError("size must be > 0")
        if size > settings.max_page_size:
            raise ValidationError(f"size too large: {size}, max_page_size={settings.max_page_size}")

        final_sql = _build_sql(stream=stream, where=where, order_by=order_by, sql=sql)

        body = {
            "query": {
                "sql": final_sql,
                "start_time": start_time_us,
                "end_time": end_time_us,
                "from": offset,
                "size": size,
            },
            "search_type": search_type,
            "timeout": timeout,
        }

        try:
            backend = OpenObserveBackend(settings)
            data = await backend.search(body)

            # --- Pagination hints (agent-friendly, non-breaking) ---
            total = data.get("total")
            resp_from = data.get("from", offset)
            resp_size = data.get("size", size)

            # next page heuristic: OpenObserve defines from/size as offset/limit
            # (see docs: query.from, query.size; response total/from/size)
            next_offset = resp_from + resp_size if isinstance(resp_from, int) and isinstance(resp_size, int) else offset + size
            has_more = False
            if isinstance(total, int) and isinstance(next_offset, int):
                has_more = next_offset < total

            page = {
                "offset": resp_from,
                "size": resp_size,
                "total": total,
                "next_offset": next_offset,
                "has_more": has_more,
            }

            log.info("success")
            return {"data": data, "page": page}
        except Exception as e:
            log.error("failure", error=str(e))
            raise ToolError(f"openobserve_logs_query failed: {e}")

    @mcp.tool(
        name=tool_name("openobserve_list_stream_schema"),
        description=(
            "[OpenObserve] Retrieve the schema for a specific stream.\n"
            "Maps to the OpenObserve API: GET /api/{org}/{stream}/schema.\n"
            "Key parameters:\n"
            "  - stream: stream name (from openobserve_stream_list)\n"
            "  - stream_type: stream type (logs/metrics/traces), default logs\n"
            "Use cases: get field names/types to help build query conditions "
            "(e.g., fields referenced in where/order_by).\n"
        ),
        annotations={
            "title": "OpenObserve: Get Stream Schema",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
        tags={"openobserve", "stream", "schema"},
        meta={"backend": "openobserve", "phase": "1"},
    )
    async def openobserve_list_stream_schema(
        stream: Annotated[
            str, Field(description="Stream name, e.g., k8s (from openobserve_stream_list)")
        ],
        stream_type: Annotated[
            StreamType, Field(description="Stream type: logs | metrics | traces")
        ] = StreamType.logs,
    ) -> Dict[str, Any]:
        """
        OpenObserve Get Stream Schema.

        - Endpoint: GET /api/{organization}/{stream}/schema
        """
        req_id = str(uuid.uuid4())
        log = logger.bind(req_id=req_id, tool="openobserve_list_stream_schema")
        log.info("request", stream=stream)

        try:
            settings = OpenObserveSettings() # type: ignore
            backend = OpenObserveBackend(settings)
            data = await backend.list_stream_schema(stream, stream_type)
            log.info("success")
            return {"data": data}
        except Exception as e:
            log.error("failure", error=str(e))
            raise ToolError(f"openobserve_list_stream_schema failed: {e}")