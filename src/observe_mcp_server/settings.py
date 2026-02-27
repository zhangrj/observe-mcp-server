from __future__ import annotations

from typing import Literal, Optional

from pydantic import AnyHttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Transport = Literal["stdio", "sse", "streamable-http"]


class MCPSettings(BaseSettings):
    """MCP server runtime settings (transport/host/port/path)."""

    model_config = SettingsConfigDict(
        env_prefix="OBSERVE_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    transport: Transport = "stdio"
    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    path: str = "/mcp"


class ToolsetSettings(BaseSettings):
    """Enable/disable toolsets (Phase-1 enables OpenObserve only)."""

    model_config = SettingsConfigDict(
        env_prefix="OBSERVE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enable_openobserve: bool = True
    enable_prometheus: bool = False
    enable_skywalking: bool = False

    # Optional prefix applied to all tool names (e.g. "staging_")
    tool_prefix: str = ""


class OpenObserveSettings(BaseSettings):
    """OpenObserve connection settings (HTTP Basic auth)."""

    model_config = SettingsConfigDict(
        env_prefix="OPENOBSERVE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: AnyHttpUrl
    org: str = "default"
    username: str
    password: SecretStr

    verify_ssl: bool = True
    timeout_seconds: float = 30.0

    # Guardrails for LLM-driven queries
    max_page_size: int = 500


# Future placeholders (Phase-2)
class PrometheusSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PROMETHEUS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: AnyHttpUrl
    username: Optional[str] = None
    password: Optional[SecretStr] = None
    token: Optional[SecretStr] = None
    verify_ssl: bool = True
    timeout_seconds: float = 30.0


class SkyWalkingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SKYWALKING_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: AnyHttpUrl
    token: Optional[SecretStr] = None
    timeout_seconds: float = 30.0