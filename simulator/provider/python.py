import logging

from simulator.handler.timer import TimerHandler
from simulator.log import SIMULATION_LOGGER
from protocol.messages.communication import CommunicationCommand
from protocol.messages.mobility import MobilityCommand
from simulator.handler.mobility import MobilityHandler
from simulator.node import Node
from simulator.handler.communication import CommunicationHandler
from simulator.provider.interface import IProvider


class PythonProvider(IProvider):
    def __init__(self, node: Node,
                 communication_handler: CommunicationHandler = None,
                 timer_handler: TimerHandler = None,
                 mobility_handler: MobilityHandler = None):
        self.node = node
        self.communication_handler = communication_handler
        self.timer_handler = timer_handler
        self.mobility_handler = mobility_handler
        self._logger = logging.getLogger(SIMULATION_LOGGER)

    def send_communication_command(self, command: CommunicationCommand):
        if self.communication_handler is not None:
            self.communication_handler.handle_command(command, self.node)
        else:
            self._logger.warning("Communication commands cannot be sent without a "
                                 "communication handler is configured")

    def send_mobility_command(self, command: MobilityCommand):
        if self.mobility_handler is not None:
            self.mobility_handler.handle_command(command, self.node)
        else:
            self._logger.warning("Mobility commands cannot be sent without a "
                                 "mobility handler is configured")

    def schedule_timer(self, timer: str, timestamp: float):
        if self.timer_handler is not None:
            self.timer_handler.set_timer(timer, timestamp, self.node)
        else:
            self._logger.warning("Timer cannot be set with no timer handler configured")

    def current_time(self) -> float:
        if self.timer_handler is not None:
            return self.timer_handler.get_current_time()
        else:
            self._logger.warning("Current time cannot be retrieved when no timer handler is configured. This function "
                                 "will always return zero.")
            return 0