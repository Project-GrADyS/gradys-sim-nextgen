"""
Wire format for the position/velocity/ID heartbeat OrcaAvoidancePlugin instances exchange to
discover and track each other.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from gradysim.protocol.position import Position

_MESSAGE_TYPE = "orca_heartbeat"


@dataclass
class HeartbeatMessage:
    """A single UAV's self-reported position and velocity, broadcast periodically so nearby UAVs
    running the same OrcaAvoidancePlugin can track it."""

    node_id: int
    position: Position
    velocity: Position

    def to_json(self) -> str:
        """Serializes this heartbeat to the JSON string sent over the wire."""
        return json.dumps({
            "type": _MESSAGE_TYPE,
            "id": self.node_id,
            "position": list(self.position),
            "velocity": list(self.velocity),
        })

    @classmethod
    def try_from_json(cls, message: str) -> Optional[HeartbeatMessage]:
        """
        Attempts to parse a raw packet payload as a heartbeat.

        Returns:
            The parsed HeartbeatMessage, or None if the payload isn't a heartbeat
            not an error.
        """
        try:
            data = json.loads(message)
        except (json.JSONDecodeError, TypeError):
            return None

        if not isinstance(data, dict) or data.get("type") != _MESSAGE_TYPE:
            return None

        try:
            return cls(
                node_id=int(data["id"]),
                position=tuple(float(x) for x in data["position"]),
                velocity=tuple(float(x) for x in data["velocity"]),
            )
        except (KeyError, TypeError, ValueError):
            return None
