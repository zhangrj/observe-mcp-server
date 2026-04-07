# observe-mcp-server

Phase-1 implements OpenObserve tools and a small Prometheus MVP. Available OpenObserve tools:

- `openobserve_stream_list` — 列出可用 streams（logs/metrics/traces）。在查询前先调用以选择目标 stream。
- `openobserve_list_stream_schema` — 获取流的 schema（字段名/类型），用于构建 WHERE/SELECT 子句。
- `openobserve_field_values` — 使用 `_values` API 预览字段的 top-N 值（需提供微秒时间窗），用于选择过滤值或排查样例。
- `openobserve_sql_lint` — 基于流 schema 的轻量 SQL 检查，提示缺失时间窗、警告 `SELECT *`、并给出建议 SQL；推荐在执行前或通过 `validate_only` 使用。
- `openobserve_logs_query` — 执行实际搜索（POST /api/{org}/_search），支持 `validate_only` 模式先运行 lint 后再执行查询。

推荐的 agent 查询步骤（强烈建议按此顺序，能降低风险与成本）：
1. 使用 `openobserve_stream_list` 选择目标 stream；
2. 使用 `openobserve_list_stream_schema` 查看 stream 的 schema；
3. 使用 `openobserve_field_values` 预览字段值（如需）；
4. 使用 `openobserve_sql_lint` 对 SQL/意图进行校验（或在 `openobserve_logs_query` 中开启 `validate_only`）；
5. 最后使用 `openobserve_logs_query` 执行查询（提供 `start_time_us` / `end_time_us`）。

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
uv pip install -e .
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

## Testing

Install test dependencies and run the test suite from the project root:

```bash
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate     # On Windows
uv pip install -e '.[tests]'
pytest -q
```

Note: run commands from the project root so the `.env` file and `pyproject.toml` are discovered correctly.

## Prometheus MCP 支持（MVP）

本仓库包含对 Prometheus 的基础 MCP 支持（MVP），实现的工具包括：

- `get_metric_catalog` — 列出/分页 metrics（带内存缓存 + TTL）；
- `get_metric_schema` — 获取 metric 的 label 列表与轻量 preview；
- `search_label_values` — 给定 label 与 matchers 时返回 top-N 值预览；
- `resolve_alias` — 将业务别名解析为 Prometheus 查询目标（从 `config/prometheus_aliases.json` 加载）；
- `lint_promql` — 基本 PromQL 静态校验与建议；
- `execute_promql` — 执行 instant 或 range 查询，带执行 guardrails。

配置示例（在项目根目录的 `.env` 或环境变量中设置）：

```bash
# 启用 Prometheus 工具集（也可在 `ToolsetSettings` 中配置）
export OBSERVE_ENABLE_PROMETHEUS=true

# Prometheus URL
export PROMETHEUS_URL="http://prometheus.example:9090"

# 可选：指定 alias 配置路径（JSON）
export PROMETHEUS_ALIAS_PATH="config/prometheus_aliases.json"
```

Prometheus 推荐工作流（示例）：

1. 使用 `resolve_alias("错误率")` 或 `get_metric_catalog` 缩小候选 metric；
2. 使用 `get_metric_schema(metric_name)` 查看 labels 与可用字段；
3. 使用 `search_label_values` 或 preview 功能查证关键 label 的可能值；
4. 用 `lint_promql` 检查生成的 PromQL；
5. 用 `execute_promql` 执行并读取结果。

示例 alias 配置文件：`config/prometheus_aliases.json`（懒加载 + TTL）。

## SkyWalking (GraphQL)

本仓库提供对 SkyWalking OAP 的基础读取工具（GraphQL）。工具包括：

- `list_layers` — 列出可用 layer（例如 HTTP、DB）
- `list_services` — 列出服务，可按 layer 过滤
- `list_instances` — 列出实例（service_id）
- `list_endpoints` — 列出服务的 endpoints
- `list_processes` — 列出服务进程
- `query_traces` — 按条件查询 traces（建议先用 list_services 缩小范围）
- `get_trace_detail` — 按 `trace_id` 查看单条 trace 的详细 spans

配置示例请在 `.env` 中设置 `SKYWALKING_BASE_URL`（例如 `http://localhost:12800/graphql`）和可选的 `SKYWALKING_TOKEN`。
