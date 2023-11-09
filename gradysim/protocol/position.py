"""
This module contains some helpers useful when working with positions. Positions are used to localize
the nodes inside the python simulation.
"""

from typing import Tuple

Position = Tuple[float, float, float]
"""
Represents a node's position inside the simulation. It is a tuple of three floating point numbers
representing the euclidean coordinates of the node.
"""


def squared_distance(start: Position, end: Position) -> float:
    """
    Calculates the squared distance between two positions.

    Args:
        start: First position
        end: Second position

    Returns:
        The distance squared
    """
    return (end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2 + (end[2] - start[2]) ** 2

