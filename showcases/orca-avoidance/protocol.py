"""
Protocols demonstrating reciprocal (ORCA) collision avoidance using OrcaAvoidancePlugin.

DynamicVelocityMobilityHandler (required by OrcaAvoidancePlugin, since it's the only handler that
emits the velocity telemetry ORCA needs) only accepts SET_SPEED commands - there's no
GotoCoordsMobilityCommand support here. So "goto coords" in this showcase means computing a
velocity that points at the target at a fixed cruise speed, not the older massless mobility
handler's literal goto command.
"""
import math
from typing import List, Optional, Tuple

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.mobility import SetVelocityMobilityCommand
from gradysim.protocol.plugin.orca_avoidance import OrcaAvoidanceConfiguration, OrcaAvoidancePlugin
from gradysim.protocol.position import Position
from gradysim.simulator.handler.mobility.dynamic_velocity.config import DynamicVelocityMobilityConfiguration
from gradysim.simulator.handler.mobility.dynamic_velocity.telemetry import DynamicVelocityTelemetry

SQUARE_SIZE = 60.0
ALTITUDE = 10.0
CRUISE_SPEED = 5.0
ARRIVAL_TOLERANCE = 2.0

DIAGONAL_ALTITUDE_OFFSET = 1.0

VERTICAL_SEEK_SPEED = 1.0

CONTROL_PERIOD = 0.1
CONTROL_TIMER_TAG = "SquareShuttleOrcaProtocol__control_timer"

CORNERS: List[Position] = [
    (0.0, 0.0, ALTITUDE),
    (SQUARE_SIZE,0.0, ALTITUDE),
    (SQUARE_SIZE, SQUARE_SIZE, ALTITUDE),
    (0.0, SQUARE_SIZE, ALTITUDE),
]

HEAD_ON_RADIUS = 40.0
HEAD_ON_LATERAL_OFFSET = 0.1
HEAD_ON_PATHS: List[Tuple[Position, Position]] = []


def build_head_on_paths(
    count: int,
    radius: float = HEAD_ON_RADIUS,
    lateral_offset: float = HEAD_ON_LATERAL_OFFSET,
    altitude: float = ALTITUDE,
) -> List[Tuple[Position, Position]]:
    """Places count drones evenly around a circle of radius, each flying towards the point
    diametrically opposite its own start - so every drone heads roughly at every other one, all
    converging near the center at once - shifted lateral_offset meters sideways (tangentially)
    so no two paths are exactly collinear (see HEAD_ON_LATERAL_OFFSET)."""
    paths: List[Tuple[Position, Position]] = []
    for i in range(count):
        start_angle = 2 * math.pi * i / count
        start = (radius * math.cos(start_angle), radius * math.sin(start_angle), altitude)

        target_angle = start_angle + math.pi
        tangent = (-math.sin(target_angle), math.cos(target_angle))
        target = (
            radius * math.cos(target_angle) + tangent[0] * lateral_offset,
            radius * math.sin(target_angle) + tangent[1] * lateral_offset,
            altitude,
        )
        paths.append((start, target))
    return paths


DYNAMIC_VELOCITY_CONFIG = DynamicVelocityMobilityConfiguration(
    update_rate=0.1,
    max_speed_xy=16.0,
    max_speed_z=16.0,
    max_acc_xy=12.0,
    max_acc_z=12.0,
    tau_xy=0.5,
    tau_z=0.5,
)


def build_orca_configuration(
    dynamic_velocity_config: DynamicVelocityMobilityConfiguration,
) -> OrcaAvoidanceConfiguration:
    return OrcaAvoidanceConfiguration.from_dynamic_velocity_config(
        dynamic_velocity_config,
        inflation_radius=5.0,
        time_horizon=4.0,
        heartbeat_period=0.2,
        orca_period=0.2,
    )


def _goto_velocity(position: Position, target: Position, speed: float) -> Position:
    """"Goto coords" behavior for a mobility handler that only accepts velocity commands.
    Horizontal (x, y) and vertical (z) motion are driven independently rather than as one
    normalized 3D direction, so a small altitude offset settles in on its own schedule instead of
    trickling in proportionally to a much larger horizontal distance."""
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    dz = target[2] - position[2]

    horizontal_distance = math.hypot(dx, dy)
    if horizontal_distance < 1e-6:
        vx, vy, vz = 0.0, 0.0, 0.0
    else:
        scale = speed / horizontal_distance
        vx, vy, vz = dx * scale, dy * scale, dz * scale

    return (vx, vy, vz)


