from __future__ import annotations

import argparse
import os

from .logging import setup_logging
from .settings import MCPSettings
from .server import mcp


def main() -> None:
    parser = argparse.ArgumentParser(prog="observe-mcp-server")
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], help="MCP transport")
    parser.add_argument("--host", help="Bind host (for sse/streamable-http)")
    parser.add_argument("--port", type=int, help="Bind port (for sse/streamable-http)")
    parser.add_argument("--path", help="Mount path (for sse/streamable-http)")
    parser.add_argument("--log-level", help="Log level: DEBUG/INFO/WARNING/ERROR")
    args = parser.parse_args()

    if args.log_level:
        os.environ["OBSERVE_LOG_LEVEL"] = args.log_level.upper()

    logger = setup_logging("observe_mcp_server")
    logger.info("starting", component="bootstrap")

    s = MCPSettings()
    transport = args.transport or s.transport
    host = args.host or s.bind_host
    port = args.port or s.bind_port
    path = args.path or s.path

    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport=transport, host=host, port=port, path=path)


if __name__ == "__main__":
    main()