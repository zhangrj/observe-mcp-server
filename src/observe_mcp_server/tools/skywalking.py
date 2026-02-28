from __future__ import annotations

from fastmcp.exceptions import ValidationError, ToolError
from pydantic import Field
from typing_extensions import Annotated


def register_skywalking_tools(mcp, logger, tool_prefix: str = "") -> None:
    """Register SkyWalking toolset (Phase-2 placeholder, disabled by default)."""

    def tool_name(name: str) -> str:
        return f"{tool_prefix}{name}" if tool_prefix else name

    @mcp.tool(
        name=tool_name("skywalking_list_services"),
        description=(
            "[SkyWalking] List services.\n"
            "In SkyWalking Query Protocol (GraphQL), this maps to listServices(layer).\n"
            "Common use cases: service discovery and as an entry point before drilling into instances/endpoints/topology analysis."
        ),
        annotations={
            "title": "SkyWalking: List Services",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
        tags={"skywalking", "discovery"},
        meta={"backend": "skywalking", "phase": "2"},
    )
    async def skywalking_list_services(
        layer: Annotated[str | None, Field(description="Optional: filter by layer (GraphQL listServices(layer))")] = None
    ):
        raise ToolError("SkyWalking tools are not implemented in Phase-1")

    @mcp.tool(
        name=tool_name("skywalking_list_instances"),
        description=(
            "[SkyWalking] List service instances.\n"
            "In SkyWalking Query Protocol (GraphQL), this maps to listInstances(duration, serviceId).\n"
            "Requires duration + serviceId (or serviceName filter; Phase-2 implementation detail)."
        ),
        annotations={
            "title": "SkyWalking: List Instances",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
        tags={"skywalking", "discovery"},
        meta={"backend": "skywalking", "phase": "2"},
    )
    async def skywalking_list_instances(
        service_id: Annotated[str, Field(description="Service ID (SkyWalking internal ID)")],
        duration_start: Annotated[str, Field(description="duration.start (e.g., '2021-07-03 1320' format; exact format is determined by the backend protocol)")],
        duration_end: Annotated[str, Field(description="duration.end")],
        step: Annotated[str, Field(description="duration.step (e.g., MINUTE/HOUR, etc.)")],
    ):
        raise ToolError("SkyWalking tools are not implemented in Phase-1")