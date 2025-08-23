"""
Gradysim Adapter for Raft Lite

This module provides an adapter for integrating Raft Lite with the Gradysim
simulation platform. It implements the necessary callbacks to bridge between
Raft Lite's internal operations and Gradysim's API.

Usage:
    from raft_fault import GradysimAdapter
    
    # Create adapter with Gradysim provider
    adapter = GradysimAdapter(provider)
    
    # Use adapter with RaftConsensus (simplified with adapter injection)
    consensus = RaftConsensus(
        config=config,
        adapter=adapter
    )
    
    # Get node position from telemetry
    position = adapter.get_node_position(telemetry)
    print(f"Node position: {position}")
"""

from typing import Optional


class GradysimAdapter:
    """
    Adapter for integrating Raft Lite with Gradysim simulation platform.
    
    This adapter provides the necessary callbacks to bridge between Raft Lite's
    internal operations and Gradysim's communication and timing APIs.
    
    Attributes:
        provider: Gradysim provider instance that provides communication
                 and timing services
    """
    
    def __init__(self, provider, protocol=None):
        """
        Initialize the Gradysim adapter.
        
        Args:
            provider: Gradysim provider instance that provides:
                     - send_communication_command()
                     - schedule_timer()
                     - cancel_timer()
                     - current_time()
                     - get_id()
            protocol: Optional protocol instance for visualization (if None, will try to get from provider)
        """
        self.provider = provider
        self.protocol = protocol
    
    def get_node_id(self) -> int:
        """
        Get the current node ID via Gradysim provider.
        
        Returns:
            Current node ID as integer
        """
        try:
            return self.provider.get_id()
        except Exception as e:
            print(f"Error getting node ID: {e}")
            # Return a fallback value to prevent crashes
            return -1
    
    def send_message(self, message: str, target_id: int) -> None:
        """
        Send message to a specific node via Gradysim communication system.
        
        This method converts Raft Lite's message sending request into
        a Gradysim communication command for point-to-point communication.
        
        Args:
            message: Message content to send (JSON string)
            target_id: ID of the target node
        """
        try:
            # Create Gradysim communication command for point-to-point
            command = self._create_communication_command(message, target_id, is_broadcast=False)
            self.provider.send_communication_command(command)
            
            # DO NOT record heartbeat response here - it should only be recorded
            # when we actually receive a response from the target node
            # The failure detection system should be based on responses received,
            # not messages sent
            
        except Exception as e:
            # Log error but don't record for failure detection
            # Only record failures when we actually fail to send the message
            print(f"Error sending message to node {target_id}: {e}")
    
    def send_broadcast(self, message: str) -> None:
        """
        Send broadcast message to all nodes via Gradysim communication system.
        
        This method converts Raft Lite's broadcast request into
        a Gradysim communication command for broadcast communication.
        
        Args:
            message: Message content to broadcast (JSON string)
        """
        try:
            # Create Gradysim communication command for broadcast
            command = self._create_communication_command(message, None, is_broadcast=True)
            self.provider.send_communication_command(command)
        except Exception as e:
            # Log error but don't crash - Raft Lite should handle failures gracefully
            print(f"Error sending broadcast message: {e}")
    
    def schedule_timer(self, timer_name: str, delay_ms: int) -> None:
        """
        Schedule timer via Gradysim timing system.
        
        This method converts Raft Lite's timer scheduling request into
        a Gradysim timer. The delay is converted from milliseconds to seconds
        and added to the current time for absolute timing.
        
        Args:
            timer_name: Name of the timer
            delay_ms: Delay in milliseconds
        """
        try:
            # Convert milliseconds to seconds
            delay_seconds = delay_ms / 1000.0
            
            # Schedule timer with absolute time (current time + delay)
            absolute_time = self.provider.current_time() + delay_seconds
            self.provider.schedule_timer(timer_name, absolute_time)
        except Exception as e:
            print(f"Error scheduling timer '{timer_name}': {e}")
    
    def cancel_timer(self, timer_name: str) -> None:
        """
        Cancel timer via Gradysim timing system.
        
        Args:
            timer_name: Name of the timer to cancel
        """
        try:
            self.provider.cancel_timer(timer_name)
        except Exception as e:
            print(f"Error canceling timer '{timer_name}': {e}")
    
    def get_current_time(self) -> float:
        """
        Get current simulation time via Gradysim.
        
        Returns:
            Current simulation time in seconds
            
        Raises:
            RuntimeError: If unable to get simulation time
        """
        try:
            return self.provider.current_time()
        except Exception as e:
            raise RuntimeError(f"Failed to get simulation time: {e}")
    
    def get_node_position(self, telemetry) -> tuple:
        """
        Get the current node's position from a Telemetry object as a tuple (x, y, z).

        Args:
            telemetry: Telemetry object from Gradysim

        Returns:
            Tuple (x, y, z) representing the node's position.
        """
        try:
            return tuple(telemetry.current_position)
        except Exception as e:
            print(f"Error getting node position from telemetry: {e}")
            return (0.0, 0.0, 0.0)

    def paint_node(self, color: str, node_id: Optional[int] = None):
        """
        Paint the node with the given color name using the VisualizationController.
        Args:
            color (str): Name of the color (e.g., 'red', 'blue', etc.)
            node_id (int, optional): ID of the node to paint. If None, paints the current node.
        """
        from gradysim.simulator.extension.visualization_controller import VisualizationController

        COLOR_MAP = {
            "red":    (255, 0, 0),
            "blue":   (0, 0, 255),
            "green":  (0, 255, 0),
            "yellow": (255, 255, 0),
            "purple": (255, 0, 255),
            "cyan":   (0, 255, 255),
            "white":  (255, 255, 255),
            "black":  (0, 0, 0),
            "orange": (255, 165, 0),
            "pink":   (255, 192, 203),
            "gray":   (128, 128, 128),
            "brown":  (139, 69, 19)
        }
    
        # Use provided node_id or current node's ID
        target_node_id = node_id if node_id is not None else self.provider.get_id()
        color_rgb = COLOR_MAP.get(color.lower(), (0, 0, 0))  # Default to black if not found
        
        # Create VisualizationController with the protocol
        try:
            # Use stored protocol or try to get from provider
            protocol = self.protocol or getattr(self.provider, 'protocol', None)
            
            if protocol is not None:
                visual_controller = VisualizationController(protocol)
                visual_controller.paint_node(target_node_id, color_rgb)
            else:
                print(f"Warning: Could not get protocol instance for visualization. Node {target_node_id} color change to {color} ignored.")
        except Exception as e:
            print(f"Error painting node {target_node_id} with color {color}: {e}")

    def _create_communication_command(self, message: str, target_id: Optional[int], is_broadcast: bool = False):
        """
        Create a Gradysim communication command.
        
        This method creates the appropriate communication command object
        that Gradysim expects. The exact implementation depends on the
        Gradysim version and API.
        
        Args:
            message: Message content
            target_id: Target node ID (None for broadcast)
            is_broadcast: Whether this is a broadcast message
            
        Returns:
            Gradysim communication command object
        """
        # Try to import Gradysim communication classes
        try:
            from gradysim.protocol.messages.communication import CommunicationCommand, CommunicationCommandType
            
            if is_broadcast:
                return CommunicationCommand(CommunicationCommandType.BROADCAST, message)
            else:
                return CommunicationCommand(CommunicationCommandType.SEND, message, target_id)
        except ImportError:
            # Fallback for different Gradysim versions or if import fails
            # Create a simple command object with the required attributes
            class SimpleCommand:
                def __init__(self, command_type, message, destination=None):
                    self.command_type = command_type
                    self.message = message
                    self.destination = destination
            
            if is_broadcast:
                return SimpleCommand("BROADCAST", message)
            else:
                return SimpleCommand("SEND", message, target_id)
    
    def __str__(self) -> str:
        """Return string representation of the adapter."""
        return f"GradysimAdapter(provider={type(self.provider).__name__})"
    
    def get_callbacks(self) -> dict:
        """
        Get all callbacks as a dictionary for easy unpacking.
        
        This method returns all the callbacks needed by RaftConsensus
        as keyword arguments that can be unpacked with **.
        
        Returns:
            Dictionary with all callback methods
            
        Example:
            # Simple way (recommended):
            consensus = RaftConsensus(config, adapter=adapter)
            
            # Alternative way (manual callbacks):
            consensus = RaftConsensus(config, **adapter.get_callbacks())
        """
        callbacks = {
            'send_message_callback': self.send_message,
            'send_broadcast_callback': self.send_broadcast,  # Add broadcast callback
            'schedule_timer_callback': self.schedule_timer,
            'cancel_timer_callback': self.cancel_timer,
            'get_current_time_callback': self.get_current_time,
            'get_node_id_callback': self.get_node_id,
            'get_node_position_callback': self.get_node_position,
            # Visualization callback
            'paint_node_callback': self.paint_node
        }
        
        return callbacks
    
    def set_failure_detector(self, failure_detector) -> None:
        """
        Set the failure detector to enable connectivity-based failure detection.
        
        Args:
            failure_detector: HeartbeatDetector instance
        """
        self._failure_detector = failure_detector
    
    def __repr__(self) -> str:
        """Return detailed string representation of the adapter."""
        return f"GradysimAdapter(provider={self.provider})" 