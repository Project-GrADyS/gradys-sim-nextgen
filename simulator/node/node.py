from simulator.encapsulator.interface import IEncapsulator
from simulator.position import Position


class Node:
    id: int
    protocol_encapsulator: IEncapsulator

    position: Position
