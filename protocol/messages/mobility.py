"""
This file defines mobility commands. Mobility commands are sent to the mobility module to instruct it to perform some
mobility action, like moving the node to a new location.
"""

from dataclasses import dataclass
from enum import Enum


class MobilityCommandType(int, Enum):
    """
    Enum that defines the types of mobility commands
    """
    GOTO_COORDS = 1
    """Move the node to a new location specified by its x, y, and z euclidean coordinates"""

    GOTO_GEO_COORDS = 2
    """Move the node to a new location specified by its latitude, longitude, and altitude"""

    SET_SPEED = 3
    """Set the node's speed in m/s"""


@dataclass
class MobilityCommand:
    """
    Represents a mobility command. Mobility commands are sent to the mobility module to instruct it to perform some
    mobility action, like moving the node to a new location. The mobility command has 6 generic parameters whose
    meaning changes depending on the command type. You shouldn't use this class directly, use one of the subclasses
    instead (e.g. GotoCoordsMobilityCommand) to have properly typed parameters.
    """

    command: MobilityCommandType
    """The type of the mobility command"""

    param_1: float = 0
    """The first parameter of the mobility command, it's meaning changes depending on the command type"""

    param_2: float = 0
    """The second parameter of the mobility command, it's meaning changes depending on the command type"""

    param_3: float = 0
    """The third parameter of the mobility command, it's meaning changes depending on the command type"""

    param_4: float = 0
    """The fourth parameter of the mobility command, it's meaning changes depending on the command type"""

    param_5: float = 0
    """The fifth parameter of the mobility command, it's meaning changes depending on the command type"""

    param_6: float = 0
    """The sixth parameter of the mobility command, it's meaning changes depending on the command type"""


class GotoCoordsMobilityCommand(MobilityCommand):
    """
    Represents a mobility command that instructs the mobility module to move the node to a new location. The new
    location is specified by its x, y, and z coordinates.
    """

    def __init__(self, x: float, y: float, z: float):
        """
        Initializes a GoToCoordsMobilityCommand

        Args:
            x: x coords of the new location
            y: y coords of the new location
            z: z coords of the new location
        """

        super().__init__(MobilityCommandType.GOTO_COORDS, x, y, z)


class SetSpeedMobilityCommand(MobilityCommand):
    """
    Represents a mobility command that sets the node's speed. The only parameter of this command is the desired speed
    in m/s.
    """

    def __init__(self, speed: float):
        """
        Initializes a SetSpeedMobilityCommand

        Args:
            speed: The desired speed in m/s
        """
        super().__init__(MobilityCommandType.SET_SPEED, speed)
