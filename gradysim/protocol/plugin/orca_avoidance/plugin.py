"""
This module declares a plugin that lets a protocol perform reciprocal (ORCA)
collision avoidance against nearby UAVs running the SAME plugin.

The plugin tracks nearby UAVs via a self-broadcast heartbeat (position/velocity/ID) and computes
an avoidance velocity whenever a neighbor is on a collision course. It never sends mobility
commands or touches any other timer itself - your protocol decides when to use
avoidance_velocity instead of its own goal-tracking velocity and is
responsible for actually issuing the mobility command.
"""

import logging
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Set

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.communication import BroadcastMessageCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.plugin.dispatcher import create_dispatcher, DispatchReturn
from gradysim.protocol.position import Position, squared_distance
from gradysim.simulator.handler.mobility.dynamic_velocity.telemetry import DynamicVelocityTelemetry

from . import orca
from .config import OrcaAvoidanceConfiguration
from .heartbeat import HeartbeatMessage

ORCA_HEARTBEAT_TIMER_TAG = "OrcaAvoidancePlugin__heartbeat_timer"
"""The plugin broadcasts its own heartbeat using a timer with this name, make sure it doesn't
conflict with other timers your protocol schedules."""

ORCA_SOLVE_TIMER_TAG = "OrcaAvoidancePlugin__solve_timer"
"""The plugin recomputes its avoidance velocity using a timer with this name, make sure it
doesn't conflict with other timers your protocol schedules."""


class OrcaAvoidancePluginException(Exception):
    pass


@dataclass
class _NeighborState:
    position: Position
    velocity: Position
    last_seen: float


