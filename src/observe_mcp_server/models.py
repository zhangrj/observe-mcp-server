from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StreamType(str, Enum):
    logs = "logs"
    metrics = "metrics"
    traces = "traces"


class OpenObserveStream(BaseModel):
    """Single stream entry returned by OpenObserve streams API."""
    name: str
    storage_type: Optional[str] = None
    stream_type: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None
    schema_: Optional[List[Dict[str, Any]]] = Field(default=None, alias="schema")
    settings: Optional[Dict[str, Any]] = None


class OpenObserveStreamListResponse(BaseModel):
    """Response schema from GET /api/{org}/streams."""
    list: List[OpenObserveStream]


class OpenObserveSearchResponse(BaseModel):
    """Response schema from POST /api/{org}/_search."""
    took: int = Field(description="Query execution time in milliseconds")
    hits: List[Dict[str, Any]] = Field(description="Matched records")
    total: int = Field(description="Total matched records")
    from_: int = Field(alias="from", description="Offset from request")
    size: int = Field(description="Limit from request")
    scan_size: int = Field(description="Scanned data size in MB")