from pydantic import SecretStr

from observe_mcp_server.models import OpenObserveSearchResponse, PrometheusMetricSchema


def test_openobserve_search_from_field():
    data = {"took": 10, "hits": [{"a": 1}], "total": 1, "from": 5, "size": 10, "scan_size": 0}
    obj = OpenObserveSearchResponse(**data)
    assert obj.from_ == 5
    assert obj.took == 10


def test_prometheus_schema_defaults():
    s = PrometheusMetricSchema(name="m")
    assert isinstance(s.labels, list)
    assert s.labels == []