class OrcaAvoidancePlugin:
    """
    Use this plugin if you want your node to perform reciprocal collision avoidance (ORCA)
    against nearby UAVs running the same plugin.

    This plugin requires the node's mobility to be provided by Dynamic Velocity Mobility Handler
    and needs both position and velocity telemetry. It broadcasts and listens for
    heartbeat message (position/velocity/ID) to discover and track neighbors.

    The plugin does not send mobility commands or touch any other timer. Feed it your protocol's
    desired velocity via set_goal_velocity, check is_colliding on your own control,
    and use avoidance_velocity instead of your own velocity command for as long as it stays True.
    """

    def __init__(self, protocol: IProtocol, configuration: OrcaAvoidanceConfiguration):
        if configuration.max_speed <= 0:
            raise ValueError("max_speed must be > 0")
        if configuration.inflation_radius <= 0:
            raise ValueError("inflation_radius must be > 0")
        if configuration.time_horizon <= 0:
            raise ValueError("time_horizon must be > 0")
        if configuration.heartbeat_period <= 0:
            raise ValueError("heartbeat_period must be > 0")
        if configuration.orca_period <= 0:
            raise ValueError("orca_period must be > 0")

        self._dispatcher = create_dispatcher(protocol)
        self._protocol = protocol
        self._config = configuration
        self._logger = logging.getLogger()

        self._neighbors: Dict[int, _NeighborState] = {}
        self._colliding_neighbor_ids: Set[int] = set()

        self._last_position: Optional[Position] = None
        self._last_velocity: Optional[Position] = None

        self._goal_velocity: Position = (0.0, 0.0, 0.0)
        self._avoidance_velocity: Optional[Position] = None

        self._initialize_telemetry_handling()
        self._initialize_packet_handling()
        self._initialize_heartbeat_loop()
        self._initialize_solve_loop()

    def _initialize_telemetry_handling(self) -> None:
        """Caches the latest position/velocity telemetry, needed both to broadcast our own
        heartbeat and to evaluate collisions against tracked neighbors."""

        def telemetry_handler(_instance: IProtocol, telemetry: Telemetry) -> DispatchReturn:
            if not isinstance(telemetry, DynamicVelocityTelemetry):
                raise OrcaAvoidancePluginException(
                    "OrcaAvoidancePlugin requires DynamicVelocityTelemetry, which is only emitted "
                    "by DynamicVelocityMobilityHandler. Make sure your simulation uses that "
                    "mobility handler."
                )

            self._last_position = telemetry.current_position
            self._last_velocity = telemetry.current_velocity
            return DispatchReturn.CONTINUE

        self._dispatcher.register_handle_telemetry(telemetry_handler)

    def _initialize_packet_handling(self) -> None:
        """Listens for other nodes' heartbeats, updating the neighbor table and immediately
        checking collision state whenever one arrives."""

        def packet_handler(_instance: IProtocol, message: str) -> DispatchReturn:
            heartbeat = HeartbeatMessage.try_from_json(message)
            if heartbeat is None:
                return DispatchReturn.CONTINUE

            if heartbeat.node_id != self._protocol.provider.get_id():
                self._neighbors[heartbeat.node_id] = _NeighborState(
                    position=heartbeat.position,
                    velocity=heartbeat.velocity,
                    last_seen=self._protocol.provider.current_time(),
                )
                self._refresh_collision_state()

            # Interrupt so the protocol doesn't see this heartbeat message 
            return DispatchReturn.INTERRUPT

        self._dispatcher.register_handle_packet(packet_handler)

    def _initialize_heartbeat_loop(self) -> None:
        def timer_handler(_instance: IProtocol, timer: str) -> DispatchReturn:
            if timer != ORCA_HEARTBEAT_TIMER_TAG:
                return DispatchReturn.CONTINUE

            self._send_heartbeat()
            self._schedule_timer(ORCA_HEARTBEAT_TIMER_TAG, self._config.heartbeat_period)
            return DispatchReturn.INTERRUPT

        self._dispatcher.register_handle_timer(timer_handler)
        self._schedule_timer(ORCA_HEARTBEAT_TIMER_TAG, self._config.heartbeat_period)

    def _initialize_solve_loop(self) -> None:
        def timer_handler(_instance: IProtocol, timer: str) -> DispatchReturn:
            if timer != ORCA_SOLVE_TIMER_TAG:
                return DispatchReturn.CONTINUE

            self._solve_step()
            self._schedule_timer(ORCA_SOLVE_TIMER_TAG, self._config.orca_period)
            return DispatchReturn.INTERRUPT

        self._dispatcher.register_handle_timer(timer_handler)
        self._schedule_timer(ORCA_SOLVE_TIMER_TAG, self._config.orca_period)

    def _schedule_timer(self, tag: str, delay: float) -> None:
        self._protocol.provider.schedule_timer(tag, self._protocol.provider.current_time() + delay)

    def _send_heartbeat(self) -> None:
        if self._last_position is None or self._last_velocity is None:
            # No telemetry yet, expected for the very first tick. Just try again next period.
            return

        message = HeartbeatMessage(
            node_id=self._protocol.provider.get_id(),
            position=self._last_position,
            velocity=self._last_velocity,
        )
        self._protocol.provider.send_communication_command(
            BroadcastMessageCommand(message.to_json())
        )

    def _prune_stale_neighbors(self) -> None:
        now = self._protocol.provider.current_time()
        timeout = self._config.effective_neighbor_timeout
        stale_ids = [
            node_id for node_id, neighbor in self._neighbors.items()
            if now - neighbor.last_seen > timeout
        ]
        for node_id in stale_ids:
            del self._neighbors[node_id]
            self._colliding_neighbor_ids.discard(node_id)

    def _refresh_collision_state(self) -> None:
        if self._last_position is None or self._last_velocity is None:
            self._colliding_neighbor_ids = set()
            return

        colliding = set()
        for node_id, neighbor in self._neighbors.items():
            if orca.is_on_collision_course(
                self_position=self._last_position,
                self_velocity=self._last_velocity,
                neighbor_position=neighbor.position,
                neighbor_velocity=neighbor.velocity,
                combined_radius=self._config.inflation_radius,
                horizon=self._config.time_horizon,
                dt=self._config.orca_period,
            ):
                colliding.add(node_id)
        self._colliding_neighbor_ids = colliding

    def _solve_step(self) -> None:
        self._prune_stale_neighbors()
        self._refresh_collision_state()

        if self._last_position is None or self._last_velocity is None or not self._neighbors:
            self._avoidance_velocity = self._goal_velocity
            return

        selected = self._select_neighbors_for_solve()
        self._avoidance_velocity = orca.solve(
            preferred_velocity=self._goal_velocity,
            self_position=self._last_position,
            self_velocity=self._last_velocity,
            neighbors=[(neighbor.position, neighbor.velocity) for neighbor in selected],
            combined_radius=self._config.inflation_radius,
            max_speed_box=self._config.max_speed_box,
            horizon=self._config.time_horizon,
            dt=self._config.orca_period,
        )

    def _select_neighbors_for_solve(self) -> List[_NeighborState]:
        """Nearest-first, capped/cutoff subset of tracked neighbors used to build the avoidance
        solve. Collision detection (_refresh_collision_state) never applies this filter."""
        neighbors = list(self._neighbors.values())

        if self._config.neighbor_distance is not None:
            max_dist_sq = self._config.neighbor_distance ** 2
            neighbors = [
                neighbor for neighbor in neighbors
                if squared_distance(self._last_position, neighbor.position) <= max_dist_sq
            ]

        if self._config.max_neighbors is not None and len(neighbors) > self._config.max_neighbors:
            neighbors.sort(key=lambda neighbor: squared_distance(self._last_position, neighbor.position))
            neighbors = neighbors[: self._config.max_neighbors]

        return neighbors

    def set_goal_velocity(self, vx: float, vy: float, vz: float) -> None:
        """
        Sets the velocity ORCA should steer towards absent any conflicting neighbor. This is
        typically your protocol's own goal-tracking velocity (e.g. an MPC's output) - ORCA finds
        the closest collision-free velocity to whatever you set here.
        """
        self._goal_velocity = (vx, vy, vz)

    @property
    def is_colliding(self) -> bool:
        """True if any tracked neighbor is currently on a collision course (within
        time_horizon seconds, under a constant-velocity extrapolation of both agents)."""
        return bool(self._colliding_neighbor_ids)

    @property
    def avoidance_velocity(self) -> Optional[Position]:
        """The latest ORCA-computed avoidance velocity, or None if this node hasn't received
        telemetry and completed at least one solve yet."""
        return self._avoidance_velocity

    @property
    def colliding_neighbor_ids(self) -> FrozenSet[int]:
        """IDs of neighbors currently on a collision course."""
        return frozenset(self._colliding_neighbor_ids)
