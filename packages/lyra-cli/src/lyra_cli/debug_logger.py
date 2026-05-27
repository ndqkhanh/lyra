"""Debug logger for tracing LLM API calls."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

# Create logs directory
LOGS_DIR = Path.home() / ".lyra" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Create debug log file with timestamp
LOG_FILE = LOGS_DIR / f"lyra_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Configure logger
logger = logging.getLogger("lyra_debug")
logger.setLevel(logging.DEBUG)

# File handler
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console handler (only for errors)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)
console_formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


def log_api_call(provider: str, model: str, prompt: str, **kwargs: Any) -> None:
    """Log an LLM API call."""
    logger.info(f"=== API CALL START ===")
    logger.info(f"Provider: {provider}")
    logger.info(f"Model: {model}")
    logger.info(f"Prompt length: {len(prompt)} chars")
    logger.info(f"Prompt preview: {prompt[:500]}...")
    logger.info(f"Full prompt (first 1000 chars): {prompt[:1000]}")
    for key, value in kwargs.items():
        logger.info(f"{key}: {value}")
    logger.info(f"=== API CALL END ===")


def log_api_response(provider: str, model: str, response: str, **kwargs: Any) -> None:
    """Log an LLM API response."""
    logger.info(f"=== API RESPONSE START ===")
    logger.info(f"Provider: {provider}")
    logger.info(f"Model: {model}")
    logger.info(f"Response length: {len(response)} chars")
    logger.info(f"Response preview: {response[:500]}...")
    logger.info(f"Full response: {response}")
    for key, value in kwargs.items():
        logger.info(f"{key}: {value}")
    logger.info(f"=== API RESPONSE END ===")


def log_error(error: Exception, context: str = "") -> None:
    """Log an error."""
    logger.error(f"ERROR in {context}: {type(error).__name__}: {str(error)}")


def log_info(message: str) -> None:
    """Log an info message."""
    logger.info(message)


def log_warning(message: str) -> None:
    """Log a warning message."""
    logger.warning(message)


# Print log file location on import
print(f"🔍 Debug logging enabled: {LOG_FILE}")
