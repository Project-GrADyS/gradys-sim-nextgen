from typing import Tuple

Position = Tuple[float, float, float]


def squared_distance(start: Position, end: Position) -> float:
    return (end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2 + (end[2] - start[2]) ** 2

