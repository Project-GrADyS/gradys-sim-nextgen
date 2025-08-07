import logging
from typing import Optional

from gradysim.protocol.interface import IProtocol
from gradysim.simulator.extension.extension import Extension
from gradysim.simulator.handler.communication import CommunicationHandler


class CommunicationController(Extension):
    """
    Controller for the communication handler. Can be used to send commands to the communication handler from a
    protocol. Commands affect the communication between nodes, such as changing the transmission range.

    !!!info
        Every method in this class is a no-op if a communication handler is not active. This includes when the protocol
        is not running on a python simulation environment.

    !!!warning
        This class is an [extension][gradysim.simulator.extension] and will raise an error if the protocol is not
        running on a python simulation.
    """

    def __init__(self, protocol: IProtocol):
        super().__init__(protocol)
        if self._provider is not None:
            self._communication: Optional[CommunicationHandler] = self._provider.handlers.get("communication")
        if self._communication is None:
            logging.warning("No communication handler detected. All commands will be no-ops.")

    def set_transmission_range(self, transmission_range: float):
        """
        Sets the transmission range of the protocol. This only affects the range of transmission, meaning other nodes
        will receive communication messages from this node if they are within this range; but not the reverse.

        No-op if no communication handler is active.

        Args:
            transmission_range: The new transmission range of the protocol. Must be a positive number.

        Raises:
            ValueError: If the transmission range is a negative number.
        """
        if transmission_range < 0:
            raise ValueError("Transmission range must be a positive number.")

        if self._communication is None:
            logging.warning("No communication handler detected, command ignored.")
            return

        self._communication.transmission_ranges[self._provider.get_id()] = transmission_range

    def get_transmission_range(self) -> Optional[float]:
        """
        Gets the current transmission range of the protocol. If no communication handler is active, returns None.

        Returns:
            The transmission range of the protocol. If no communication handler is active, returns None
        """
        if self._communication is None:
            logging.warning("No communication handler detected, returning 0.")
            return None

        return self._communication.transmission_ranges[self._provider.get_id()]