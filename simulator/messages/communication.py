from enum import Enum
from typing import Optional


class CommunicationCommandType(Enum):
    SEND = 1
    BROADCAST = 2


class CommunicationCommand:
    def __init__(self, command: CommunicationCommandType, message: dict, destination: Optional[int] = None):
        self.type = command
        self.message = message
        self.destination = destination

    type: CommunicationCommandType
    message: dict
    destination: Optional[int]


class SendMessageCommand(CommunicationCommand):
    def __init__(self, message: dict):
        self.command = CommunicationCommandType.SEND.name
        self.message = message


class BroadcastMessageCommand(CommunicationCommand):
    def __init__(self, message: dict):
        self.command = CommunicationCommandType.BROADCAST.name
        self.message = message
