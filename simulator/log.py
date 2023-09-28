import logging
from datetime import timedelta

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


def setup_simulation_formatter(debug=False) -> SimulationFormatter:
    logger = logging.getLogger(SIMULATION_LOGGER)
    handler = logging.StreamHandler()
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    formatter = SimulationFormatter()
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return formatter
