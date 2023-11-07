"""
This is a simple module containing declarations necessary to keep track of the nodes during the simulation
"""

from typing import Generic, TypeVar

from gradysim.protocol.interface import IProtocol
from gradysim.encapsulator.interface import IEncapsulator
from gradysim.simulator.position import Position

T = TypeVar("T", bound=IProtocol)


class Node(Generic[T]):
    """
    Represents a node inside the python simulation. Holds the reference to the node's encapsulated protocol.
    This class is accessible to [handlers][gradysim.simulator.handler].
    """
    id: int
    """Node's unique identifier"""

    protocol_encapsulator: IEncapsulator[T]
    """Node's encapsulated protocol"""

    position: Position
    """Node's position inside the simulation"""
