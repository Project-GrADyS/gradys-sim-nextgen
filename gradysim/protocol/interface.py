"""
This file contains the interface that all protocols must implement. It also contains the interface that all protocols
use to interact with their environment, the IProvider interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from gradysim.protocol.messages.communication import CommunicationCommand
from gradysim.protocol.messages.mobility import MobilityCommand
from gradysim.protocol.messages.telemetry import Telemetry


class IProvider(ABC):
    """
    Interface that all protocols use to interact with their environment. The IProvider instance provides the protocol
    with the necessary tools to interact with the environment. It enables the protocol to send messages to other nodes,
    schedule timers, and more.
    """

    @abstractmethod
    def send_communication_command(self, command: CommunicationCommand) -> None:
        """
        Sends a communication command to the node's communication module

        Args:
            command: the communication command to send
        """
        pass

    @abstractmethod
    def send_mobility_command(self, command: MobilityCommand) -> None:
        """
        Sends a mobility command to the node's mobility module

        Args:
            command: the mobility command to send
        """
        pass

    @abstractmethod
    def schedule_timer(self, timer: str, timestamp: float) -> None:
        """
        Schedules a timer that should fire at a specified timestamp

        Args:
            timer: the timer to schedule. Use this string to identify the timer when it fires, associate it with some
                serialized data, or anything else that can be represented as a string.
            timestamp: the timestamp in simulation seconds at which the timer should fire.
        """
        pass

    @abstractmethod
    def current_time(self) -> float:
        """
        Returns the current simulator time in seconds

        Returns:
            the current simulator time in seconds
        """
        pass

    @abstractmethod
    def get_id(self) -> int:
        """
        Returns the node's unique identifier in the simulation

        Returns:
            the node's unique identifier in the simulation
        """
        pass

    # TODO: Document this
    tracked_variables: Dict[str, Any]


class IProtocol(ABC):
    """
    Subclass this interface to define a protocol. All abstract methods must be implemented, they can be empty in case
    no action is necessary. These methods define how a node reacts to its environment. You should use them to implement
    the logic that powers your node. Following this interface you will need to implement your protocol's logic in a
    event-based fashion.

    The IProvider interface accessible through the `provider` attribute provides the protocol with the necessary tools
    to interact with the environment.

    Protocols that follow this interface can run in any of the [execution-modes][] supported by GrADyS-SIM TNG.
    """

    provider: IProvider
    """
    IProvider instance that will provide protocol
    with necessary tools to interact with the environment.
    """

    @classmethod
    def instantiate(cls, provider: IProvider) -> 'IProtocol':
        """
        Called when the protocol is instantiated before the simulator starts. The protocol's __init__() method is not
        called, instead this method is used to initialize the protocol.

        Args:
            provider: the IProvider instance that will provide the protocol
                with necessary tools to interact with the environment

        Returns:
            the instantiated protocol
        """
        protocol = cls()
        protocol.provider = provider
        return protocol

    @abstractmethod
    def initialize(self, stage: int) -> None:
        """
        This is the first function called when the simulator begins. The initialize()
        methods for each network node are called in arbitrary order so don't rely on other
        protocols having already been initialized.
        """
        pass

    @abstractmethod
    def handle_timer(self, timer: str) -> None:
        """
        Called when a timer fires. The timer is identified by a string. This is the same string that was passed to the
        provider's schedule_timer() method when the timer was scheduled.

        Args:
            timer: the timer that fired
        """
        pass

    @abstractmethod
    def handle_packet(self, message: str) -> None:
        """
        Called when a packet is received from another node. The packet contains a message which can be an identifier,
        some serialized data, or anything else that can be represented as a string.

        Args:
            message: the message contained in the packet
        """
        pass

    @abstractmethod
    def handle_telemetry(self, telemetry: Telemetry) -> None:
        """
        Regularly called by the mobility module with information about the state of the node's mobility. Use this data
        if your protocol should react to the node's mobility.

        Args:
            telemetry: the telemetry data
        """
        pass

    @abstractmethod
    def finish(self) -> None:
        """
        Called when the simulator finishes. The finish() method of every node in the simulator is called in arbitrary
        order.
        """
        pass
