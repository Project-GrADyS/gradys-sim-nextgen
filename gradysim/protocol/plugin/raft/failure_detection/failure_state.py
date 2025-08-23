"""
Failure State Management

This module manages the state of node failures in the Raft cluster.
"""

from typing import Dict, Set, Optional
from enum import Enum


class NodeStatus(Enum):
    """Status of a node in the cluster."""
    ACTIVE = "active"
    FAILED = "failed"
    UNKNOWN = "unknown"


class FailureState:
    """
    Manages the failure state of nodes in the Raft cluster.
    
    This class tracks which nodes are active, failed, or unknown,
    and maintains statistics for failure detection.
    """
    
    def __init__(self, known_nodes: Set[int]):
        """
        Initialize failure state for known nodes.
        
        Args:
            known_nodes: Set of all known node IDs in the cluster
        """
        self._known_nodes = known_nodes.copy()
        self._node_status: Dict[int, NodeStatus] = {}
        self._consecutive_failures: Dict[int, int] = {}
        self._consecutive_successes: Dict[int, int] = {}
        self._last_heartbeat_response: Dict[int, float] = {}
        
        # Initialize all known nodes as active
        for node_id in known_nodes:
            self._node_status[node_id] = NodeStatus.ACTIVE
            self._consecutive_failures[node_id] = 0
            self._consecutive_successes[node_id] = 0
    
    def record_heartbeat_response(self, node_id: int, timestamp: float, success: bool) -> None:
        """
        Record a heartbeat response from a node.
        
        Args:
            node_id: ID of the node that responded
            timestamp: Timestamp of the response
            success: Whether the heartbeat was successful
        """
        if node_id not in self._known_nodes:
            return  # Ignore unknown nodes
        
        self._last_heartbeat_response[node_id] = timestamp
        
        if success:
            self._consecutive_successes[node_id] += 1
            self._consecutive_failures[node_id] = 0
        else:
            self._consecutive_failures[node_id] += 1
            self._consecutive_successes[node_id] = 0
    
    def check_node_failure_with_timeout(self, node_id: int, failure_threshold: int, timeout_ms: int, current_time: float) -> bool:
        """
        Check if a node should be marked as failed based on timeout and consecutive failures.
        
        Args:
            node_id: ID of the node to check
            failure_threshold: Number of consecutive failures to mark as failed
            timeout_ms: Timeout in milliseconds
            current_time: Current timestamp
            
        Returns:
            True if node should be marked as failed
        """
        if node_id not in self._known_nodes:
            return False
        
        # Check if we have a recent heartbeat response
        last_response = self._last_heartbeat_response.get(node_id)
        if last_response is not None:
            time_since_response = (current_time - last_response) * 1000  # Convert to ms
            
            # If timeout exceeded, count as a failure
            if time_since_response > timeout_ms:
                self._consecutive_failures[node_id] += 1
                self._consecutive_successes[node_id] = 0
                # self.logger.warning(f"Node {node_id} timeout: {time_since_response:.1f}ms > {timeout_ms}ms") # Original code had this line commented out
        
        # Check if we have enough consecutive failures
        if self._consecutive_failures[node_id] >= failure_threshold:
            if self._node_status[node_id] != NodeStatus.FAILED:
                self._node_status[node_id] = NodeStatus.FAILED
                return True
        return False
    
    def check_node_failure(self, node_id: int, failure_threshold: int) -> bool:
        """
        Check if a node should be marked as failed (legacy method for backward compatibility).
        
        Args:
            node_id: ID of the node to check
            failure_threshold: Number of consecutive failures to mark as failed
            
        Returns:
            True if node should be marked as failed
        """
        if node_id not in self._known_nodes:
            return False
        
        if self._consecutive_failures[node_id] >= failure_threshold:
            if self._node_status[node_id] != NodeStatus.FAILED:
                self._node_status[node_id] = NodeStatus.FAILED
                return True
        return False
    
    def check_node_recovery(self, node_id: int, recovery_threshold: int) -> bool:
        """
        Check if a node should be marked as recovered.
        
        Args:
            node_id: ID of the node to check
            recovery_threshold: Number of consecutive successes to mark as recovered
            
        Returns:
            True if node should be marked as recovered
        """
        if node_id not in self._known_nodes:
            return False
        
        if self._consecutive_successes[node_id] >= recovery_threshold:
            if self._node_status[node_id] != NodeStatus.ACTIVE:
                self._node_status[node_id] = NodeStatus.ACTIVE
                return True
        return False
    
    def get_failed_nodes(self) -> Set[int]:
        """Get set of currently failed nodes."""
        return {node_id for node_id, status in self._node_status.items() 
                if status == NodeStatus.FAILED}
    
    def get_active_nodes(self) -> Set[int]:
        """Get set of currently active nodes."""
        return {node_id for node_id, status in self._node_status.items() 
                if status == NodeStatus.ACTIVE}
    
    def get_node_status(self, node_id: int) -> NodeStatus:
        """Get the current status of a specific node."""
        return self._node_status.get(node_id, NodeStatus.UNKNOWN)
    
    def is_node_failed(self, node_id: int) -> bool:
        """Check if a specific node is currently failed."""
        return self._node_status.get(node_id) == NodeStatus.FAILED
    

    
    def get_statistics(self, node_id: int) -> Dict[str, int]:
        """Get failure statistics for a specific node."""
        if node_id not in self._known_nodes:
            return {}
        
        return {
            "consecutive_failures": self._consecutive_failures[node_id],
            "consecutive_successes": self._consecutive_successes[node_id],
            "status": self._node_status[node_id].value if hasattr(self._node_status[node_id], 'value') else str(self._node_status[node_id])
        }
    
    def get_timeout_statistics(self, node_id: int, current_time: float) -> Dict[str, float]:
        """
        Get timeout statistics for a specific node.
        
        Args:
            node_id: ID of the node
            current_time: Current timestamp
            
        Returns:
            Dictionary with timeout statistics
        """
        if node_id not in self._known_nodes:
            return {}
        
        last_response = self._last_heartbeat_response.get(node_id)
        time_since_response = None
        
        if last_response is not None:
            time_since_response = (current_time - last_response) * 1000  # Convert to ms
        
        return {
            "last_response_timestamp": last_response or 0,
            "time_since_response_ms": time_since_response or 0,
            "consecutive_failures": self._consecutive_failures[node_id],
            "consecutive_successes": self._consecutive_successes[node_id]
        }
    
    def get_all_nodes(self) -> Set[int]:
        """Get all known nodes."""
        return self._known_nodes.copy()
    
    def add_node(self, node_id: int) -> None:
        """Add a new node to failure detection."""
        if node_id not in self._known_nodes:
            self._known_nodes.add(node_id)
            self._node_status[node_id] = NodeStatus.ACTIVE
            self._consecutive_failures[node_id] = 0
            self._consecutive_successes[node_id] = 0
    
    def remove_node(self, node_id: int) -> None:
        """Remove a node from failure detection."""
        if node_id in self._known_nodes:
            self._known_nodes.remove(node_id)
            self._node_status.pop(node_id, None)
            self._consecutive_failures.pop(node_id, None)
            self._consecutive_successes.pop(node_id, None)
            self._last_heartbeat_response.pop(node_id, None)
    
    def reset_node(self, node_id: int) -> None:
        """Reset failure statistics for a specific node."""
        if node_id in self._known_nodes:
            self._node_status[node_id] = NodeStatus.ACTIVE
            self._consecutive_failures[node_id] = 0
            self._consecutive_successes[node_id] = 0
    
    def __str__(self) -> str:
        """String representation of the failure state."""
        active = len(self.get_active_nodes())
        failed = len(self.get_failed_nodes())
        total = len(self._known_nodes)
        
        return (f"FailureState(active={active}, failed={failed}, "
                f"total={total}, failed_nodes={self.get_failed_nodes()})") 