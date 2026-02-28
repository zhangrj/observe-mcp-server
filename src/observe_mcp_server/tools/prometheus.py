from __future__ import annotations

from fastmcp.exceptions import ValidationError, ToolError
from pydantic import Field
from typing_extensions import Annotated


def register_prometheus_tools(mcp, logger, tool_prefix: str = "") -> None:
    """Register Prometheus toolset (Phase-2 placeholder, disabled by default)."""

    def tool_name(name: str) -> str:
        return f"{tool_prefix}{name}" if tool_prefix else name

    @mcp.tool(
        name=tool_name("prometheus_list_metrics"),
        description=(
            "【Prometheus】列出 Prometheus 中可用的所有指标名称（metrics）。\n"
            "典型对应 Prometheus HTTP API：/api/v1/label/__name__/values。\n"
            "常见用途：发现指标、自动补全、构建仪表盘。"
        ),
        tags={"prometheus", "discovery"},
        meta={"backend": "prometheus", "phase": "2"},
    )
    async def prometheus_list_metrics(
        match: Annotated[str | None, Field(description="可选过滤条件（例如按关键字/正则过滤，具体实现二期确定）")] = None,
        limit: Annotated[int | None, Field(description="可选返回数量限制（实现二期确定）")] = None,
    ):
        raise ToolError("Prometheus tools are not implemented in Phase-1")

    @mcp.tool(
        name=tool_name("prometheus_execute_query"),
        description=(
            "【Prometheus】执行 PromQL Instant Query（即时查询）。\n"
            "典型对应 Prometheus HTTP API：/api/v1/query。\n"
            "输入 query（PromQL），可选 time（RFC3339 或 unix timestamp）。"
        ),
        tags={"prometheus", "query"},
        meta={"backend": "prometheus", "phase": "2"},
    )
    async def prometheus_execute_query(
        query: Annotated[str, Field(description="PromQL 表达式，例如 up{job='prometheus'}")],
        time: Annotated[str | None, Field(description="可选：评估时间点（RFC3339 或 unix timestamp）")] = None,
    ):
        raise ToolError("Prometheus tools are not implemented in Phase-1")

    @mcp.tool(
        name=tool_name("prometheus_execute_range_query"),
        description=(
            "【Prometheus】执行 PromQL Range Query（范围查询）。\n"
            "典型对应 Prometheus HTTP API：/api/v1/query_range。\n"
            "必填：start/end/step，用于返回时间序列（matrix）。"
        ),
        tags={"prometheus", "query"},
        meta={"backend": "prometheus", "phase": "2"},
    )
    async def prometheus_execute_range_query(
        query: Annotated[str, Field(description="PromQL 表达式")],
        start: Annotated[str, Field(description="开始时间（RFC3339 或 unix timestamp）")],
        end: Annotated[str, Field(description="结束时间（RFC3339 或 unix timestamp）")],
        step: Annotated[str, Field(description="步长/分辨率，例如 15s、1m、5m")],
    ):
        raise ToolError("Prometheus tools are not implemented in Phase-1")