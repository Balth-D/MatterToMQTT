"""Logging configuration."""

import logging


class LoggerConfig:
    """Manages logger setup."""

    @staticmethod
    def setup(debug_level: str) -> logging.Logger:
        """Setup logger with the specified debug level."""
        log_level = getattr(logging, debug_level.upper(), logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)

        # Configure root logger so all loggers inherit the configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.handlers.clear()
        root_logger.addHandler(handler)

        return root_logger
