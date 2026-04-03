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

本仓库包含对 Prometheus 的基础 MCP 支持（MVP），实现了以下 tool：

- `get_metric_catalog`：获取 metric 目录摘要（带内存缓存 + TTL）。
- `get_metric_schema`：获取单个 metric 的 label 列表与值预览（轻量）。
- `search_label_values`：为指定 label 返回值预览（top-N）。
- `resolve_alias`：业务别名解析（从 `config/prometheus_aliases.json` 加载）。
- `lint_promql`：PromQL 简单静态校验。
- `execute_promql`：执行 instant 或 range 查询。

配置示例（在项目根目录的 `.env` 或环境变量中设置）：

```bash
# 启用 Prometheus 工具集
export OBSERVE_ENABLE_PROMETHEUS=true

# Prometheus URL
export PROMETHEUS_URL="http://prometheus.example:9090"

# 可选：指定 alias 配置路径
export PROMETHEUS_ALIAS_PATH="config/prometheus_aliases.json"
```

注意：`ToolsetSettings` 中默认 `enable_prometheus` 为 `False`，可通过环境变量或直接修改配置启用。

工作流示例（推荐）：

1. 先调用 `resolve_alias("错误率")` 或查看 `get_metric_catalog` 来收窄候选 metric。
2. 对候选 metric 调用 `get_metric_schema(metric_name)` 获取可用 labels 与 preview。
3. 基于 schema 构建 PromQL，调用 `lint_promql` 做静态检查。
4. 使用 `execute_promql` 执行查询并查看结果。

示例 alias 文件位于 `config/prometheus_aliases.json`，可按需修改并热加载（在 MVP 中为懒加载 + TTL）。
