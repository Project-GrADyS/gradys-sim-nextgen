from typing import Generic, TypeVar

from protocol.interface import IProtocol
from simulator.encapsulator.interface import IEncapsulator
from simulator.position import Position

T = TypeVar("T", bound=IProtocol)


class Node(Generic[T]):
    """
    Represents a node inside the python simulation,
    """
    id: int
    protocol_encapsulator: IEncapsulator[T]

    position: Position
