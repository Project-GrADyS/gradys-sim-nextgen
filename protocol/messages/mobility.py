from dataclasses import dataclass
from enum import Enum


class MobilityCommandType(int, Enum):
    GOTO_COORDS = 1
    GOTO_GEO_COORDS = 2
    SET_SPEED = 3


@dataclass
class MobilityCommand:
    command: MobilityCommandType

    param_1: float = 0
    param_2: float = 0
    param_3: float = 0
    param_4: float = 0
    param_5: float = 0
    param_6: float = 0


class GotoCoordsMobilityCommand(MobilityCommand):
    def __init__(self, x: float, y: float, z: float):
        super().__init__(MobilityCommandType.GOTO_COORDS, x, y, z)


class SetSpeedMobilityCommand(MobilityCommand):
    def __init__(self, speed: float):
        super().__init__(MobilityCommandType.SET_SPEED, speed)
