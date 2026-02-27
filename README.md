# observe-mcp-server

Phase-1 implements OpenObserve tools:
- openobserve_stream_list
- openobserve_logs_query

Transports supported (FastMCP):
- stdio (default)
- sse
- streamable-http

## Install
```bash
uv sync
```

## Configure
Copy .env.example to .env and edit.

## Run
### STDIO (default)
```bash
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate     # On Windows
observe-mcp-server
# or
python -m observe_mcp_server
```
### Streamable HTTP
```bash
observe-mcp-server --transport streamable-http --host 0.0.0.0 --port 8000 --path /mcp
```
### SSE
```bash
observe-mcp-server --transport sse --host 0.0.0.0 --port 8000 --path /mcp
```
