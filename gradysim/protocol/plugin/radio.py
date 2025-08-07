"""
This module declares a plugin for the protocol that allows a protocol to instantiate multiple radios, each with their own
communication characteristics. This plugin is only available in a Python simulation environment and will raise an
error if used in other environments. Alternative implementations should be provided for other simulation environments,
"""
from dataclasses import dataclass

from gradysim.encapsulator.python import PythonProvider
from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.communication import CommunicationCommand
from gradysim.simulator.extension.communication_controller import CommunicationController


@dataclass
class RadioConfiguration:
    range: float

class Radio:
    """
    A plugin that allows a protocol to instantiate multiple radios, each with their own communication characteristics.

    Multiple radios can be instantiated in a single protocol. Messages sent through the radio will use the radio's
    communication characteristics, such as transmission range. Messages sent through other radios or directly through
    the protocol will not be affected by the radio's characteristics.

    This plugin is only available in a Python simulation environment and will raise an error if used in other
    environments. Alternative implementations should be provided for other simulation environments, ones that
    interface with real hardware radios or other communication systems.

    !!!warning
        This plugin can only be used in a Python simulation environment.
    """

    def __init__(self, protocol: IProtocol, radio_configuration: RadioConfiguration):
        """
        Initializes the Radio plugin.
        """
        self._radio_configuration = radio_configuration

        provider = protocol.provider
        if not isinstance(provider, PythonProvider):
            raise TypeError("Radio plugin can only be used in a Python simulation environment.")
        self._provider = provider

        self._communication_controller = CommunicationController(protocol)

    def set_configuration(self, radio_configuration: RadioConfiguration) -> None:
        """
        Sets a new configuration for the radio.

        Args:
            radio_configuration: The new configuration for the radio.
        """
        self._radio_configuration = radio_configuration

    def send_communication_command(self, command: CommunicationCommand) -> None:
        """
        Sends a message via the radio.

        Args:
            command: The communication command to send. Same CommunicationCommand used in [IProvider][gradysim.protocol.interface.IProvider]
        """
        previous_range = self._communication_controller.get_transmission_range()
        if previous_range is None:
            raise RuntimeError("Cannot use radio: No communication handler detected.")
        self._communication_controller.set_transmission_range(self._radio_configuration.range)
        self._provider.send_communication_command(command)
        self._communication_controller.set_transmission_range(previous_range)
