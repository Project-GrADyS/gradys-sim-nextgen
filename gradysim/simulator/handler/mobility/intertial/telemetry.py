from dataclasses import dataclass

from gradysim.protocol.messages.telemetry import Telemetry


@dataclass
class InertialTelemetry(Telemetry):
    """
    Telemetry message emitted by InertialMobilityHandler after position updates. This class extends the base Telemetry
    message with additional fields specifying the node's velocity and acceleration, which is relevant information for
    protocols using inertial mobility.
    """
    current_velocity: tuple[float, float, float]
