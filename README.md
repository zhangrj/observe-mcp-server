# observe-mcp-server

This is an MCP server that supports Prometheus metrics, OpenObserve logs and SkyWalking traces.

Overview
--------
`observe-mcp-server` provides a set of MCP (Model Context Protocol) tools for exploring and querying observability systems. The project includes integrations for:

- Prometheus: metric discovery, label schema, label value preview, alias resolution, PromQL linting and execution.
- OpenObserve: log stream listing, schema inspection, field value preview, SQL linting and log queries. (OpenObserve in this project supports log queries only.)
- SkyWalking: GraphQL-based APIs for layers, services, instances, endpoints, trace queries, and trace detail.

Key tools
---------
- `openobserve_stream_list` — list available streams (logs).
- `openobserve_list_stream_schema` — get field names and types for a stream.
- `openobserve_field_values` — preview top‑N values for a field (microsecond time window required).
- `openobserve_sql_lint` — lightweight linting for queries against an OpenObserve stream schema.
- `openobserve_logs_query` — execute a logs query (supports `validate_only` to run linting first).
- `get_metric_catalog` — paginated Prometheus metric name listing (in-memory cache + TTL).
- `get_metric_schema` — list label keys for a metric and provide a light preview.
- `search_label_values` — return top‑N label values for a label and matcher set.
- `resolve_alias` — resolve business-friendly aliases to Prometheus query targets (from `config/prometheus_aliases.json`).
- `lint_promql` — basic static checks and suggestions for PromQL.
- `execute_promql` — run instant or range queries with guardrails.
- SkyWalking tools: `list_layers`, `list_services`, `list_instances`, `list_endpoints`, `list_processes`, `query_traces`, `get_trace_detail`.

Quick start
-----------

1. Create and activate a virtual environment, then install the package in editable mode:

```bash
# Unix / macOS
python -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install -e .
```

2. Configure the service by copying the example env file and editing values:

```bash
cp .env.example .env
# edit .env to set PROMETHEUS_URL, SKYWALKING_BASE_URL, etc.
```

3. Run the server:

```bash
# default (stdio transport)
observe-mcp-server
# or run as a module
python -m observe_mcp_server

# streamable-http transport
observe-mcp-server --transport streamable-http --host 0.0.0.0 --port 8000 --path /mcp

# SSE transport
observe-mcp-server --transport sse --host 0.0.0.0 --port 8000 --path /mcp
```

Configuration
-------------
Environment variables are the primary configuration mechanism. Example variables:

```bash
# Enable Prometheus tools
export OBSERVE_ENABLE_PROMETHEUS=true

# Prometheus base URL
export PROMETHEUS_URL="http://prometheus.example:9090"

# Optional alias file
export PROMETHEUS_ALIAS_PATH="config/prometheus_aliases.json"

# SkyWalking GraphQL endpoint and optional token
export SKYWALKING_BASE_URL="http://localhost:12800/graphql"
export SKYWALKING_TOKEN=""
```

Testing
-------
Install test dependencies and run the test suite from the project root:

```bash
python -m pip install -e '.[tests]'
python -m pytest -q
```

Notes on testing and development
--------------------------------
- All external HTTP/GraphQL calls are made via injectable clients to simplify testing and mocking.
- Server registration logic can be stubbed in tests to avoid import-time side effects.
- Configuration files under `config/` (aliases, stream catalogs) are lazily loaded when present.

Contributing
------------
Contributions are welcome. Please open issues or PRs, run tests locally, and keep changes focused and well‑documented.
