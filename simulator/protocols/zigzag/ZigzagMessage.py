from enum import Enum
import json


class ZigzagMessageType(int, Enum):
    HEARTBEAT = 0
    PAIR_REQUEST = 1
    PAIR_CONFIRM = 2
    BEARER = 3


class ZigzagMessage:
    messageType: ZigzagMessageType
    sourceID: int
    destinationID: int
    nextWaypointID: int
    lastWaypointID: int
    dataLength: int
    reversed: bool

    def __init__(
        self,
        messageType: ZigzagMessageType = ZigzagMessageType.HEARTBEAT,
        sourceID: int = -1,
        destinationID: int = -1,
        nextWaypointID: int = -1,
        lastWaypointID: int = -1,
        dataLength: int = 5,
        reversed: bool = False,
    ) -> None:
        self.messageType = messageType
        self.sourceID = sourceID
        self.destinationID = destinationID
        self.nextWaypointID = nextWaypointID
        self.lastWaypointID = lastWaypointID
        self.dataLength = dataLength
        self.reversed = reversed

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        return cls(**data)
