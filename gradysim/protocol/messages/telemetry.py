from dataclasses import dataclass

from gradysim.protocol.position import Position


@dataclass
class Telemetry:
    current_position: Position