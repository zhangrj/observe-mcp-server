from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from fastmcp.exceptions import ValidationError, ToolError
from pydantic import Field
from typing_extensions import Annotated

from ..backends.prometheus import PrometheusBackend
from ..models import (
    PrometheusMetricCatalogItem,
    PrometheusMetricSchema,
    PrometheusQueryResponse,
)
from ..settings import PrometheusSettings


class _SimpleTTLCache:
    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    def get(self, key: str, ttl: int):
        entry = self._store.get(key)
        if not entry:
            return None
        value, ts = entry
        if time.time() - ts > ttl:
            try:
                del self._store[key]
            except Exception:
                pass
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, time.time())

    def clear(self, key: Optional[str] = None) -> None:
        if key is None:
            self._store.clear()
        else:
            self._store.pop(key, None)


def register_prometheus_tools(mcp, logger, tool_prefix: str = "") -> None:
    """Register a lightweight Prometheus toolset (MVP).

    Tools implemented (MVP):
      - get_metric_catalog
      - get_metric_schema
      - search_label_values
      - resolve_alias
      - lint_promql
      - execute_promql
    """

    def tool_name(name: str) -> str:
        return f"{tool_prefix}{name}" if tool_prefix else name

    cache = _SimpleTTLCache()

    async def _load_settings() -> PrometheusSettings:
        return PrometheusSettings()  # type: ignore

    async def _load_backend() -> PrometheusBackend:
        settings = await _load_settings()
        return PrometheusBackend(settings)

    async def _load_aliases(settings: PrometheusSettings) -> Dict[str, Any]:
        key = "__aliases__"
        cached = cache.get(key, settings.alias_ttl_seconds)
        if cached is not None:
            return cached
        aliases: Dict[str, Any] = {}
        if settings.alias_path:
            try:
                with open(settings.alias_path, "r", encoding="utf-8") as f:
                    aliases = json.load(f)
            except Exception:
                aliases = {}
        cache.set(key, aliases)
        return aliases

    @mcp.tool(
        name=tool_name("get_metric_catalog"),
        description=(
            "Return a paginated metric catalog summary (name/type/help/label_keys). Uses Prometheus '/api/v1/label/__name__/values'"
        ),
        annotations={
            "title": "Prometheus: Get Metric Catalog",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
        tags={"prometheus", "catalog"},
        meta={"backend": "prometheus", "phase": "2"},
    )
    async def get_metric_catalog(
        prefix: Annotated[Optional[str], Field(description="Optional metric name prefix") ] = None,
        contains: Annotated[Optional[str], Field(description="Optional substring filter") ] = None,
        type: Annotated[Optional[str], Field(description="Unused for MVP; placeholder for metric type filter")] = None,
        limit: Annotated[int, Field(description="Max results to return")] = 200,
        cursor: Annotated[Optional[str], Field(description="Not implemented in MVP; reserved for pagination")] = None,
    ) -> Dict[str, Any]:
        req_log = logger.bind(tool="get_metric_catalog")
        req_log.info("request", prefix=prefix, contains=contains, limit=limit)
        try:
            settings = await _load_settings()
            backend = await _load_backend()

            cache_key = "catalog_all"
            cached = cache.get(cache_key, settings.catalog_ttl_seconds)
            metrics: List[str]
            cache_hit = cached is not None
            if cached is None:
                metrics = await backend.list_metrics()
                cache.set(cache_key, metrics)
            else:
                metrics = cached

            # simple filtering
            filtered = []
            for m in metrics:
                if prefix and not m.startswith(prefix):
                    continue
                if contains and contains not in m:
                    continue
                filtered.append(m)
                if len(filtered) >= limit:
                    break

            items = [PrometheusMetricCatalogItem(name=m).dict() for m in filtered]
            req_log.info("success", count=len(items), cache_hit=cache_hit)
            return {"metrics": items, "cache_hit": cache_hit}
        except Exception as e:
            req_log.error("failure", error=str(e))
            raise ToolError(f"get_metric_catalog failed: {e}")

    @mcp.tool(
        name=tool_name("get_metric_schema"),
        description=("Return label keys and light schema hints for a single metric. Includes small label value preview if requested."),
        annotations={"title": "Prometheus: Get Metric Schema", "readOnlyHint": True},
        tags={"prometheus", "schema"},
        meta={"backend": "prometheus", "phase": "2"},
    )
    async def get_metric_schema(
        metric_name: Annotated[str, Field(description="Metric name to inspect")],
        include_label_values_preview: Annotated[bool, Field(description="Whether to include a small preview of label values")] = True,
    ) -> Dict[str, Any]:
        req_log = logger.bind(tool="get_metric_schema")
        req_log.info("request", metric=metric_name, preview=include_label_values_preview)
        try:
            settings = await _load_settings()
            backend = await _load_backend()

            cache_key = f"schema:{metric_name}"
            cached = cache.get(cache_key, settings.schema_ttl_seconds)
            if cached is not None:
                return {"schema": cached, "cache_hit": True}

            # infer label keys from series API (may be heavy; MVP keeps it simple)
            series = await backend.series_for_metric(metric_name)
            label_keys = set()
            for s in series:
                if isinstance(s, dict):
                    label_keys.update(set(s.keys()) - {"__name__"})

            label_preview = {}
            if include_label_values_preview:
                # for each label, fetch top N via label_values endpoint (may be coarse)
                for label in sorted(label_keys):
                    try:
                        vals = await backend.label_values(label)
                        label_preview[label] = (vals or [])[:10]
                    except Exception:
                        label_preview[label] = []

            schema = PrometheusMetricSchema(
                name=metric_name,
                labels=sorted(label_keys),
                label_preview=label_preview,
            ).dict()
            cache.set(cache_key, schema)
            req_log.info("success", labels=len(label_keys))
            return {"schema": schema, "cache_hit": False}
        except Exception as e:
            req_log.error("failure", error=str(e))
            raise ToolError(f"get_metric_schema failed: {e}")

    @mcp.tool(
        name=tool_name("search_label_values"),
        description=("Return a preview of label values for a given metric and label name. Returns top-N sample values."),
        annotations={"title": "Prometheus: Search Label Values", "readOnlyHint": True},
        tags={"prometheus", "labels"},
        meta={"backend": "prometheus", "phase": "2"},
    )
    async def search_label_values(
        metric_name: Annotated[Optional[str], Field(description="Optional metric to limit search") ] = None,
        label_name: Annotated[str, Field(description="Label name to inspect")] = "",
        matchers: Annotated[Optional[str], Field(description="Optional matchers; not implemented in MVP")] = None,
        time_range: Annotated[Optional[str], Field(description="Time range string, e.g. 1h; used for future improvements")] = None,
        limit: Annotated[int, Field(description="Max preview values to return")] = 20,
    ) -> Dict[str, Any]:
        req_log = logger.bind(tool="search_label_values")
        req_log.info("request", metric=metric_name, label=label_name, limit=limit)
        try:
            settings = await _load_settings()
            backend = await _load_backend()

            # attempt to use label_values endpoint (fast) — fallback to series scan if needed
            try:
                vals = await backend.label_values(label_name)
                preview = (vals or [])[:limit]
            except Exception:
                # fallback: use series_for_metric to gather values
                preview = []
                if metric_name:
                    series = await backend.series_for_metric(metric_name)
                    seen = set()
                    for s in series:
                        if not isinstance(s, dict):
                            continue
                        v = s.get(label_name)
                        if v is not None and v not in seen:
                            seen.add(v)
                            preview.append(v)
                            if len(preview) >= limit:
                                break

            is_high_card = len(preview) >= limit
            req_log.info("success", preview_count=len(preview), high_cardinality=is_high_card)
            return {"preview": preview, "high_cardinality": is_high_card}
        except Exception as e:
            req_log.error("failure", error=str(e))
            raise ToolError(f"search_label_values failed: {e}")

    @mcp.tool(
        name=tool_name("resolve_alias"),
        description=("Resolve a business alias / intent to candidate metrics and recommended query patterns."),
        annotations={"title": "Prometheus: Resolve Alias", "readOnlyHint": True},
        tags={"prometheus", "alias"},
        meta={"backend": "prometheus", "phase": "2"},
    )
    async def resolve_alias(
        alias_or_intent: Annotated[str, Field(description="Business term or short intent")],
        limit: Annotated[int, Field(description="Max candidates to return")] = 5,
    ) -> Dict[str, Any]:
        req_log = logger.bind(tool="resolve_alias")
        req_log.info("request", alias=alias_or_intent)
        try:
            settings = await _load_settings()
            aliases = await _load_aliases(settings)
            q = alias_or_intent.lower()
            matches = []
            for name, entry in (aliases.items() if isinstance(aliases, dict) else []):
                if q == name.lower() or q in name.lower():
                    matches.append({"alias": name, "entry": entry})
                    if len(matches) >= limit:
                        break

            return {"matches": matches, "count": len(matches)}
        except Exception as e:
            req_log.error("failure", error=str(e))
            raise ToolError(f"resolve_alias failed: {e}")

    @mcp.tool(
        name=tool_name("lint_promql"),
        description=("Lightweight PromQL lint: basic sanity checks and simple advice. Not a full parser.") ,
        annotations={"title": "Prometheus: Lint PromQL", "readOnlyHint": True},
        tags={"prometheus", "lint"},
        meta={"backend": "prometheus", "phase": "2"},
    )
    async def lint_promql(
        query: Annotated[str, Field(description="PromQL to lint")],
    ) -> Dict[str, Any]:
        req_log = logger.bind(tool="lint_promql")
        try:
            if not query or not query.strip():
                return {"ok": False, "issues": ["empty query"], "severity": "error"}
            issues = []
            if len(query) > 2000:
                issues.append("query length unusually long")
            # simple bracket balance check
            if query.count("(") != query.count(")"):
                issues.append("unbalanced parentheses")
            if query.count("{") != query.count("}"):
                issues.append("unbalanced braces")
            ok = len(issues) == 0
            return {"ok": ok, "issues": issues, "severity": "warning" if issues else "ok"}
        except Exception as e:
            req_log.error("failure", error=str(e))
            raise ToolError(f"lint_promql failed: {e}")

    @mcp.tool(
        name=tool_name("execute_promql"),
        description=("Execute PromQL (instant or range) with simple guardrails. Returns raw Prometheus response."),
        annotations={"title": "Prometheus: Execute PromQL", "readOnlyHint": True},
        tags={"prometheus", "query"},
        meta={"backend": "prometheus", "phase": "2"},
    )
    async def execute_promql(
        query: Annotated[str, Field(description="PromQL expression")],
        mode: Annotated[str, Field(description="instant | range")] = "instant",
        time: Annotated[Optional[str], Field(description="RFC3339 or unix time for instant queries")] = None,
        start: Annotated[Optional[str], Field(description="Start time for range queries")] = None,
        end: Annotated[Optional[str], Field(description="End time for range queries")] = None,
        step: Annotated[Optional[str], Field(description="Step for range queries, e.g., 15s") ] = None,
        limit: Annotated[int, Field(description="soft limit for results; not strictly enforced") ] = 1000,
        timeout: Annotated[Optional[int], Field(description="Optional timeout seconds") ] = None,
    ) -> Dict[str, Any]:
        req_log = logger.bind(tool="execute_promql")
        req_log.info("request", mode=mode, query=query[:160])
        try:
            settings = await _load_settings()
            backend = await _load_backend()

            if mode == "instant":
                resp = await backend.query_instant(query=query, time=time)
            else:
                if not (start and end and step):
                    raise ValidationError("start/end/step are required for range queries")
                resp = await backend.query_range(query=query, start=start, end=end, step=step)

            return {"result": resp}
        except Exception as e:
            req_log.error("failure", error=str(e))
            raise ToolError(f"execute_promql failed: {e}")
