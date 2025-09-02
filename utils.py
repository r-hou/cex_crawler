from loguru import logger
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Ensure logs directory exists at project root
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(ROOT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Filename is current Hong Kong time
_hk_now = datetime.now(ZoneInfo("Asia/Hong_Kong"))
_log_filename = _hk_now.strftime("%Y-%m-%d_%H-%M-%S") + ".log"
_log_path = os.path.join(LOG_DIR, _log_filename)

# Filters to separate sinks
def _file_filter(record):
    return record["extra"].get("target") == "file"

def _console_filter(record):
    return record["extra"].get("target") == "console"

# Avoid duplicate default sink
logger.remove()

# File sink (Hong Kong time filename)
logger.add(
    _log_path,
    level="INFO",
    encoding="utf-8",
    enqueue=True,
    retention="14 days",
    backtrace=True,
    diagnose=False,
    filter=_file_filter,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
)

# Console sink
logger.add(
    sys.stderr,
    level="INFO",
    enqueue=True,
    colorize=True,
    filter=_console_filter,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
)

# Two logger instances for external use
file_logger = logger.bind(target="file")
console_logger = logger.bind(target="console")

__all__ = ["file_logger", "console_logger"]