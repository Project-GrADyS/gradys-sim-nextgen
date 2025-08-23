"""
Heartbeat-based Failure Detection

This module implements heartbeat-based failure detection for Raft nodes.
"""

import logging
from typing import Callable, Dict, Set, Optional, Any
from .failure_config import FailureConfig
from .failure_state import FailureState, NodeStatus
import time


class HeartbeatDetector:
    """
    Heartbeat-based failure detector for Raft nodes.
    
    Monitors heartbeat responses from all nodes and detects failures
    based on consecutive missed heartbeats.
    """
    
    def __init__(self, config: FailureConfig, known_nodes: Set[int], 
                 on_failure_callback: Optional[Callable[[int], None]] = None,
                 on_recovery_callback: Optional[Callable[[int], None]] = None,
                 get_current_time_callback: Optional[Callable[[], float]] = None):
        """
        Initialize heartbeat detector.
        
        Args:
            config: Failure detection configuration
            known_nodes: Set of all known node IDs
            on_failure_callback: Callback called when a node failure is detected
            on_recovery_callback: Callback called when a node recovery is detected
            get_current_time_callback: Callback to get current simulation time (optional)
        """
        self.config = config
        self.failure_state = FailureState(known_nodes)
        self._detection_enabled = True  # Always enabled when detector is created
        self._heartbeat_counter = 0
        self._on_failure_callback = on_failure_callback
        self._on_recovery_callback = on_recovery_callback
        self._get_current_time_callback = get_current_time_callback
        
        # Initialize metrics
        self._metrics = {
            'total_heartbeats_sent': 0,
            'total_responses_received': 0,
            'total_successful_responses': 0,
            'total_failed_responses': 0,
            'total_failures_detected': 0,
            'total_recoveries_detected': 0,
            'average_response_time_ms': 0.0,
            'detection_latency_ms': 0.0,
            'last_detection_check_time': 0.0,
            'node_response_times': {},  # {node_id: [response_times]}
            'node_failure_history': {},  # {node_id: [failure_timestamps]}
            'node_recovery_history': {}  # {node_id: [recovery_timestamps]}
        }
        
        # Setup logging
        self.logger = logging.getLogger("HeartbeatDetector")
        self.logger.setLevel(logging.INFO)
        
        self.logger.info(f"Failure detection enabled with threshold {config.failure_threshold}")
        if get_current_time_callback:
            self.logger.info("Using simulation time callback for failure detection")
        else:
            self.logger.info("Using system time for failure detection")
    
    def record_heartbeat_sent(self, node_id: int) -> None:
        """
        Record that a heartbeat was sent to a node.
        
        Args:
            node_id: ID of the node that received the heartbeat
        """
        if not self._detection_enabled:
            return
        
        # Update metrics
        self._metrics['total_heartbeats_sent'] += 1
        
        # Log detailed heartbeat information
        self.logger.debug(f"Heartbeat sent to node {node_id} (total sent: {self._metrics['total_heartbeats_sent']})")
    
    def record_heartbeat_response(self, node_id: int, success: bool, response_time_ms: float = None) -> None:
        """
        Record a heartbeat response from a node.
        
        Args:
            node_id: ID of the node that responded
            success: Whether the heartbeat was successful
            response_time_ms: Response time in milliseconds (optional)
        """
        if not self._detection_enabled:
            return
        
        # Use simulation time callback
        if self._get_current_time_callback:
            current_time = self._get_current_time_callback()
        else:
            raise RuntimeError("No simulation time callback available")
        self.failure_state.record_heartbeat_response(node_id, current_time, success)
        
        # Update metrics
        self._metrics['total_responses_received'] += 1
        
        if success:
            self._metrics['total_successful_responses'] += 1
            self.logger.debug(f"Successful response from node {node_id}")
        else:
            self._metrics['total_failed_responses'] += 1
            self.logger.debug(f"Failed response from node {node_id}")
        
        # Update response time metrics if provided
        if response_time_ms is not None:
            if node_id not in self._metrics['node_response_times']:
                self._metrics['node_response_times'][node_id] = []
            
            self._metrics['node_response_times'][node_id].append(response_time_ms)
            
            # Keep only the last 10 response times per node
            if len(self._metrics['node_response_times'][node_id]) > 10:
                self._metrics['node_response_times'][node_id].pop(0)
            
            # Update average response time
            all_response_times = []
            for times in self._metrics['node_response_times'].values():
                all_response_times.extend(times)
            
            if all_response_times:
                self._metrics['average_response_time_ms'] = sum(all_response_times) / len(all_response_times)
    
    def on_heartbeat_sent(self) -> None:
        """
        Called when heartbeats are sent to all followers.
        Increments the heartbeat counter and schedules detection if needed.
        """
        if not self._detection_enabled:
            return
        
        self._heartbeat_counter += 1
        
        # Check if it's time to run detection
        if self._heartbeat_counter % self.config.detection_interval == 0:
            self._run_detection_check()
    
    def get_failed_nodes(self) -> Set[int]:
        """Get the set of currently failed nodes."""
        return self.failure_state.get_failed_nodes()
    
    def get_active_nodes(self) -> Set[int]:
        """Get the set of currently active nodes."""
        return self.failure_state.get_active_nodes()
    
    def is_node_failed(self, node_id: int) -> bool:
        """Check if a specific node is currently failed."""
        return self.failure_state.is_node_failed(node_id)
    

    
    def get_node_statistics(self, node_id: int) -> Dict[str, int]:
        """Get failure statistics for a specific node."""
        return self.failure_state.get_statistics(node_id)
    
    def get_node_timeout_statistics(self, node_id: int) -> Dict[str, float]:
        """
        Get timeout statistics for a specific node.
        
        Args:
            node_id: ID of the node
            
        Returns:
            Dictionary with timeout statistics including time since last response
        """
        # Use simulation time callback
        if self._get_current_time_callback:
            current_time = self._get_current_time_callback()
        else:
            raise RuntimeError("No simulation time callback available")
        return self.failure_state.get_timeout_statistics(node_id, current_time)
    
    def get_detection_summary(self) -> Dict[str, any]:
        """
        Get a summary of the failure detection system.
        
        Returns:
            Dictionary with detection summary
        """
        # Use simulation time callback
        if self._get_current_time_callback:
            current_time = self._get_current_time_callback()
        else:
            raise RuntimeError("No simulation time callback available")
        timeout_ms = self.config.get_timeout_ms()
        
        # Calculate success rate
        success_rate = 0.0
        if self._metrics['total_responses_received'] > 0:
            success_rate = (self._metrics['total_successful_responses'] / self._metrics['total_responses_received']) * 100
        
        summary = {
            "enabled": self._detection_enabled,
            "heartbeat_counter": self._heartbeat_counter,
            "detection_interval": self.config.detection_interval,
            "failure_threshold": self.config.failure_threshold,
            "recovery_threshold": self.config.recovery_threshold,
            "timeout_ms": timeout_ms,
            "total_nodes": len(self.failure_state.get_all_nodes()),
            "active_nodes": len(self.failure_state.get_active_nodes()),
            "failed_nodes": len(self.failure_state.get_failed_nodes()),
            "performance": {
                "total_heartbeats_sent": self._metrics['total_heartbeats_sent'],
                "total_responses_received": self._metrics['total_responses_received'],
                "success_rate_percent": success_rate,
                "average_response_time_ms": self._metrics['average_response_time_ms'],
                "detection_latency_ms": self._metrics['detection_latency_ms']
            },
            "detection_stats": {
                "total_failures_detected": self._metrics['total_failures_detected'],
                "total_recoveries_detected": self._metrics['total_recoveries_detected']
            },
            "node_details": {}
        }
        
        # Add details for each node
        for node_id in self.failure_state.get_all_nodes():
            timeout_stats = self.failure_state.get_timeout_statistics(node_id, current_time)
            node_metrics = {
                "status": "ACTIVE" if node_id in self.failure_state.get_active_nodes() else "FAILED",
                "time_since_response_ms": timeout_stats.get("time_since_response_ms", 0),
                "consecutive_failures": timeout_stats.get("consecutive_failures", 0),
                "consecutive_successes": timeout_stats.get("consecutive_successes", 0),
                "timeout_exceeded": timeout_stats.get("time_since_response_ms", 0) > timeout_ms,
                "recent_response_times": self._metrics['node_response_times'].get(node_id, [])[-3:],  # Last 3
                "failure_count": len(self._metrics['node_failure_history'].get(node_id, [])),
                "recovery_count": len(self._metrics['node_recovery_history'].get(node_id, []))
            }
            summary["node_details"][node_id] = node_metrics
        
        return summary
    
    def add_node(self, node_id: int) -> None:
        """Add a new node to failure detection."""
        self.failure_state.add_node(node_id)
        self.logger.info(f"Added node {node_id} to failure detection")
    
    def remove_node(self, node_id: int) -> None:
        """Remove a node from failure detection."""
        self.failure_state.remove_node(node_id)
        self.logger.info(f"Removed node {node_id} from failure detection")
    
    def reset_node(self, node_id: int) -> None:
        """Reset failure statistics for a specific node."""
        self.failure_state.reset_node(node_id)
        self.logger.info(f"Reset failure statistics for node {node_id}")
    
    def _run_detection_check(self) -> None:
        """
        Run failure detection check on all nodes.
        """
        if not self._detection_enabled:
            return
        
        # Use simulation time callback
        if self._get_current_time_callback:
            current_time = self._get_current_time_callback()
        else:
            raise RuntimeError("No simulation time callback available")
        timeout_ms = self.config.get_timeout_ms()
        
        # Calculate detection latency
        if self._metrics['last_detection_check_time'] > 0:
            detection_latency = (current_time - self._metrics['last_detection_check_time']) * 1000
            self._metrics['detection_latency_ms'] = detection_latency
            self.logger.debug(f"Detection check latency: {detection_latency:.2f}ms")
        
        self._metrics['last_detection_check_time'] = current_time
        
        # Check for failures using timeout
        for node_id in self.failure_state.get_all_nodes():
            if self.failure_state.check_node_failure_with_timeout(
                node_id, 
                self.config.failure_threshold, 
                timeout_ms, 
                current_time
            ):
                self.logger.warning(f"Node {node_id} marked as failed (timeout: {timeout_ms}ms)")
                
                # Update failure metrics
                self._metrics['total_failures_detected'] += 1
                if node_id not in self._metrics['node_failure_history']:
                    self._metrics['node_failure_history'][node_id] = []
                self._metrics['node_failure_history'][node_id].append(current_time)
                
                if self._on_failure_callback:
                    self._on_failure_callback(node_id)
            
            # Check for recoveries
            if self.failure_state.check_node_recovery(node_id, self.config.recovery_threshold):
                self.logger.info(f"Node {node_id} marked as recovered")
                
                # Update recovery metrics
                self._metrics['total_recoveries_detected'] += 1
                if node_id not in self._metrics['node_recovery_history']:
                    self._metrics['node_recovery_history'][node_id] = []
                self._metrics['node_recovery_history'][node_id].append(current_time)
                
                if self._on_recovery_callback:
                    self._on_recovery_callback(node_id)
    
    def _check_node_status(self, node_id: int) -> None:
        """
        Check the status of a specific node and update if necessary.
        
        Args:
            node_id: ID of the node to check
        """
        # Check for failure
        if self.failure_state.check_node_failure(node_id, self.config.failure_threshold):
            self.logger.warning(f"Node {node_id} marked as FAILED")
            self._on_node_failed(node_id)
        
        # Check for recovery
        if self.failure_state.check_node_recovery(node_id, self.config.recovery_threshold):
            self.logger.info(f"Node {node_id} marked as RECOVERED")
            self._on_node_recovered(node_id)
    
    def _on_node_failed(self, node_id: int) -> None:
        """
        Called when a node is detected as failed.
        
        Args:
            node_id: ID of the failed node
        """
        # Log detailed statistics
        stats = self.failure_state.get_statistics(node_id)
        self.logger.warning(
            f"Node {node_id} failed - "
            f"consecutive_failures={stats['consecutive_failures']}, "
            f"consecutive_successes={stats['consecutive_successes']}"
        )
    
    def _on_node_recovered(self, node_id: int) -> None:
        """
        Called when a node is detected as recovered.
        
        Args:
            node_id: ID of the recovered node
        """
        # Log detailed statistics
        stats = self.failure_state.get_statistics(node_id)
        self.logger.info(
            f"Node {node_id} recovered - "
            f"consecutive_failures={stats['consecutive_failures']}, "
            f"consecutive_successes={stats['consecutive_successes']}"
        )
    
    def __str__(self) -> str:
        """String representation of the heartbeat detector."""
        return (f"HeartbeatDetector("
                f"enabled={self._detection_enabled}, "
                f"failed_nodes={len(self.get_failed_nodes())}, "
                f"active_nodes={len(self.get_active_nodes())})") 

    def get_detection_metrics(self) -> Dict[str, Any]:
        """
        Get detailed metrics about failure detection performance.
        
        Returns:
            Dictionary with detailed metrics
        """
        # Calculate success rate
        success_rate = 0.0
        if self._metrics['total_responses_received'] > 0:
            success_rate = (self._metrics['total_successful_responses'] / self._metrics['total_responses_received']) * 100
        
        # Calculate failure rate
        failure_rate = 0.0
        if self._metrics['total_responses_received'] > 0:
            failure_rate = (self._metrics['total_failed_responses'] / self._metrics['total_responses_received']) * 100
        
        # Get current time for relative timestamps
        if self._get_current_time_callback:
            current_time = self._get_current_time_callback()
        else:
            raise RuntimeError("No simulation time callback available")
        
        # Process node histories
        node_histories = {}
        for node_id in self.failure_state.get_all_nodes():
            node_histories[node_id] = {
                'recent_response_times': self._metrics['node_response_times'].get(node_id, [])[-5:],  # Last 5
                'failure_count': len(self._metrics['node_failure_history'].get(node_id, [])),
                'recovery_count': len(self._metrics['node_recovery_history'].get(node_id, [])),
                'last_failure': self._metrics['node_failure_history'].get(node_id, [])[-1] if self._metrics['node_failure_history'].get(node_id) else None,
                'last_recovery': self._metrics['node_recovery_history'].get(node_id, [])[-1] if self._metrics['node_recovery_history'].get(node_id) else None
            }
            
            # Convert timestamps to relative times
            if node_histories[node_id]['last_failure']:
                node_histories[node_id]['time_since_last_failure'] = (current_time - node_histories[node_id]['last_failure']) * 1000
            if node_histories[node_id]['last_recovery']:
                node_histories[node_id]['time_since_last_recovery'] = (current_time - node_histories[node_id]['last_recovery']) * 1000
        
        return {
            'performance': {
                'total_heartbeats_sent': self._metrics['total_heartbeats_sent'],
                'total_responses_received': self._metrics['total_responses_received'],
                'total_successful_responses': self._metrics['total_successful_responses'],
                'total_failed_responses': self._metrics['total_failed_responses'],
                'success_rate_percent': success_rate,
                'failure_rate_percent': failure_rate,
                'average_response_time_ms': self._metrics['average_response_time_ms'],
                'detection_latency_ms': self._metrics['detection_latency_ms']
            },
            'detection': {
                'total_failures_detected': self._metrics['total_failures_detected'],
                'total_recoveries_detected': self._metrics['total_recoveries_detected'],
                'heartbeat_counter': self._heartbeat_counter,
                'detection_interval': self.config.detection_interval
            },
            'node_histories': node_histories,
            'configuration': {
                'failure_threshold': self.config.failure_threshold,
                'recovery_threshold': self.config.recovery_threshold,
                'timeout_ms': self.config.get_timeout_ms(),
                'detection_interval': self.config.detection_interval
            }
        } 