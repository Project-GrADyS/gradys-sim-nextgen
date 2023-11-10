"""
Encapsulates protocols that run in [prototype-mode][]. The encapsulator will wrap the protocol instance and handle
interactions with the python simulator. It will also inject a provider instance that translates the protocol's calls
into interactions with the python simulator.
"""

import logging
from typing import Type, Optional

from gradysim.protocol.interface import IProtocol, IProvider
from gradysim.encapsulator.interface import IEncapsulator
from gradysim.protocol.messages.communication import CommunicationCommand
from gradysim.protocol.messages.mobility import MobilityCommand
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.simulator.handler.mobility import MobilityHandler
from gradysim.simulator.log import SIMULATION_LOGGER
from gradysim.simulator.node import Node
from gradysim.simulator.handler.communication import CommunicationHandler


class PythonProvider(IProvider):
    """
    Handles protocols actions translating them into actions inside the python simulation
    """
    def __init__(self, node: Node,
                 communication_handler: Optional[CommunicationHandler] = None,
                 timer_handler: Optional[TimerHandler] = None,
                 mobility_handler: Optional[MobilityHandler] = None):
        """
        Instantiates a python provider

        Args:
            node: The node being encapsulated
            communication_handler: The communication handler if available
            timer_handler: The timer handler if available
            mobility_handler: The mobility handler if available
        """
        self.node = node
        self.communication_handler = communication_handler
        self.timer_handler = timer_handler
        self.mobility_handler = mobility_handler
        self._logger = logging.getLogger(SIMULATION_LOGGER)

    def send_communication_command(self, command: CommunicationCommand) -> None:
        """
        Forwards a communication command to the communication handler. If the simulation is running with no communication
        handler issues a warning and does nothing.

        Args:
            command: Communication command being sent
        """
        if self.communication_handler is not None:
            self.communication_handler.handle_command(command, self.node)
        else:
            self._logger.warning("Communication commands cannot be sent without a "
                                 "communication handler is configured")

    def send_mobility_command(self, command: MobilityCommand) -> None:
        """
        Forwards a mobility command to the mobility handler. If the simulation is running without a mobility handler
        issues a warning and does nothing.

        Args:
            command: Command being sent
        """
        if self.mobility_handler is not None:
            self.mobility_handler.handle_command(command, self.node)
        else:
            self._logger.warning("Mobility commands cannot be sent without a "
                                 "mobility handler is configured")

    def schedule_timer(self, timer: str, timestamp: float) -> None:
        """
        Schedules a timer using the timer handler. If one is not present in the simulation issues a warning and does
        nothing

        Args:
            timer: Timer being ser
            timestamp: Timestamp when it should fire

        Returns:

        """
        if self.timer_handler is not None:
            self.timer_handler.set_timer(timer, timestamp, self.node)
        else:
            self._logger.warning("Timer cannot be set with no timer handler configured")

    def current_time(self) -> float:
        """
        Returns the current time consulted from the timer handler. If one is not present issues a warning and returns
        zero.

        Returns:
            Simulation timestamp in seconds or zero if no timer handler is present
        """
        if self.timer_handler is not None:
            return self.timer_handler.get_current_time()
        else:
            self._logger.warning("Current time cannot be retrieved when no timer handler is configured. This function "
                                 "will always return zero.")
            return 0

    def get_id(self) -> int:
        """
        Returns the node's unique identifier in the simulation

        Returns:
            the node's unique identifier in the simulation
        """
        return self.node.id


class PythonEncapsulator(IEncapsulator):
    """
    Encapsulates the protocol to work with the python simulation.
    """

    def __init__(self,
                 node: Node,
                 communication: Optional[CommunicationHandler] = None,
                 timer: Optional[TimerHandler] = None,
                 mobility: Optional[MobilityHandler] = None,
                 **_kwargs: dict):
        """
        Instantiates a python encapsulator

        Args:
            node: Node being encapsulated
            communication: Communication handler, if present
            timer: Timer handler, if present
            mobility: Mobility handler, if present
        """
        self.provider = PythonProvider(node, communication, timer, mobility)

    def encapsulate(self, protocol: Type[IProtocol]) -> None:
        """
        Encapsulates the protocol instance. Injencts a PythonProvider instance into it

        Args:
            protocol: Type of protocol being instantiated
        """
        self.protocol = protocol.instantiate(self.provider)

    def initialize(self, stage: int) -> None:
        """
        Redirects the call to the protocol
        """
        self.protocol.initialize(stage)

    def handle_timer(self, timer: str) -> None:
        """
        Redirects the call to the protocol
        """
        self.protocol.handle_timer(timer)

    def handle_packet(self, message: str) -> None:
        """
        Redirects the call to the protocol
        """
        self.protocol.handle_packet(message)

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        """
        Redirects the call to the protocol
        """
        self.protocol.handle_telemetry(telemetry)

    def finish(self) -> None:
        """
        Redirects the call to the protocol
        """
        self.protocol.finish()