class SquareShuttleOrcaProtocol(IProtocol):
    """
    Flies to the diagonally opposite corner of the square and back (two crossings total), using
    OrcaAvoidancePlugin to avoid the other three drones doing the same. Flies a simple
    straight-line "goto" velocity by default; while OrcaAvoidancePlugin reports is_colliding,
    sends its avoidance_velocity instead.
    """

    def __init__(self):
        super().__init__()
        self.node_id: Optional[int] = None
        self.orca_plugin: Optional[OrcaAvoidancePlugin] = None

        self._start: Position = (0.0, 0.0, 0.0)
        self._target: Position = (0.0, 0.0, 0.0)
        self._last_position: Optional[Position] = None
        self._legs_completed = 0
        self._leg_index = 0  # 0 = first (flat) leg, 1 = second (altitude-offset) leg
        self._finished = False
        self._altitude_offset = 0.0

        self.df = []

    def initialize(self) -> None:
        self.node_id = self.provider.get_id()
        corner_index = self.node_id % 4
        self._start = CORNERS[corner_index]
        self._target = CORNERS[(corner_index + 2) % 4]
        # Each diagonal pair (0/2, 1/3) gets an opposite offset, applied starting the second leg.
        self._altitude_offset = DIAGONAL_ALTITUDE_OFFSET if corner_index in (0, 1) else -DIAGONAL_ALTITUDE_OFFSET

        config = build_orca_configuration(DYNAMIC_VELOCITY_CONFIG)
        self.orca_plugin = OrcaAvoidancePlugin(self, config)

        print(f"Node {self.node_id}: shuttling {self._start} <-> {self._target}")

        # Nodes 0/2 and 1/3 share a diagonal and would otherwise reach the exact center at the
        # exact same instant every leg (perfect square, equal speeds) - a razor-edge singular
        # case where every pair stays exactly collinear for a long stretch. A small per-node
        # start offset breaks that exact synchrony so avoidance shows up as a brief, localized
        # episode near each crossing instead of a near-constant one.
        self._schedule_control_tick(self.node_id * 1.5)

    def _schedule_control_tick(self, delay: float) -> None:
        self.provider.schedule_timer(CONTROL_TIMER_TAG, self.provider.current_time() + delay)

    def handle_timer(self, timer: str) -> None:
        if timer != CONTROL_TIMER_TAG:
            return

        self._control_step()
        self._schedule_control_tick(CONTROL_PERIOD)

    def handle_packet(self, message: str) -> None:
        pass

    def handle_telemetry(self, telemetry: DynamicVelocityTelemetry) -> None:
        if not isinstance(telemetry, DynamicVelocityTelemetry):
            return

        self._last_position = telemetry.current_position

        self.df.append({
            "t": self.provider.current_time(),
            "x": telemetry.current_position[0],
            "y": telemetry.current_position[1],
            "z": telemetry.current_position[2],
            "vx": telemetry.current_velocity[0],
            "vy": telemetry.current_velocity[1],
            "vz": telemetry.current_velocity[2],
            "colliding": self.orca_plugin.is_colliding if self.orca_plugin is not None else False,
        })

    def _control_step(self) -> None:
        if self._last_position is None:
            return

        if self._finished:
            return

        if math.dist(self._last_position, self._target) <= ARRIVAL_TOLERANCE:
            self._legs_completed += 1

            if self._leg_index == 0:
                # Completed the first, flat crossing, turn back for the second one, this time
                # with the diagonal pair's altitude offset baked into the target from the start.
                old_start = self._start
                self._start = self._target
                self._target = (old_start[0], old_start[1], ALTITUDE + self._altitude_offset)
                self._leg_index = 1
            else:
                # Completed the second (offset) crossing, the showcase calls for exactly two
                # crossings, so stop here rather than starting a third leg.
                self._finished = True
                self.orca_plugin.set_goal_velocity(0.0, 0.0, 0.0)
                self.provider.send_mobility_command(SetVelocityMobilityCommand(0.0, 0.0, 0.0))
                return

        goal_velocity = _goto_velocity(self._last_position, self._target, CRUISE_SPEED)
        self.orca_plugin.set_goal_velocity(*goal_velocity)

        if self.orca_plugin.is_colliding and self.orca_plugin.avoidance_velocity is not None:
            velocity = self.orca_plugin.avoidance_velocity
        else:
            velocity = goal_velocity

        self.provider.send_mobility_command(SetVelocityMobilityCommand(*velocity))

    def finish(self) -> None:
        colliding_ticks = sum(1 for row in self.df if row["colliding"])
        colliding_seconds = colliding_ticks * DYNAMIC_VELOCITY_CONFIG.update_rate
        print(
            f"Node {self.node_id}: completed {self._legs_completed} legs, "
            f"spent {colliding_seconds:.1f}s of the run avoiding a collision"
        )


