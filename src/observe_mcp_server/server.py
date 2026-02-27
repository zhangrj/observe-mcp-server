from __future__ import annotations

from fastmcp import FastMCP

from .logging import get_logger
from .settings import ToolsetSettings
from .tools import (
    register_openobserve_tools,
    register_prometheus_tools,
    register_skywalking_tools,
)

mcp = FastMCP(name="observe-mcp-server")
logger = get_logger("observe_mcp_server")


def register_all_tools() -> None:
    toolsets = ToolsetSettings()
    prefix = toolsets.tool_prefix or ""

    if toolsets.enable_openobserve:
        register_openobserve_tools(mcp, logger, tool_prefix=prefix)

    # Phase-1 default disabled; kept for future extension
    if toolsets.enable_prometheus:
        register_prometheus_tools(mcp, logger, tool_prefix=prefix)

    if toolsets.enable_skywalking:
        register_skywalking_tools(mcp, logger, tool_prefix=prefix)


register_all_tools()