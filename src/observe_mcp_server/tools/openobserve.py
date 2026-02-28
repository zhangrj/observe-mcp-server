from __future__ import annotations

import uuid
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
            "【OpenObserve】列出 Streams（logs/metrics/traces）。\n"
            "对应 OpenObserve Streams API：GET /api/{org}/streams?fetchSchema=false&type={StreamType}。\n"
            "返回 OpenObserve 原始响应结构：{ list: [ {name, storage_type, stream_type, stats, (schema?), settings} ... ] }。\n"
            "适用场景：在执行查询前发现可用 stream 名称，或检查 stream 统计信息/全文索引字段配置。\n"
        ),
        tags={"openobserve", "streams", "discovery"},
        meta={"backend": "openobserve", "phase": "1"},
    )
    async def openobserve_stream_list(
        stream_type: Annotated[StreamType, Field(description="Stream 类型：logs | metrics | traces")] = StreamType.logs,
        fetch_schema: Annotated[bool, Field(description="是否返回每个 stream 的 schema 字段")] = False,
    ) -> Dict[str, Any]:
        """
        OpenObserve Streams List.

        - Endpoint: GET /api/{organization}/streams?fetchSchema=false&type={StreamType}
        - Notes:
          - fetchSchema=true 时响应包含 schema（字段名/类型）。
          - type 支持 logs/metrics/traces，默认 logs。
        """
        req_id = str(uuid.uuid4())
        log = logger.bind(req_id=req_id, tool="openobserve_stream_list")
        log.info("request", stream_type=stream_type.value, fetch_schema=fetch_schema)

        try:
            settings = OpenObserveSettings() # type: ignore
            backend = OpenObserveBackend(settings)
            data = await backend.list_streams(stream_type=stream_type, fetch_schema=fetch_schema)
            log.info("success")
            return {"data": data}
        except Exception as e:
            log.error("failure", error=str(e))
            raise ToolError(f"openobserve_stream_list failed: {e}")

    @mcp.tool(
        name=tool_name("openobserve_logs_query"),
        description=(
            "【OpenObserve】查询日志数据（Phase-1 仅支持 logs 查询）。\n"
            "对应 OpenObserve Search API：POST /api/{org}/_search。\n"
            "核心参数：\n"
            "  - stream：日志 stream 名称（如 k8s）\n"
            "  - start_time_us / end_time_us：微秒时间戳（必填；OpenObserve 文档强调必须给时间范围以避免扫描全量数据）\n"
            "  - sql：可直接传完整 SQL；若不传则由 stream/where/order_by 自动拼接\n"
            "  - offset(size/from)：分页\n"
            "返回字段：took/hits/total/from/size/scan_size（OpenObserve 原始结构）。\n"
            "安全/成本保护：限制 size 最大值（OPENOBSERVE_MAX_PAGE_SIZE），避免一次返回过大。\n"
        ),
        tags={"openobserve", "logs", "query"},
        meta={"backend": "openobserve", "phase": "1"},
    )
    async def openobserve_logs_query(
        stream: Annotated[str, Field(description="日志 stream 名称，例如 k8s（来自 openobserve_stream_list）")],
        start_time_us: Annotated[int, Field(description="开始时间（微秒时间戳，必填）")],
        end_time_us: Annotated[int, Field(description="结束时间（微秒时间戳，必填）")],
        offset: Annotated[int, Field(description="分页 offset，对应 OpenObserve query.from")] = 0,
        size: Annotated[int, Field(description="分页 limit，对应 OpenObserve query.size")] = 50,
        where: Annotated[Optional[str], Field(description="可选 WHERE 子句（不含 WHERE 关键字），例如 kubernetes.namespace_name='default'")] = None,
        order_by: Annotated[Optional[str], Field(description="可选 ORDER BY 子句（不含 ORDER BY 关键字），默认 _timestamp DESC")] = "_timestamp DESC",
        sql: Annotated[Optional[str], Field(description="可选完整 SQL；提供时将覆盖 stream/where/order_by 自动拼接")] = None,
        search_type: Annotated[str, Field(description="search_type：ui|dashboards|reports|alerts")] = "ui",
        timeout: Annotated[int, Field(description="timeout：0 表示使用服务端默认")] = 0,
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
          } [2](https://openobserve.ai/docs/api/search/search/)

        Constraints:
          - start_time/end_time 必须提供且为微秒；文档强调必须给时间范围。
        """
        req_id = str(uuid.uuid4())
        log = logger.bind(req_id=req_id, tool="openobserve_logs_query")
        log.info("request", stream=stream, start_time_us=start_time_us, end_time_us=end_time_us, offset=offset, size=size)

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
            log.info("success")
            return {"data": data}
        except Exception as e:
            log.error("failure", error=str(e))
            raise ToolError(f"openobserve_logs_query failed: {e}")
