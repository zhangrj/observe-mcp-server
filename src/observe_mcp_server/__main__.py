from __future__ import annotations

import argparse
import os

from .logging import setup_logging
from .settings import MCPSettings
from .server import mcp


def main() -> None:
    parser = argparse.ArgumentParser(prog="observe-mcp-server")
    parser.add_argument(
        "--transport", choices=["stdio", "sse", "streamable-http"], help="MCP transport"
    )
    parser.add_argument("--host", help="Bind host (for sse/streamable-http)")
    parser.add_argument("--port", type=int, help="Bind port (for sse/streamable-http)")
    parser.add_argument("--path", help="Mount path (for sse/streamable-http)")
    parser.add_argument("--log-level", help="Log level: DEBUG/INFO/WARNING/ERROR")
    args = parser.parse_args()

    overrides = {}
    if args.transport is not None:
        overrides["transport"] = args.transport
    if args.host is not None:
        overrides["bind_host"] = args.host
    if args.port is not None:
        overrides["bind_port"] = args.port
    if args.path is not None:
        overrides["path"] = args.path
    if args.log_level is not None:
        overrides["log_level"] = args.log_level.upper()

    # init kwargs > .env > defaults
    s = MCPSettings(**overrides)

    logger = setup_logging("observe_mcp_server", level_str=s.log_level)
    logger.info(
        "starting",
        component="bootstrap",
        transport=s.transport,
        host=s.bind_host,
        port=s.bind_port,
        path=s.path,
    )

    if s.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport=s.transport, host=s.bind_host, port=s.bind_port, path=s.path)


if __name__ == "__main__":
    main()
