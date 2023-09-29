import logging
from datetime import timedelta
from pathlib import Path
from typing import Optional

SIMULATION_LOGGER = "gradys-sim"

class SimulationFormatter(logging.Formatter):
    def __init__(self):
        super().__init__("%(levelname)s: %(message)s")

    _prefix: str = ""

    def scope_event(self, iteration: int, timestamp: float, handler: str):
        self._prefix = f"[it={iteration} time={timedelta(seconds=timestamp)} | {handler}] "

    def clear_iteration(self):
        self._prefix = ""

    def format(self, record: logging.LogRecord) -> str:
        log = super().format(record)
        return self._prefix + log


def setup_simulation_formatter(debug: bool, log_file: Optional[Path]) -> SimulationFormatter:
    logger = logging.getLogger(SIMULATION_LOGGER)

    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    formatter = SimulationFormatter()
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file is not None:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return formatter
