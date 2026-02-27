from __future__ import annotations

import logging
import os
import sys
import structlog


def setup_logging(logger_name: str = "observe_mcp_server") -> structlog.BoundLogger:
    """Configure structured JSON logging to stderr.

    - Do NOT log secrets (passwords/tokens).
    - Use OBSERVE_LOG_LEVEL to control verbosity.
    """
    level_str = os.getenv("OBSERVE_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=level,
    )

    return structlog.get_logger(logger_name)


def get_logger(logger_name: str = "observe_mcp_server") -> structlog.BoundLogger:
    return structlog.get_logger(logger_name)