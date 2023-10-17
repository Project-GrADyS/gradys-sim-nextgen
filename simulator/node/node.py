from typing import Generic, TypeVar

from simulator.encapsulator.interface import IEncapsulator
from simulator.position import Position
from simulator.protocols.interface import IProtocol

T = TypeVar("T", bound=IProtocol)


class Node(Generic[T]):
    id: int
    protocol_encapsulator: IEncapsulator[T]

    position: Position
