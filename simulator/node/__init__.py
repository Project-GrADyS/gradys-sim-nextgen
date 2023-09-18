from typing import Tuple

from simulator.encapsulator.interface import IEncapsulator

Position = Tuple[float, float, float]


class Node:
    id: int
    protocol_encapsulator: IEncapsulator

    position: Position
