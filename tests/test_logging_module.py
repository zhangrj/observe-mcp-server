import os

from observe_mcp_server import logging as obs_logging


def test_setup_logging_respects_env(monkeypatch):
    monkeypatch.setenv("OBSERVE_LOG_LEVEL", "DEBUG")
    logger = obs_logging.setup_logging("test_logger")
    assert hasattr(logger, "info")
    # cleanup
    try:
        del os.environ["OBSERVE_LOG_LEVEL"]
    except KeyError:
        pass
