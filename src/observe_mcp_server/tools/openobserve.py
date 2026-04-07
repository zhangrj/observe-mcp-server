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
            "[OpenObserve] List available streams. Use this tool FIRST to choose a stream to query.\n"
            "Returns stream metadata and, if configured, a catalog mapping to human-friendly names.\n"
            "Tip for agents: call this tool before requesting schema or field values for a stream."
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
            "[OpenObserve] Execute a search on a selected stream. Run this LAST after: 1) selecting a stream with openobserve_stream_list, 2) inspecting schema with openobserve_list_stream_schema, and 3) optionally previewing values with openobserve_field_values.\n"
            "Provide microsecond `start_time_us` and `end_time_us` to avoid full scans. Use `validate_only` to run lint checks prior to execution.\n"
            "Returns the raw OpenObserve response plus an agent-friendly `page` object and execution hints when `validate_only` is used."
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
                    "Optional WHERE clause (without the WHERE keyword), field should from openobserve_list_stream_schema, "
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
        validate_only: Annotated[
            bool, Field(description="If true, do not execute the query; only run lint checks and return suggestions")
        ] = False,
        sql_source: Annotated[
            Optional[str], Field(description="Optional hint where SQL came from: ui|nl_to_sql|template")
        ] = None,
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

        # If validate_only is requested, run the SQL linter and return lint result + execution hints
        if validate_only:
            try:
                lint_result = await openobserve_sql_lint(stream=stream, sql=final_sql, start_time_us=start_time_us, end_time_us=end_time_us)
            except Exception as e:
                raise ToolError(f"openobserve_logs_query validate_only lint failed: {e}")

            execution_hint = {
                "safe_to_execute": lint_result.get("valid", False),
                "suggested_sql": lint_result.get("suggested_sql"),
                "messages": lint_result.get("messages", []),
            }
            return {"lint": lint_result, "execution_hint": execution_hint}


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
        log.debug("request_body", body=body)

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
            "[OpenObserve] Retrieve the schema (field names and types) for a selected stream.\n"
            "Use this immediately after choosing a stream to determine valid fields for WHERE/SELECT clauses and to guide value previews."
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

    @mcp.tool(
        name=tool_name("openobserve_field_values"),
        description=(
            "[OpenObserve] Preview top values for one or more fields. Use this after inspecting the stream schema to obtain sample values helpful for building WHERE clauses.\n"
            "Requires a microsecond time window (`start_time_us` and `end_time_us`). Keep `size` small for quick previews."
        ),
        annotations={
            "title": "OpenObserve: Field Values",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
        tags={"openobserve", "values", "discovery"},
        meta={"backend": "openobserve", "phase": "2"},
    )
    async def openobserve_field_values(
        stream: Annotated[str, Field(description="Stream name, e.g., k8s")],
        fields: Annotated[str, Field(description="Comma-separated field names, e.g., service_name,status_code")],
        start_time_us: Annotated[int, Field(description="Start time in microseconds (required)")],
        end_time_us: Annotated[int, Field(description="End time in microseconds (required)")],
        size: Annotated[int, Field(description="How many values to return per field (default 10)")]=10,
        keyword: Annotated[Optional[str], Field(description="Optional substring to filter values")]=None,
        no_count: Annotated[bool, Field(description="If true, do not return counts; default false")]=False,
    ) -> Dict[str, Any]:
        req_id = str(uuid.uuid4())
        log = logger.bind(req_id=req_id, tool="openobserve_field_values")
        log.info("request", stream=stream, fields=fields, start_time_us=start_time_us, end_time_us=end_time_us, size=size)

        settings = OpenObserveSettings() # type: ignore

        # Guardrails
        if start_time_us <= 0 or end_time_us <= 0:
            raise ValidationError("start_time_us/end_time_us must be provided in microseconds (us) and > 0")
        if end_time_us < start_time_us:
            raise ValidationError("end_time_us must be >= start_time_us")
        if size <= 0:
            raise ValidationError("size must be > 0")
        if size > 100:
            raise ValidationError("size too large: max 100")

        try:
            backend = OpenObserveBackend(settings)
            data = await backend.field_values(
                stream=stream,
                fields=fields,
                start_time=start_time_us,
                end_time=end_time_us,
                size=size,
                keyword=keyword,
                no_count=no_count,
            )
            log.info("success")
            return {"data": data}
        except Exception as e:
            log.error("failure", error=str(e))
            raise ToolError(f"openobserve_field_values failed: {e}")

    @mcp.tool(
        name=tool_name("openobserve_sql_lint"),
        description=(
            "[OpenObserve] Lint SQL for safety and performance using the stream schema. Run this before executing a query to check time range, avoid expensive patterns (e.g., SELECT *), and get suggested SQL.\n"
            "Recommended usage: call after schema inspection and before `openobserve_logs_query` execution (or via `validate_only`)."
        ),
        annotations={
            "title": "OpenObserve: SQL Lint",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
        tags={"openobserve", "lint", "safety"},
        meta={"backend": "openobserve", "phase": "2"},
    )
    async def openobserve_sql_lint(
        stream: Annotated[str, Field(description="Stream name, e.g., k8s")],
        sql: Annotated[Optional[str], Field(description="SQL text to lint; if omitted, lint will evaluate a default SELECT * pattern")]=None,
        start_time_us: Annotated[Optional[int], Field(description="Optional start time in microseconds for suggested fixes")]=None,
        end_time_us: Annotated[Optional[int], Field(description="Optional end time in microseconds for suggested fixes")]=None,
    ) -> Dict[str, Any]:
        """
        Basic schema-aware lint: enforces time-window, warns on SELECT *, and suggests explicit fields.
        Returns: { valid: bool, messages: [...], suggested_sql: str, schema: {...} }
        """
        req_id = str(uuid.uuid4())
        log = logger.bind(req_id=req_id, tool="openobserve_sql_lint")
        log.info("request", stream=stream)

        try:
            settings = OpenObserveSettings() # type: ignore
            backend = OpenObserveBackend(settings)

            # fetch schema to make suggestions
            try:
                schema_resp = await backend.list_stream_schema(stream, StreamType.logs)
            except Exception:
                schema_resp = {}

            messages: list[str] = []
            valid = True
            suggested_sql = sql or f"SELECT * FROM {stream}"

            # check time window
            if not start_time_us or not end_time_us:
                messages.append("Missing time window: recommend providing start_time_us and end_time_us in microseconds to avoid full scans.")
                valid = False
            else:
                if end_time_us < start_time_us:
                    messages.append("Invalid time window: end_time_us < start_time_us")
                    valid = False

            # check SELECT * usage
            if sql:
                low = sql.lower()
                if "select *" in low:
                    # try to suggest explicit fields from schema
                    fields_suggestion = None
                    try:
                        # schema_resp may contain various shapes; attempt to extract field names
                        field_names: list[str] = []
                        s = None
                        if isinstance(schema_resp, dict):
                            s = schema_resp.get("schema") or schema_resp.get("defined_schema_fields") or schema_resp
                        if isinstance(s, dict) and "fields" in s and isinstance(s["fields"], list):
                            for f in s["fields"]:
                                if isinstance(f, dict):
                                    name = f.get("name")
                                    if name:
                                        field_names.append(name)
                                else:
                                    field_names.append(str(f))
                        elif isinstance(s, list):
                            for f in s:
                                if isinstance(f, dict):
                                    name = f.get("name")
                                    if name:
                                        field_names.append(name)
                                else:
                                    field_names.append(str(f))
                        # fallback to top-level keys if schema_resp is a mapping of fields
                        if not field_names and isinstance(schema_resp, dict):
                            for k in ["defined_schema_fields", "fields", "schema"]:
                                v = schema_resp.get(k)
                                if isinstance(v, list):
                                    for item in v:
                                        if isinstance(item, str):
                                            field_names.append(item)
                        if field_names:
                            fields_suggestion = ",".join(field_names[:8])
                    except Exception:
                        fields_suggestion = None

                    if fields_suggestion:
                        suggested_sql = sql.replace("*", fields_suggestion, 1)
                        messages.append("Avoid SELECT *: suggested explicit fields based on schema.")
                    else:
                        messages.append("Avoid SELECT *: consider selecting explicit fields to reduce scan size.")
                    valid = False

            # summary
            result = {
                "valid": valid,
                "messages": messages,
                "suggested_sql": suggested_sql,
                "schema": schema_resp,
            }

            log.info("success", valid=valid, messages=messages)
            return result
        except Exception as e:
            log.error("failure", error=str(e))
            raise ToolError(f"openobserve_sql_lint failed: {e}")