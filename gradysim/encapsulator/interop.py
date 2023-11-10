"""
Wraps the running protocol and prepares it for integration with the OMNeT++, in [integrated-mode][]. It is injected with
a [InteropProvider][gradysim.encapsulator.interop.InteropProvider] instance that provides it with the necessary tools to
interact with the OMNeT++ environment.

The integration works by collecting all the consequences of the protocol's actions and returning them to the OMNeT++.
Consequences are actions that the protocol wants to perform on the environment, such as sending a message or moving the
node. The OMNeT++ environment then performs these actions is able to call protocol when it needs to, such as when a
message is received or a timer fires.

This encapsulator is instantiated by OMNeT++, the execution flow is only transferred to this code when an envet happens
in the OMNeT++ simulation that warrants a call to the protocol. No code changes are necessary to run a protocol in this
mode.
"""

from enum import Enum
from typing import List, Type, Tuple, Union, Any, Callable

from gradysim.protocol.interface import IProtocol, IProvider
from gradysim.encapsulator.interface import IEncapsulator
from gradysim.protocol.messages.communication import CommunicationCommand
from gradysim.protocol.messages.mobility import MobilityCommand

from gradysim.protocol.messages.telemetry import Telemetry


class ConsequenceType(int, Enum):
    """
    Enum representing the different types of consequences that can be returned by the protocol. Each consequence type
    serializes a different interaction the protocol wants to perform with the environment.
    """
    COMMUNICATION = 0
    MOBILITY = 1
    TIMER = 2
    TRACK_VARIABLE = 3


TimerParams = Tuple[str, float]
"""Parameters to a timer consequence. The str is the timer and the float is the timestamp when the timer should fire"""

TrackVariableParams = Tuple[str, Any]
"""Parameters to a track variable consequence. The str is the variable name and the Any is the variable value"""

Consequence = Tuple[ConsequenceType, Union[CommunicationCommand, MobilityCommand, TimerParams, TrackVariableParams]]
"""
A consequence is a tuple of a consequence type and a consequence payload. The payload is a different type for each
consequence type
"""


class _TrackedVariableContainer(dict):
    def __init__(self, setter_callback: Callable[[str, Any], None]):
        super().__init__()
        self.callback = setter_callback

    def __setitem__(self, key, value):
        self.callback(key, value)


class InteropProvider(IProvider):
    """
    Provider implementation for the OMNeT++ environment. The provider is injected into the protocol encapsulator and
    provides it with the necessary tools to interact with the environment.
    """
    consequences: List[Consequence]
    timestamp: int
    id: int

    def __init__(self):
        """
        Creates a new provider instance
        """
        self.consequences = []
        self.timestamp = 0
        self.id = 0
        self.tracked_variables = \
            _TrackedVariableContainer(lambda key, value: self.consequences.append((ConsequenceType.TRACK_VARIABLE,
                                                                                   (key, value))))

    def send_communication_command(self, command: CommunicationCommand) -> None:
        """
        Adds a communication command to the list of consequences
        
        Args:
            command: Command being issued
        """
        self.consequences.append((ConsequenceType.COMMUNICATION, command))

    def send_mobility_command(self, command: MobilityCommand) -> None:
        """
        Adds a mobility command to the list of consequences

        Args:
            command: Command being issued
        """
        self.consequences.append((ConsequenceType.MOBILITY, command))

    def schedule_timer(self, timer: str, timestamp: float) -> None:
        """
        Adds a timer consequence to the list of consequences

        Args:
            timer: The timer that will be fired
            timestamp: The timestamp in simulation seconds when the timer will fire
        """
        self.consequences.append((ConsequenceType.TIMER, (timer, timestamp)))

    def current_time(self) -> int:
        """
        Returns the current simulation time in seconds

        Returns: The current simulation time in seconds
        """
        return self.timestamp

    def get_id(self) -> int:
        """
        Returns the node's unique identifier in the simulation

        Returns:
            The node's unique identifier in the simulation
        """
        return self.id


class InteropEncapsulator(IEncapsulator):
    """
    Encapsulator implementation for the OMNeT++ environment. The encapsulator wraps the protocol and prepares it for
    integration with the OMNeT++ environment. It is injected with a [InteropProvider][gradysim.encapsulator.interop.InteropProvider]
    instance that provides it with the necessary tools to interact with the OMNeT++ environment.
    """
    provider: InteropProvider

    def __init__(self):
        """
        Creates a new encapsulator instance
        """
        self.provider = InteropProvider()

    def encapsulate(self, protocol: Type[IProtocol]) -> None:
        """
        Instantiates the protocol and injects the provider into it

        Args:
            protocol: The type of protocol being encapsulated
        """
        self.protocol = protocol.instantiate(self.provider)

    def _collect_consequences(self) -> List[Consequence]:
        consequences = self.provider.consequences
        self.provider.consequences = []
        return consequences

    def set_timestamp(self, timestamp: float):
        """
        Sets the current simulation time in seconds. This method is called by the OMNeT++ environment before calling
        the protocol's methods, to make sure the protocol has the correct time.
        """
        self.provider.timestamp = timestamp

    def set_id(self, id: int):
        """
        Sets the node's unique identifier in the simulation. This method is called once by the OMNeT++ environment
        before calling any of the protocol's methods, to make sure the protocol has the correct id.
        """
        self.provider.id = id

    def initialize(self, stage: int) -> List[Consequence]:
        """
        Initializes the protocol. Called by the OMNeT++ environment before the simulation starts.

        Returns:
            A list of consequences that the protocol wants to perform on the environment from this call
        """
        self.protocol.initialize(stage)
        return self._collect_consequences()

    def handle_timer(self, timer: str) -> List[Consequence]:
        """
        Handles a timer event. Called by the OMNeT++ environment when a timer fires.

        Args:
            timer: The timer that fired

        Returns:
            A list of consequences that the protocol wants to perform on the environment from this call
        """
        self.protocol.handle_timer(timer)
        return self._collect_consequences()

    def handle_packet(self, message: str) -> List[Consequence]:
        """
        Handles a message. Called by the OMNeT++ environment when a message is received.

        Args:
            message: Message being received

        Returns:
            A list of consequences that the protocol wants to perform on the environment from this call
        """
        self.protocol.handle_packet(message)
        return self._collect_consequences()

    def handle_telemetry(self, telemetry: Telemetry) -> List[Consequence]:
        """
        Handles a telemetry event. Called by the OMNeT++ environment when a telemetry event happens.

        Args:
            telemetry: Telemetry event being received

        Returns:
            A list of consequences that the protocol wants to perform on the environment from this call
        """
        self.protocol.handle_telemetry(telemetry)
        return self._collect_consequences()

    def finish(self) -> List[Consequence]:
        """
        Finalizes the protocol. Called by the OMNeT++ environment when the simulation is over.

        Returns:
            A list of consequences that the protocol wants to perform on the environment from this call
        """
        self.protocol.finish()
        return self._collect_consequences()
