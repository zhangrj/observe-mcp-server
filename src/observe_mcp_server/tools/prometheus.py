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
            "[Prometheus] List all available metric names in Prometheus.\n"
            "Typically maps to the Prometheus HTTP API: /api/v1/label/__name__/values.\n"
            "Common use cases: metric discovery, auto-completion, and dashboard building."
        ),
        annotations={
            "title": "Prometheus: List Metrics",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
        tags={"prometheus", "discovery"},
        meta={"backend": "prometheus", "phase": "2"},
    )
    async def prometheus_list_metrics(
        match: Annotated[str | None, Field(description="Optional filter (e.g., keyword/regex); Phase-2 implementation detail")] = None,
        limit: Annotated[int | None, Field(description="Optional max number of results; Phase-2 implementation detail")] = None,
    ):
        raise ToolError("Prometheus tools are not implemented in Phase-1")

    @mcp.tool(
        name=tool_name("prometheus_execute_query"),
        description=(
            "[Prometheus] Execute a PromQL instant query.\n"
            "Typically maps to the Prometheus HTTP API: /api/v1/query.\n"
            "Input query (PromQL) and optional time (RFC3339 or Unix timestamp)."
        ),
        annotations={
            "title": "Prometheus: Execute Instant Query",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
        tags={"prometheus", "query"},
        meta={"backend": "prometheus", "phase": "2"},
    )
    async def prometheus_execute_query(
        query: Annotated[str, Field(description="PromQL expression, e.g. up{job='prometheus'}")],
        time: Annotated[str | None, Field(description="Optional evaluation time (RFC3339 or Unix timestamp)")] = None,
    ):
        raise ToolError("Prometheus tools are not implemented in Phase-1")

    @mcp.tool(
        name=tool_name("prometheus_execute_range_query"),
        description=(
            "[Prometheus] Execute a PromQL range query.\n"
            "Typically maps to the Prometheus HTTP API: /api/v1/query_range.\n"
            "Required: start/end/step for returning a time series (matrix)."
        ),
        annotations={
            "title": "Prometheus: Execute Range Query",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
        tags={"prometheus", "query"},
        meta={"backend": "prometheus", "phase": "2"},
    )
    async def prometheus_execute_range_query(
        query: Annotated[str, Field(description="PromQL expression")],
        start: Annotated[str, Field(description="Start time (RFC3339 or Unix timestamp)")],
        end: Annotated[str, Field(description="End time (RFC3339 or Unix timestamp)")],
        step: Annotated[str, Field(description="Step/resolution, e.g. 15s, 1m, 5m")],
    ):
        raise ToolError("Prometheus tools are not implemented in Phase-1")