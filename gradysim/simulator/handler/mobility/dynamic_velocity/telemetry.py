from dataclasses import dataclass

from gradysim.protocol.messages.telemetry import Telemetry


@dataclass
class DynamicVelocityTelemetry(Telemetry):
    """
    Telemetry message emitted by DynamicVelocityMobilityHandler after position updates.

    This class extends the base Telemetry message with additional fields
    specifying the node's velocity, which is relevant information for
    protocols using dynamic velocity mobility.
    """
    current_velocity: tuple[float, float, float]
