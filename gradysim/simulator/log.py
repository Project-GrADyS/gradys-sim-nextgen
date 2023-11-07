"""
Logging is an important part of any software. It helps users and developers understand what is happening during the
execution of the program. When running GrADyS-SIM TNG in prototype-mode logging is automatically configured for you,
users that want to make use of this logging should use `logging.getLogger(SIMULATION_LOGGER)` where SIMULATION_LOGGER
can be imported from this file.

The logger annotates the output with timing information and execution context to improve understanding.
"""

import logging
from datetime import timedelta
from pathlib import Path
from typing import Optional

SIMULATION_LOGGER = "gradysim-sim"
"""
Use this logger to have properly formatted logs. Beware that if you use logging in your protocols the logs will only
be properly formatted when you are running in prototype-mode.

Use with `logging.getLogger(SIMULATION_LOGGER)`
"""


class SimulationFormatter(logging.Formatter):
    """
    Custom logging formatter responsible for annotating the simulation logs with useful information about
    timing and execution context.
    """
    def __init__(self):
        super().__init__("%(message)s")

    _prefix: str = ""

    def scope_event(self, iteration: int, timestamp: float, context: str):
        """
        Call this method to update the formatter's annotation with current information. This module is called by
        the [Simulator][gradysim.simulator.simulation.Simulator].

        Args:
            iteration: Current iteration the simulation is at
            timestamp: Simulation timestamp in seconds
            context: Context of what's being currently executed in the simulation

        Returns:

        """
        self._prefix = f"[it={iteration} time={timedelta(seconds=timestamp)} | {context}] "

    def clear_iteration(self):
        self._prefix = ""

    def format(self, record: logging.LogRecord) -> str:
        log = super().format(record)
        return f"{record.levelname: <8} {self._prefix}{log}"


def setup_simulation_formatter(debug: bool, log_file: Optional[Path]) -> SimulationFormatter:
    """
    Sets up the logger for the simulation. Called before the simulation starts to configure
    the `SIMULATION_LOGGER` logger.

    Args:
        debug: Include DEBUG level logs
        log_file: Configure a logging handler to save logs in a file. Optional.

    Returns:
        The formatter instance. Is returned because it needs to be updated with current simulation information.
    """
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
