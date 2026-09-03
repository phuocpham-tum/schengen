from loguru import logger
import sys
from pathlib import Path
import time

# get current time for log file naming
current_time = time.strftime("%Y-%m-%d_%H-%M-%S")

LOG_DIR = Path("logs") / current_time
LOG_DIR.mkdir(exist_ok=True, parents=True)
MODULE_LEVELS = {
    "src.schengen": "DEBUG",
    "__main__": "DEBUG",  # to capture logs when train.py is run directly
    "src.routing.routing_2": "DEBUG",
    "src.utils.netlist_analyzer": "DEBUG",
    "src.placements.placer": "DEBUG",
    "src.constraints.placement": "DEBUG",
    "src.constraints.orientation": "DEBUG",
    "src.constraints.library": "DEBUG",
}


def filter_fn(module_name):
    def f(record):
        name = record["name"]
        # Match both the module import case (src.schengen) and execution case (__main__)
        # When train.py runs as main, record["name"] is "__main__"
        # When train.py is imported, record["name"] is "src.schengen"
        if module_name == "src.schengen" and name == "__main__":
            return (
                True  # Log __main__ to src.schengen.log when running train.py directly
            )
        return name.endswith(module_name)

    def f_filepath(record):
        # record["file"].path is often more reliable than name.
        # For example, when train.py is run directly, name is "__main__", but file path will still contain "train.py"
        filepath = record["file"].path.replace("/", ".")
        return module_name in filepath

    return f_filepath


def setup_logger():
    logger.remove()

    message_fmt = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    for module, level in MODULE_LEVELS.items():
        logger.add(
            LOG_DIR / f"{module}.log",
            level=level,
            rotation="5 MB",  # specifies a condition in which the current log file will be closed and a new file will be created.
            retention="7 days",  # specifies how log each log file will be retained before it is deleted from the filesystem.
            compression="zip",
            filter=filter_fn(module),
            format=message_fmt,
        )
        # Also log to stdout for real-time visibility
        logger.add(
            sys.stdout,
            level=level,
            filter=filter_fn(module),
            format=message_fmt,
        )

    logger.add(
        LOG_DIR / "app.log",
        level="INFO",
        rotation="10 MB",
        retention="10 days",  # specifies how log each log file will be retained before it is deleted from the filesystem.
        compression="zip",
        format=message_fmt,
    )
