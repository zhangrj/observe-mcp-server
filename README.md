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
Environment variables are the primary configuration mechanism. The table below lists supported environment variables, whether they are optional, and their default values.

| Variable | Description | Optional | Default |
|---|---:|---:|---|
| `OBSERVE_MCP_LOG_LEVEL` | Log level for the service | yes | `INFO` |
| `OBSERVE_MCP_TRANSPORT` | MCP transport: `stdio` `sse` `streamable-http` | yes | `stdio` |
| `OBSERVE_MCP_BIND_HOST` | Host address to bind (when using streamable-http or sse) | yes | `127.0.0.1` |
| `OBSERVE_MCP_BIND_PORT` | Port to bind the MCP server (when using streamable-http or sse) | yes | `8000` |
| `OBSERVE_MCP_PATH` | HTTP path for MCP endpoint (when using streamable-http or sse) | yes | `/mcp` |
| `OBSERVE_ENABLE_OPENOBSERVE` | Enable OpenObserve tools (logs) | yes | `true` |
| `OBSERVE_ENABLE_PROMETHEUS` | Enable Prometheus tools | yes | `true` |
| `OBSERVE_ENABLE_SKYWALKING` | Enable SkyWalking tools | yes | `true` |
| `OBSERVE_TOOL_PREFIX` | Prefix applied to all tool names (optional) | yes | (empty) |
| `PROMETHEUS_URL` | Prometheus HTTP API base URL | REQUIRED when `OBSERVE_ENABLE_PROMETHEUS=true` | (no default) |
| `PROMETHEUS_TOKEN` | Prometheus bearer token (optional) | yes | (empty) |
| `PROMETHEUS_USERNAME` | Prometheus basic auth username (optional) | yes | (empty) |
| `PROMETHEUS_PASSWORD` | Prometheus basic auth password (optional) | yes | (empty) |
| `PROMETHEUS_VERIFY_SSL` | Verify TLS for Prometheus endpoints | yes | `true` |
| `PROMETHEUS_TIMEOUT_SECONDS` | Request timeout (seconds) for Prometheus | yes | `30` |
| `PROMETHEUS_ALIAS_PATH` | Path to alias JSON file (optional) | yes | `config/prometheus_aliases.json` |
| `PROMETHEUS_CATALOG_TTL_SECONDS` | Cache TTL for metric catalog (seconds) | yes | `600` |
| `PROMETHEUS_SCHEMA_TTL_SECONDS` | Cache TTL for metric schema (seconds) | yes | `600` |
| `PROMETHEUS_LABEL_PREVIEW_TTL_SECONDS` | Cache TTL for label preview (seconds) | yes | `180` |
| `PROMETHEUS_ALIAS_TTL_SECONDS` | Cache TTL for alias mapping (seconds) | yes | `1800` |
| `OPENOBSERVE_BASE_URL` | OpenObserve API base URL (logs only) | REQUIRED when `OBSERVE_ENABLE_OPENOBSERVE=true` | (no default) |
| `OPENOBSERVE_ORG` | Organization/tenant for OpenObserve | yes | `default` |
| `OPENOBSERVE_USERNAME` | OpenObserve username (HTTP Basic auth) | REQUIRED when `OBSERVE_ENABLE_OPENOBSERVE=true` | (no default) |
| `OPENOBSERVE_PASSWORD` | OpenObserve password (HTTP Basic auth) | REQUIRED when `OBSERVE_ENABLE_OPENOBSERVE=true` | (no default) |
| `OPENOBSERVE_VERIFY_SSL` | Verify TLS for OpenObserve endpoints | yes | `true` |
| `OPENOBSERVE_TIMEOUT_SECONDS` | Request timeout (seconds) for OpenObserve | yes | `30` |
| `OPENOBSERVE_MAX_PAGE_SIZE` | Max page size for OpenObserve list/preview | yes | `500` |
| `OPENOBSERVE_STREAM_CATALOG_PATH` | Optional local stream catalog JSON path | yes | (empty) |
| `SKYWALKING_BASE_URL` | SkyWalking GraphQL endpoint | REQUIRED when `OBSERVE_ENABLE_SKYWALKING=true` | (no default) |
| `SKYWALKING_TOKEN` | SkyWalking bearer token (optional) | yes | (empty) |
| `SKYWALKING_VERIFY_SSL` | Verify TLS for SkyWalking endpoints | yes | `true` |
| `SKYWALKING_TIMEOUT_SECONDS` | Request timeout (seconds) for SkyWalking | yes | `30` |

Notes:

- Variables marked as "REQUIRED when `OBSERVE_ENABLE_* = true`" must be provided if the corresponding toolset is enabled; otherwise they can be omitted.
- File paths such as `PROMETHEUS_ALIAS_PATH` and `OPENOBSERVE_STREAM_CATALOG_PATH` are optional; if provided they are read lazily at runtime.
- Boolean values are read as strings; the loader treats `true`, `True`, `1` as truthy in typical environments.


Configuration Files
-------------------
The project supports optional JSON configuration files under the `config/` directory to enhance query capabilities with business-friendly aliases and stream metadata.

### Prometheus Aliases (`config/prometheus_aliases.json`)
This file maps business-friendly metric aliases to actual Prometheus metric names and recommended query patterns. It enables the `resolve_alias` tool to translate user-friendly terms into executable PromQL queries.

**Structure:**
```json
{
  "alias_name": {
    "description": "Human-readable description of the metric",
    "target_metrics": ["actual_metric_name_1", "actual_metric_name_2"],
    "recommended_filters": ["label_matcher1", "label_matcher2"],
    "recommended_query_patterns": ["complete_promql_expression"]
  }
}
```

**Example entries:**
- `error_rate`: Maps to HTTP error rate calculations using `http_requests_total` or `http_server_requests_total` with status code filtering.
- `qps`: Maps to request rate queries using `rate()` function on request counter metrics.

**Usage:** When a user queries for "error rate" or "QPS", the `resolve_alias` tool automatically resolves these to the appropriate PromQL expressions based on this configuration.

**Configuration:** The path can be customized via the `PROMETHEUS_ALIAS_PATH` environment variable (default: `config/prometheus_aliases.json`).

### OpenObserve Stream Catalog (`config/openobserve_stream_catalog.json`)
This file provides metadata about OpenObserve log streams, including descriptions, searchable keywords, and alternative names (aliases). It enhances stream discovery and helps users find the right log stream for their queries.

**Structure:**
```json
{
  "stream_name": {
    "desc": "Detailed description of the stream's purpose and content",
    "keywords": ["keyword1", "keyword2", "context_tag"],
    "aliases": ["alternative name 1", "alternative name 2"]
  }
}
```

**Usage:** The stream catalog metadata assists the `openobserve_stream_list` tool in providing richer context when listing available streams, making it easier for users to identify the correct stream based on environment (dev/sit/bms), component (apisix/business logs), or cluster name.

**Configuration:** The path can be customized via the `OPENOBSERVE_STREAM_CATALOG_PATH` environment variable (default: empty, meaning no catalog file is loaded). If not set, stream listing will still work but without enhanced metadata.

**Best Practices:**
- Keep keywords specific and relevant to help AI agents match user queries accurately.
- Include common abbreviations and alternative naming conventions in the `aliases` array.
- Use clear, descriptive text in the `desc` field to provide context about the stream's purpose.


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
