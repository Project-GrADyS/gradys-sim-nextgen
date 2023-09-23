from enum import Enum


class MobilityCommandType(int, Enum):
    SET_MODE = 0
    GOTO_COORDS = 1

    GOTO_WAYPOINT = 2
    REVERSE = 3


class MobilityMode(int, Enum):
    GUIDED = 0
    AUTO = 1


class MobilityCommand:
    command: MobilityCommandType

    param_1: int
    param_2: int
    param_3: int
    param_4: int
    param_5: int
    param_6: int


class ReverseCommand(MobilityCommand):
    def __init__(self):
        self.command = MobilityCommandType.REVERSE

        self.param_1 = 0
        self.param_2 = 0
        self.param_3 = 0
        self.param_4 = 0
        self.param_5 = 0
        self.param_6 = 0


class SetModeCommand(MobilityCommand):
    def __init__(self, mode: MobilityMode):
        self.command = MobilityCommandType.SET_MODE
        self.param_1 = mode.value

        self.param_2 = 0
        self.param_3 = 0
        self.param_4 = 0
        self.param_5 = 0
        self.param_6 = 0
