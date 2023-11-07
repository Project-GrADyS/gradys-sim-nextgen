"""
This file contains definitions for the communication commands. These commands are sent to the communication module
to instruct it to perform some communication action, generally sending a message to another node.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CommunicationCommandType(int, Enum):
    """
    Enum that defines the types of communication commands
    """
    SEND = 0
    """Send a message to a specific node"""
    BROADCAST = 1
    """Send a message to all nodes"""


@dataclass
class CommunicationCommand:
    """
    Represents a communication command. Communication commands are sent to the communication module to instruct it to
    perform some communication action, generally sending a message to another node.
    """
    command_type: CommunicationCommandType
    """The type of the communication command"""

    message: str
    """The message to send"""

    destination: Optional[int] = None
    """The destination node ID. It's not necessary for a broadcast message"""


class SendMessageCommand(CommunicationCommand):
    def __init__(self, message: str):
        self.command = CommunicationCommandType.SEND
        self.message = message


class BroadcastMessageCommand(CommunicationCommand):
    def __init__(self, message: str):
        self.command = CommunicationCommandType.BROADCAST
        self.message = message
