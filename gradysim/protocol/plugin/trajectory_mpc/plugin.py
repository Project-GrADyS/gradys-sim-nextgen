"""
This module declares a plugin that lets a protocol follow a time-parameterized trajectory using
a Model Predictive Controller.

Beware that this plugin controls your protocol's mobility to implement its behaviour, so you
should not use any other mobility plugin with it or implement any mobility behaviour in your
protocol while a trajectory is in progress.
"""

import logging
from typing import Optional, Tuple

import numpy as np

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.mobility import SetVelocityMobilityCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.plugin.dispatcher import create_dispatcher, DispatchReturn
from gradysim.protocol.position import squared_distance
from gradysim.simulator.handler.mobility.dynamic_velocity.telemetry import DynamicVelocityTelemetry

from .config import TrajectoryMPCConfiguration
from .mpc import DoubleIntegratorMPC
from .reference import ITrajectoryReference

CONTROL_TIMER_TAG = "TrajectoryMPCPlugin__control_timer"
"""The plugin drives its control loop using a timer with this name, make sure it doesn't
conflict with other timers your protocol schedules."""


class TrajectoryMPCPluginException(Exception):
    pass


class TrajectoryMPCPlugin:
    """
    Use this plugin if you want your node to follow a time-parameterized trajectory using
    a Model Predictive Controller that outputs velocity commands.

    This plugin requires the node's mobility to be provided by Dynamic Velocity Mobility Handler.
    It also needs both position and velocity telemetry and sends velocity mobility commands. 

    """

    def __init__(self, protocol: IProtocol, configuration: TrajectoryMPCConfiguration):

        self._dispatcher = create_dispatcher(protocol)
        self._protocol = protocol
        self._config = configuration
        self._logger = logging.getLogger()

        self._mpc = DoubleIntegratorMPC(
            dt=configuration.control_period,
            horizon_steps=configuration.horizon_steps,
            max_speed_xy_box=configuration.max_speed_xy_box,
            max_speed_z=configuration.max_speed_z,
            max_acc_xy_box=configuration.max_acc_xy_box,
            max_acc_z=configuration.max_acc_z,
            position_weight=configuration.position_weight,
            velocity_weight=configuration.velocity_weight,
            control_weight=configuration.control_weight,
            control_rate_weight=configuration.control_rate_weight,
            terminal_position_weight=configuration.terminal_position_weight,
            terminal_velocity_weight=configuration.terminal_velocity_weight,
            tau_xy=configuration.tau_xy,
            tau_z=configuration.tau_z,
        )

        self._reference: Optional[ITrajectoryReference] = None
        self._trajectory_start_time: Optional[float] = None
        self._active: bool = False
        self._completed: bool = False

        self._last_position: Optional[Tuple[float, float, float]] = None
        self._last_velocity: Optional[Tuple[float, float, float]] = None

        self._initialize_telemetry_handling()
        self._initialize_control_loop()

    def _initialize_telemetry_handling(self) -> None:
        """Caches the latest position/velocity telemetry for use in the control loop."""

        def telemetry_handler(_instance: IProtocol, telemetry: Telemetry) -> DispatchReturn:
            if not isinstance(telemetry, DynamicVelocityTelemetry):
                raise TrajectoryMPCPluginException(
                    "TrajectoryMPCPlugin requires DynamicVelocityTelemetry, which is only emitted "
                    "by DynamicVelocityMobilityHandler. Make sure your simulation uses that "
                    "mobility handler."
                )

            self._last_position = telemetry.current_position
            self._last_velocity = telemetry.current_velocity
            return DispatchReturn.CONTINUE

        self._dispatcher.register_handle_telemetry(telemetry_handler)

    def _initialize_control_loop(self) -> None:
        """Drives the periodic MPC solve/command cycle from a dedicated timer."""

        def timer_handler(_instance: IProtocol, timer: str) -> DispatchReturn:
            if timer != CONTROL_TIMER_TAG:
                return DispatchReturn.CONTINUE

            if self._active:
                self._control_step()

            return DispatchReturn.INTERRUPT

        self._dispatcher.register_handle_timer(timer_handler)

    def _schedule_control_tick(self, delay: float) -> None:
        self._protocol.provider.schedule_timer(
            CONTROL_TIMER_TAG,
            self._protocol.provider.current_time() + delay,
        )

    def _build_reference_horizon(self, elapsed: float) -> np.ndarray:
        horizon = self._config.horizon_steps
        dt = self._config.control_period

        reference_states = np.zeros((6, horizon + 1))
        for k in range(horizon + 1):
            ref_position, ref_velocity = self._reference.evaluate(elapsed + k * dt)
            reference_states[0, k] = ref_position[0]
            reference_states[1, k] = ref_velocity[0]
            reference_states[2, k] = ref_position[1]
            reference_states[3, k] = ref_velocity[1]
            reference_states[4, k] = ref_position[2]
            reference_states[5, k] = ref_velocity[2]

        return reference_states

    def _control_step(self) -> None:
        if self._last_position is None or self._last_velocity is None:
            # No telemetry received yet, expected for the very first tick, since it fires
            # before DynamicVelocityMobilityHandler emits its first update. Just try again soon.
            self._logger.debug("Trajectory MPC: no telemetry received yet, skipping control step")
            self._schedule_control_tick(self._config.control_period)
            return

        now = self._protocol.provider.current_time()
        elapsed = now - self._trajectory_start_time

        reference_states = self._build_reference_horizon(elapsed)
        command = self._mpc.solve(self._last_position, self._last_velocity, reference_states)
        self._protocol.provider.send_mobility_command(SetVelocityMobilityCommand(*command))

        if self._has_reached_end(elapsed):
            self._logger.info("Trajectory MPC: trajectory finished")
            self._protocol.provider.send_mobility_command(SetVelocityMobilityCommand(0.0, 0.0, 0.0))
            self._completed = True
            self._deactivate()
            return

        self._schedule_control_tick(self._config.control_period)

    def _has_reached_end(self, elapsed: float) -> bool:
        """Whether the node is past the trajectory's final waypoint time and within tolerance
        of its position. Assumes a trajectory is currently active."""
        if elapsed < self._reference.final_time:
            return False

        distance_squared = squared_distance(self._last_position, self._reference.final_position)
        return distance_squared <= self._config.tolerance ** 2

    def start_trajectory(self, reference: ITrajectoryReference) -> None:
        """
        Starts following a trajectory. The node will use an MPC controller to compute velocity
        commands that track the given reference as closely as the vehicle's speed/acceleration
        limits allow.

        Calling this while a trajectory is already in progress replaces it with the new one and
        restarts the trajectory clock at the current simulation time.

        Args:
            reference: Time-parameterized position/velocity reference to track, with time
                measured in seconds since the trajectory starts. Use `PiecewiseLinearReference` for a straight-line interpolation between
                waypoints, or implement `ITrajectoryReference` for something else.
        """
        # Cancel any control tick left over from a previous trajectory before scheduling a fresh
        self._protocol.provider.cancel_timer(CONTROL_TIMER_TAG)

        self._reference = reference
        self._trajectory_start_time = self._protocol.provider.current_time()
        self._active = True
        self._completed = False

        self._logger.info(f"Trajectory MPC: starting trajectory (final time {reference.final_time:.1f}s)")
        self._schedule_control_tick(0.0)

    def _deactivate(self) -> None:
        self._active = False
        self._reference = None
        self._trajectory_start_time = None

    def stop_trajectory(self) -> None:
        """
        Stops following the current trajectory, if there is one.

        Calling this yourself (e.g. to hand off control to something else) leaves the node at
        whatever velocity it was last commanded to have.
        """
        if not self._active:
            return

        self._deactivate()
        self._protocol.provider.cancel_timer(CONTROL_TIMER_TAG)

        self._logger.info("Trajectory MPC: stopping trajectory")

    @property
    def is_idle(self) -> bool:
        """True if no trajectory is currently being followed."""
        return not self._active

    @property
    def is_finished(self) -> bool:
        """
        True if the most recently started trajectory ran to completion.
        """
        return self._completed
