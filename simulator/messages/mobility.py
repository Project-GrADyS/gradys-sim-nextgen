from enum import Enum


class MobilityCommandType(int, Enum):
    SET_MODE = 0
    GOTO_COORDS = 1

    GOTO_WAYPOINT = 2
    REVERSE = 3

    SET_SPEED = 4


class MobilityMode(int, Enum):
    GUIDED = 0
    AUTO = 1


class MobilityCommand:
    command: MobilityCommandType

    param_1: float
    param_2: float
    param_3: float
    param_4: float
    param_5: float
    param_6: float

    def __init__(self, command: MobilityCommandType,
                 param_1: float = 0,
                 param_2: float = 0,
                 param_3: float = 0,
                 param_4: float = 0,
                 param_5: float = 0,
                 param_6: float = 0):
        self.command = command
        self.param_1 = param_1
        self.param_2 = param_2
        self.param_3 = param_3
        self.param_4 = param_4
        self.param_5 = param_5
        self.param_6 = param_6


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
