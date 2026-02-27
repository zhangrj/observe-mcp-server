from __future__ import annotations

from fastmcp import UserError
from pydantic import Field
from typing_extensions import Annotated


def register_skywalking_tools(mcp, logger, tool_prefix: str = "") -> None:
    """Register SkyWalking toolset (Phase-2 placeholder, disabled by default)."""

    def tool_name(name: str) -> str:
        return f"{tool_prefix}{name}" if tool_prefix else name

    @mcp.tool(
        name=tool_name("skywalking_list_services"),
        description=(
            "【SkyWalking】列出服务列表（services）。\n"
            "SkyWalking Query Protocol(GraphQL) 中对应 listServices(layer)。\n"
            "常见用途：服务发现、下钻实例/端点/拓扑分析前的入口。"
        ),
        tags={"skywalking", "discovery"},
        meta={"backend": "skywalking", "phase": "2"},
    )
    async def skywalking_list_services(
        layer: Annotated[str | None, Field(description="可选：按 layer 过滤（GraphQL listServices(layer)）")] = None
    ):
        raise UserError("SkyWalking tools are not implemented in Phase-1")

    @mcp.tool(
        name=tool_name("skywalking_list_instances"),
        description=(
            "【SkyWalking】列出服务实例列表（instances）。\n"
            "SkyWalking Query Protocol(GraphQL) 中对应 listInstances(duration, serviceId)。\n"
            "需要 duration + serviceId（或 serviceName 条件，二期确定）。"
        ),
        tags={"skywalking", "discovery"},
        meta={"backend": "skywalking", "phase": "2"},
    )
    async def skywalking_list_instances(
        service_id: Annotated[str, Field(description="服务 ID（SkyWalking 内部 ID）")],
        duration_start: Annotated[str, Field(description="duration.start（如 '2021-07-03 1320' 形式，具体由后端协议决定）")],
        duration_end: Annotated[str, Field(description="duration.end")],
        step: Annotated[str, Field(description="duration.step（例如 MINUTE/HOUR 等）")],
    ):
        raise UserError("SkyWalking tools are not implemented in Phase-1")