"""
Velocity-driven mobility handler for GrADyS-SIM NG.

This handler provides realistic, velocity-based mobility for nodes with
explicit acceleration and velocity constraints. It is designed for
distributed controllers that output velocity commands, such as
soliton-like wave-based control laws for swarm encirclement.

Author: Laércio Lucchesi
Date: December 27, 2025
"""

from typing import Dict, Tuple

from gradysim.protocol.messages.mobility import MobilityCommand, MobilityCommandType
from gradysim.simulator.event import EventLoop
from gradysim.simulator.node import Node
from gradysim.simulator.handler.interface import INodeHandler
from gradysim.protocol.messages.telemetry import Telemetry

from .config import InertialMobilityConfiguration
from .core import (
    apply_acceleration_limits,
    apply_velocity_limits,
    apply_velocity_tracking_first_order,
    integrate_position,
)
from .telemetry import InertialTelemetry


class InertialMobilityHandler(INodeHandler):
    """
    Velocity-driven mobility handler for GrADyS-SIM NG.
    
    This handler updates node positions based on velocity commands with
    realistic physical constraints (velocity and acceleration limits).
    
    Key features:
    - Direct velocity control (no waypoints)
    - Independent horizontal and vertical constraints
    - Acceleration-limited velocity tracking (optionally with 1st-order lag via tau)
    - Optional telemetry emission
    
    Usage:
        config = VelocityMobilityConfiguration(
            update_rate=0.1,
            max_speed_xy=10.0,
            max_speed_z=5.0,
            max_acc_xy=2.0,
            max_acc_z=1.0
        )
        handler = VelocityMobilityHandler(config)
        
        # In your protocol handler:
        handler.set_velocity(node.identifier, (vx, vy, vz))
    """
    
    def __init__(self, config: InertialMobilityConfiguration):
        """
        Initialize the velocity mobility handler.
        
        Args:
            config: Configuration parameters for mobility constraints and update rate.
        """
        self._config = config
        self._loop: EventLoop = None
        self._nodes: Dict[int, Node] = {}  # Track all registered nodes
        
        # Per-node state: current velocity and desired velocity
        self._current_velocity: Dict[int, Tuple[float, float, float]] = {}
        self._desired_velocity: Dict[int, Tuple[float, float, float]] = {}
        
        # Telemetry tracking: count updates per node
        self._update_counter: Dict[int, int] = {}
    
    @staticmethod
    def get_label() -> str:
        return "mobility"

    def register_node(self, node: Node):
        """
        Register a node with this handler (called when node is created).
        
        Args:
            node: The node instance to register.
        """
        # Initialize state for this node
        node_id = node.id
        self._nodes[node_id] = node
        self._current_velocity[node_id] = (0.0, 0.0, 0.0)
        self._desired_velocity[node_id] = (0.0, 0.0, 0.0)
        self._update_counter[node_id] = 0
    
    def inject(self, event_loop: EventLoop):
        """
        Inject the event loop into the handler.
        
        Args:
            event_loop: The event loop for scheduling periodic updates.
        """
        self._loop = event_loop
    
    def initialize(self):
        """
        Start the periodic mobility update loop.
        
        Schedules the first mobility update event for all nodes.
        """
        if self._nodes:  # Only schedule if we have nodes
            self._loop.schedule_event(
                self._loop.current_time + self._config.update_rate,
                self._mobility_update
            )

    def finalize(self):
        """Finalize handler after simulation ends (not used by this handler)."""
        pass
    
    def after_simulation_step(self, iteration: int, time: float):
        """
        Called after each simulation step.
        
        Args:
            iteration: Current simulation iteration number
            time: Current simulation time
        """
        pass

    def handle_command(self, command: MobilityCommand, node: Node):
        """
        Performs a mobility command. This method is called by the node's
        provider to transmit it's mobility command to the mobility handler.

        Args:
            command: Command being issued
            node: Node that issued the command
        """
        if node.id not in self._nodes:
            raise Exception("Error handling commands: Cannot handle command from unregistered node")

        if command.command_type == MobilityCommandType.SET_SPEED:
            if command.param_1 is None or command.param_2 is None or command.param_3 is None:
                raise Exception("Velocity SET_SPEED command requires three parameters (vx, vy, vz). "
                                "Make sure that the command is properly constructed using SetVelocityMobilityCommand.")
            self._set_velocity(node.id, (command.param_1, command.param_2, command.param_3))
        else:
            raise Exception("The only command accepted in VelocityMobilityHandler is SET_SPEED")
    
    def _set_velocity(self, node_id: int, v_des: Tuple[float, float, float]) -> None:
        """
        Set the desired velocity for a node.
        
        The velocity persists until updated by a new command. To stop a node,
        explicitly command zero velocity: (0.0, 0.0, 0.0).
        
        Args:
            node_id: Identifier of the node to control.
            v_des: Desired velocity as (vx, vy, vz) in m/s.
        
        Example:
            # Move northeast at 5 m/s horizontally, ascending at 2 m/s
            handler.set_velocity(node.id, (3.54, 3.54, 2.0))
            
            # Stop the node
            handler.set_velocity(node.id, (0.0, 0.0, 0.0))
        """
        if node_id not in self._desired_velocity:
            # Initialize state if node not yet known
            self._current_velocity[node_id] = (0.0, 0.0, 0.0)
            self._desired_velocity[node_id] = v_des
            self._update_counter[node_id] = 0
        else:
            self._desired_velocity[node_id] = v_des
    
    def _get_node_velocity(self, node_id: int) -> Tuple[float, float, float] | None:
        """
        Get the current velocity of a node.
        
        Args:
            node_id: ID of the node
            
        Returns:
            Velocity vector (vx, vy, vz) in m/s, or None if node not registered
        """
        return self._current_velocity.get(node_id)

    def _get_node_position(self, node_id: int) -> Tuple[float, float, float] | None:
        """
        Get the current position of a node.
        
        Args:
            node_id: ID of the node
            
        Returns:
            Position vector (x, y, z) in meters, or None if node not registered
        """
        node = self._nodes.get(node_id)
        return node.position if node is not None else None
    
    def _mobility_update(self):
        """
        Perform a single mobility update step for all nodes.
        
        This method:
        1. Iterates through all registered nodes
        2. Retrieves the current and desired velocities for each
        3. Applies acceleration limits to compute the new velocity
        4. Applies velocity saturation
        5. Updates the node position using numerical integration
        6. Optionally emits telemetry
        7. Schedules the next update
        """
        dt = self._config.update_rate
        
        # Update all nodes
        for node_id, node in self._nodes.items():
            # Get current and desired velocities
            v_current = self._current_velocity[node_id]
            v_desired = self._desired_velocity[node_id]
            
            # UAV trajectory model:
            # - The protocol commands a desired velocity v_desired.
            # - The vehicle tracks it with bounded acceleration.
            # - Optionally, a 1st-order lag (time constant tau) shapes the transient:
            #       a* = (v_des - v) / tau
            #   then a is saturated and integrated.
            if self._config.tau_xy is None and self._config.tau_z is None:
                v_new = apply_acceleration_limits(
                    v_current,
                    v_desired,
                    dt,
                    self._config.max_acc_xy,
                    self._config.max_acc_z,
                )
            else:
                v_new = apply_velocity_tracking_first_order(
                    v_current,
                    v_desired,
                    dt,
                    self._config.max_acc_xy,
                    self._config.max_acc_z,
                    tau_xy=self._config.tau_xy,
                    tau_z=self._config.tau_z,
                )
            
            # Apply velocity saturation
            v_new = apply_velocity_limits(
                v_new,
                self._config.max_speed_xy,
                self._config.max_speed_z
            )
            
            # Update position: x_{k+1} = x_k + v_k * dt
            new_pos = integrate_position(node.position, v_new, dt)
            node.position = new_pos
            
            # Update stored velocity
            self._current_velocity[node_id] = v_new
            
            # Update counter and emit telemetry if needed
            self._update_counter[node_id] += 1
            if self._should_emit_telemetry(node_id):
                self._emit_telemetry(node)
        
        # Schedule next update
        self._loop.schedule_event(
            self._loop.current_time + self._config.update_rate,
            self._mobility_update
        )
    
    def _should_emit_telemetry(self, node_id: int) -> bool:
        """
        Determine if telemetry should be emitted on this update.
        
        Args:
            node_id: Identifier of the node.
        
        Returns:
            True if telemetry should be emitted, False otherwise.
        """
        if not self._config.send_telemetry:
            return False
        
        count = self._update_counter[node_id]
        return (count % self._config.telemetry_decimation) == 0
    
    def _emit_telemetry(self, node: Node):
        """
        Emit a Telemetry message with the current node position.
        
        Args:
            node: The node to emit telemetry for.
        
        The telemetry is sent directly to the node's protocol encapsulator.
        """
        telemetry = InertialTelemetry(
            current_position=node.position,
            current_velocity=self._get_node_position(node.id),
        )
        
        # Schedule telemetry delivery to protocol (same pattern as MobilityHandler)
        def send_telemetry():
            node.protocol_encapsulator.handle_telemetry(telemetry)
        
        self._loop.schedule_event(
            self._loop.current_time,
            send_telemetry,
            f"Node {node.id} handle_telemetry"
        )
