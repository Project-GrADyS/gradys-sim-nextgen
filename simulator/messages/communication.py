from enum import Enum
from typing import Optional



class CommunicationCommandType(int, Enum):
    SEND = 0
    BROADCAST = 1


class CommunicationCommand:
    type: CommunicationCommandType
    message: dict
    destination: Optional[int]

    def __init__(self, command: CommunicationCommandType, message: dict, destination: Optional[int] = None):
        self.type = command
        self.message = message
        self.destination = destination


class SendMessageCommand(CommunicationCommand):
    def __init__(self, message: str):
        self.command = CommunicationCommandType.SEND.name
        self.message = message


class BroadcastMessageCommand(CommunicationCommand):
    def __init__(self, message: str):
        self.command = CommunicationCommandType.BROADCAST.name
        self.message = message