HEAD_ON_TIMER_TAG = "HeadOnOrcaProtocol__control_timer"


class HeadOnOrcaProtocol(IProtocol):
    """
    Minimal single-leg ORCA demo used for the 2- and 3-drone head-on scenarios: flies straight
    from a start position to a target position its own entry in HEAD_ON_PATHS.
    """

    def __init__(self):
        super().__init__()
        self.node_id: Optional[int] = None
        self.orca_plugin: Optional[OrcaAvoidancePlugin] = None

        self._target: Position = (0.0, 0.0, 0.0)
        self._last_position: Optional[Position] = None
        self._finished = False

        self.df = []

    def initialize(self) -> None:
        self.node_id = self.provider.get_id()
        start, self._target = HEAD_ON_PATHS[self.node_id]

        config = build_orca_configuration(DYNAMIC_VELOCITY_CONFIG)
        self.orca_plugin = OrcaAvoidancePlugin(self, config)

        print(f"Node {self.node_id}: flying {start} -> {self._target}")

        # Small per-node stagger so drones don't all take their first control step at the exact
        # same instant - same rationale as SquareShuttleOrcaProtocol's own start-time offset.
        self._schedule_control_tick(self.node_id * 0.5)

    def _schedule_control_tick(self, delay: float) -> None:
        self.provider.schedule_timer(HEAD_ON_TIMER_TAG, self.provider.current_time() + delay)

    def handle_timer(self, timer: str) -> None:
        if timer != HEAD_ON_TIMER_TAG:
            return

        self._control_step()
        self._schedule_control_tick(CONTROL_PERIOD)

    def handle_packet(self, message: str) -> None:
        pass

    def handle_telemetry(self, telemetry: DynamicVelocityTelemetry) -> None:
        if not isinstance(telemetry, DynamicVelocityTelemetry):
            return

        self._last_position = telemetry.current_position

        self.df.append({
            "t": self.provider.current_time(),
            "x": telemetry.current_position[0],
            "y": telemetry.current_position[1],
            "z": telemetry.current_position[2],
            "vx": telemetry.current_velocity[0],
            "vy": telemetry.current_velocity[1],
            "vz": telemetry.current_velocity[2],
            "colliding": self.orca_plugin.is_colliding if self.orca_plugin is not None else False,
        })

    def _control_step(self) -> None:
        if self._last_position is None or self._finished:
            return

        if math.dist(self._last_position, self._target) <= ARRIVAL_TOLERANCE:
            self._finished = True
            self.orca_plugin.set_goal_velocity(0.0, 0.0, 0.0)
            self.provider.send_mobility_command(SetVelocityMobilityCommand(0.0, 0.0, 0.0))
            return

        goal_velocity = _goto_velocity(self._last_position, self._target, CRUISE_SPEED)
        self.orca_plugin.set_goal_velocity(*goal_velocity)

        if self.orca_plugin.is_colliding and self.orca_plugin.avoidance_velocity is not None:
            velocity = self.orca_plugin.avoidance_velocity
        else:
            velocity = goal_velocity

        self.provider.send_mobility_command(SetVelocityMobilityCommand(*velocity))

    def finish(self) -> None:
        colliding_ticks = sum(1 for row in self.df if row["colliding"])
        colliding_seconds = colliding_ticks * DYNAMIC_VELOCITY_CONFIG.update_rate
        print(
            f"Node {self.node_id}: reached target, "
            f"spent {colliding_seconds:.1f}s of the run avoiding a collision"
        )
