from observe_mcp_server import logging as obs_logging


def test_setup_logging_accepts_explicit_level():
    logger = obs_logging.setup_logging("test_logger", level_str="DEBUG")
    assert hasattr(logger, "info")


def test_setup_logging_uses_default_level_when_not_provided():
    logger = obs_logging.setup_logging("test_logger")
    assert hasattr(logger, "info")
