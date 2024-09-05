"""
Logging is an important part of any software. It helps users and developers understand what is happening during the
execution of the program. When running GrADyS-SIM NextGen in prototype-mode logging is automatically configured for you.

The logger annotates the output with timing information and execution context to improve understanding.
"""

import logging
from pathlib import Path
from typing import Optional

from gradysim.simulator.node import Node





class SimulationFormatter(logging.Formatter):
    """
    Custom logging formatter responsible for annotating the simulation logs with useful information about
    timing and execution context.
    """
    def __init__(self):
        super().__init__("%(message)s")

    prefix: str = ""

    def clear_iteration(self):
        self.prefix = ""

    def format(self, record: logging.LogRecord) -> str:
        log = super().format(record)
        return f"{record.levelname: <8} {self.prefix}{log}"


def setup_simulation_formatter(debug: bool, log_file: Optional[Path]) -> SimulationFormatter:
    """
    Sets up the logger for the simulation. Called before the simulation starts to configure
    the logger.

    Args:
        debug: Include DEBUG level logs
        log_file: Configure a logging handler to save logs in a file. Optional.

    Returns:
        The formatter instance. Is returned because it needs to be updated with current simulation information.
    """
    logger = logging.getLogger()

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

def label_node(node: Node) -> str:
    try:
        protocol_type_name = node.protocol_encapsulator.protocol.__class__.__name__
    except AttributeError:
        protocol_type_name = 'Node'
    return f"{protocol_type_name} {node.id}"