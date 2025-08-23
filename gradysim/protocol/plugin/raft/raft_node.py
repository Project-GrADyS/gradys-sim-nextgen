"""
Individual Raft Node Implementation

Implements the core Raft node functionality including:
- State management (Follower, Candidate, Leader)
- Election handling
- Heartbeat management
- Consensus value tracking
- Message processing

This module provides the internal Raft node implementation that handles
all the low-level Raft protocol operations.
"""

import logging
import random
import time
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

from .raft_state import RaftState
from .raft_message import (
    RequestVote, RequestVoteResponse,
    AppendEntries, AppendEntriesResponse,
    DiscoveryHeartbeat, DiscoveryHeartbeatResponse,
    MessageFactory
)
from .raft_config import RaftConfig
from .failure_detection import HeartbeatDetector


class RaftNode:
    """
    Individual Raft node implementation.
    
    Handles all Raft protocol operations including state transitions,
    election management, heartbeat processing, and consensus value tracking.
    
    This class is designed to be used internally by RaftConsensus and
    should not be instantiated directly by users.
    """
    
    def __init__(self, node_id: int, config: RaftConfig, callbacks=None):
        """
        Initialize Raft node.
        
        Args:
            node_id: Unique identifier for this node
            config: Raft configuration
            callbacks: Dictionary containing all required callbacks
            
        Raises:
            ValueError: If callbacks is not provided
            
        Example:
            # Simple usage with callbacks (recommended):
            node = RaftNode(node_id=1, config=config, callbacks=callbacks)
        """
        self.node_id = node_id
        self.config = config
        
        # Inicialize o logger logo no início
        self.logger = logging.getLogger(f"RaftNode-{node_id}")
        
        # Configure logging based on config
        if config._enable_logging:
            self.logger.setLevel(getattr(logging, config._log_level))
        else:
            self.logger.setLevel(logging.ERROR)  # Disable all logs except errors
        
        # Validate callbacks is provided
        if callbacks is None:
            raise ValueError("Callbacks must be provided. Use: RaftNode(node_id=node_id, config=config, callbacks=callbacks)")
        
        # Extract callbacks from dictionary
        self._send_message_callback = callbacks.get('send_message_callback')
        self._send_broadcast = callbacks.get('send_broadcast_callback')
        self._schedule_timer = callbacks.get('schedule_timer_callback')
        self._cancel_timer = callbacks.get('cancel_timer_callback')
        self._get_current_time = callbacks.get('get_current_time_callback')
        
        # Validate required callbacks
        self._validate_callbacks()
        
        # Raft state
        self.state = RaftState.FOLLOWER
        self.current_term = 0
        self.voted_for: Optional[int] = None
        
        # Cluster information
        self.cluster_id: Optional[int] = None
        
        # Election state
        self.election_timeout = 0
        self.votes_received: Set[int] = set()
        self.vote_requests_sent: Set[int] = set()
        
        # Election state tracking
        self.election_attempts = 0  # For future use if needed
        
        # Leader state
        self.leader_id: Optional[int] = None
        self.next_index: Dict[int, int] = defaultdict(lambda: 1)
        self.match_index: Dict[int, int] = defaultdict(lambda: 0)
        
        # Consensus state
        self.consensus_values: Dict[str, Any] = {}
        self.committed_values: Dict[str, Any] = {}
        self.current_term_number = 0
        
        # Timers
        self.active_timers: Set[str] = set()
        
        # Initialize consensus values
        for var_name, var_type in config.get_consensus_variables().items():
            self.consensus_values[var_name] = None
            self.committed_values[var_name] = None
        
        # Failure detection (always enabled)
        self._heartbeat_detector: Optional[HeartbeatDetector] = None
        self._initialize_failure_detection()
        
        # Node simulation control
        self._is_active: bool = True  # Each node controls its own active state
        self._known_nodes: List[int] = []
        
        # Active nodes tracking for majority calculation
        self._known_active_count: Optional[int] = None  # Count of active nodes from leader
        self._last_active_count_update: float = 0.0     # Timestamp of last update
        self._known_active_nodes_list: Optional[set] = None  # Complete list of active nodes from leader
        self._last_active_nodes_list_update: float = 0.0    # Timestamp of last list update
        
        # Discovery state for active nodes discovery before elections
        self._discovery_responses: Set[int] = set()     # Set of nodes that responded to discovery
        self._is_discovering: bool = False              # Whether currently in discovery mode
        self._discovery_timeout: Optional[str] = None   # Timer for discovery timeout
        self._discovered_active_count: Optional[int] = None  # Count discovered during election
        
    
    def _validate_callbacks(self) -> None:
        """Validate that all required callbacks are provided."""
        required_callbacks = [
            ('send_message_callback', self._send_message_callback),
            ('schedule_timer_callback', self._schedule_timer),
            ('cancel_timer_callback', self._cancel_timer)
        ]
        
        missing_callbacks = []
        for name, callback in required_callbacks:
            if callback is None:
                missing_callbacks.append(name)
        
        if missing_callbacks:
            raise ValueError(f"Missing required callbacks: {missing_callbacks}")
        
        # Optional callbacks
        if self._send_broadcast is None:
            self.logger.info("Broadcast callback not provided, will use individual messages")
        if self._get_current_time is None:
            self.logger.info("Get current time callback not provided, will use system time")
    
    def _initialize_failure_detection(self) -> None:
        """Initialize failure detection system."""
        failure_config = self.config.get_failure_config()
        
        # Get current time callback if available
        get_current_time_callback = None
        if hasattr(self, '_get_current_time') and self._get_current_time is not None:
            get_current_time_callback = self._get_current_time
        
        # Initialize with callbacks for failure and recovery notifications
        self._heartbeat_detector = HeartbeatDetector(
            config=failure_config,
            known_nodes=set(),  # Will be updated when known_nodes is set
            on_failure_callback=self.on_node_failure_detected,
            on_recovery_callback=self.on_node_recovery_detected,
            get_current_time_callback=get_current_time_callback
        )
        
        self.logger.info("Failure detection initialized")
    
    def start(self) -> None:
        """Start the Raft node and begin election timeout."""
        self.logger.info(f"Starting Raft node {self.node_id}")
        
        # Failure detection is automatically enabled when detector is created
        # No need to explicitly start it
        
        self._schedule_election_timeout()
    
    def stop(self) -> None:
        """Stop the Raft node and cancel all timers."""
        self.logger.info(f"Stopping Raft node {self.node_id}")
        
        # Failure detection is automatically managed
        # No need to explicitly stop it
        
        for timer in list(self.active_timers):
            self._cancel_timer(timer)
        self.active_timers.clear()
    
    def propose_value(self, variable_name: str, value: Any) -> bool:
        """
        Propose a new value for consensus.
        
        Args:
            variable_name: Name of the consensus variable
            value: Value to propose
            
        Returns:
            True if proposal was accepted, False otherwise
            
        Raises:
            ValueError: If variable is not configured or value type is invalid
        """
        if not self.config.has_consensus_variable(variable_name):
            raise ValueError(f"Consensus variable '{variable_name}' not configured")
        
        expected_type = self.config.get_consensus_variable_type(variable_name)
        if not isinstance(value, expected_type):
            raise ValueError(f"Value must be of type {expected_type.__name__}")
        
        if self.state != RaftState.LEADER:
            self.logger.warning(f"Node {self.node_id} is not leader, cannot propose value")
            return False
        
        # Check if this node is active before proposing values
        if not self._is_active:
            self.logger.warning(f"Leader {self.node_id} is inactive, cannot propose value")
            return False
        
        # Check if the value has actually changed to avoid unnecessary proposals
        current_committed_value = self.committed_values.get(variable_name)
        if current_committed_value == value:
            self.logger.debug(f"Value {value} for {variable_name} already committed, skipping proposal")
            return True  # Return True since it's already the desired state
        
        self.logger.info(f"Proposing value {value} for variable {variable_name}")
        self.consensus_values[variable_name] = value
        self.current_term_number += 1
        
        # Send append entries to all followers
        self._send_append_entries()
        return True
    
    def get_committed_value(self, variable_name: str) -> Optional[Any]:
        """
        Get the committed value for a consensus variable.
        
        Args:
            variable_name: Name of the consensus variable
            
        Returns:
            Committed value, or None if not available
        """
        return self.committed_values.get(variable_name)
    
    def get_all_committed_values(self) -> Dict[str, Any]:
        """
        Get all committed consensus values.
        
        Returns:
            Dictionary of all committed values
        """
        return self.committed_values.copy()
    
    def is_leader(self) -> bool:
        """Check if this node is the current leader."""
        return self.state == RaftState.LEADER
    
    def get_leader_id(self) -> Optional[int]:
        """Get the current leader ID."""
        return self.leader_id
    
    def get_current_term(self) -> int:
        """Get the current term."""
        return self.current_term
    
    def handle_message(self, message_str: str, sender_id: int) -> None:
        """
        Handle incoming message.
        
        Args:
            message_str: JSON string representation of the message
            sender_id: ID of the message sender
        """
        # Check if this node is active
        if not self._is_active:
            self.logger.debug(f"Node {self.node_id} is inactive, ignoring message from {sender_id}")
            return
        
        try:
            message = MessageFactory.create_from_json(message_str)
            self._process_message(message, sender_id)
        except Exception as e:
            self.logger.error(f"Error processing message from {sender_id}: {e}")
    
    def _send_message(self, message_str: str, target_id: int) -> None:
        """
        Send message to a specific node.
        
        Args:
            message_str: JSON string representation of the message
            target_id: ID of the target node
        """
        # Check if this node is active before sending messages
        if not self._is_active:
            self.logger.debug(f"Node {self.node_id} is inactive, not sending message to {target_id}")
            return
        
        if self._send_message_callback is not None:
            self._send_message_callback(message_str, target_id)
        else:
            self.logger.warning(f"No send_message callback available")
    
    def handle_timer(self, timer_name: str) -> None:
        """
        Handle timer expiration.
        
        Args:
            timer_name: Name of the expired timer
        """
        if timer_name not in self.active_timers:
            return
        
        self.active_timers.remove(timer_name)
        
        if timer_name == "election_timeout":
            self._handle_election_timeout()
        elif timer_name == "heartbeat":
            self._handle_heartbeat_timeout()
        elif timer_name == "discovery_timeout":
            self._handle_discovery_timeout()
        else:
            self.logger.warning(f"Unknown timer: {timer_name}")
    
    def _process_message(self, message: Any, sender_id: int) -> None:
        """Process a Raft message."""
        if hasattr(message, 'term') and message.term > self.current_term:
            self._step_down(message.term)
        
        if isinstance(message, RequestVote):
            self._handle_request_vote(message, sender_id)
        elif isinstance(message, RequestVoteResponse):
            self._handle_request_vote_response(message, sender_id)
        elif isinstance(message, AppendEntries):
            self._handle_append_entries(message, sender_id)
        elif isinstance(message, AppendEntriesResponse):
            self._handle_append_entries_response(message, sender_id)
        elif isinstance(message, DiscoveryHeartbeat):
            self._handle_discovery_heartbeat(message, sender_id)
        elif isinstance(message, DiscoveryHeartbeatResponse):
            self._handle_discovery_heartbeat_response(message, sender_id)
    
    def _handle_request_vote(self, message: RequestVote, sender_id: int) -> None:
        """Handle RequestVote message."""
        vote_granted = False
        
        if message.term > self.current_term:
            self._step_down(message.term)
        
        if message.term == self.current_term and (self.voted_for is None or self.voted_for == message.candidate_id):
            self.voted_for = message.candidate_id
            vote_granted = True
            self.logger.info(f"Voted for candidate {message.candidate_id}")
        
        # Only send response if sender is not self
        if sender_id != self.node_id:
            response = RequestVoteResponse(self.current_term, vote_granted, self.node_id)
            self._send_message(response.to_json(), sender_id)
    
    def _handle_request_vote_response(self, message: RequestVoteResponse, sender_id: int) -> None:
        """Handle RequestVoteResponse message."""
        if self.state != RaftState.CANDIDATE or message.term != self.current_term:
            return
        
        if message.vote_granted:
            self.votes_received.add(sender_id)
            self.logger.info(f"Received vote from {sender_id}, total votes: {len(self.votes_received)}")
            
            # Check if we have majority votes
            if self.has_majority_votes():
                self._become_leader()
    
    def _handle_append_entries(self, message: AppendEntries, sender_id: int) -> None:
        """Handle AppendEntries message."""
        success = True
        
        # Step down only if we receive a message with a higher term
        if message.term > self.current_term:
            self.leader_id = message.leader_id
            self._step_down(message.term)
        elif message.term == self.current_term:
            # If same term, just update leader_id if we're a follower
            if self.state == RaftState.FOLLOWER:
                self.leader_id = message.leader_id
        
        # Store active nodes information from leader for majority calculation
        if message.active_nodes_count is not None:
            self._known_active_count = message.active_nodes_count
            if self._get_current_time:
                self._last_active_count_update = self._get_current_time()
            else:
                raise RuntimeError("No simulation time callback available")
            self.logger.debug(f"Updated active nodes count from leader: {message.active_nodes_count}")
        
        # Store complete active nodes list from leader (if available)
        if message.active_nodes_list is not None:
            self._known_active_nodes_list = set(message.active_nodes_list)
            if self._get_current_time:
                self._last_active_nodes_list_update = self._get_current_time()
            else:
                raise RuntimeError("No simulation time callback available")
            self.logger.debug(f"Updated active nodes list from leader: {message.active_nodes_list}")
        
        # Update consensus values
        for var_name, value in message.consensus_values.items():
            if self.config.has_consensus_variable(var_name):
                self.consensus_values[var_name] = value
        
        # Update committed values if term number is higher and there are actual values
        if message.term_number > self.current_term_number and message.consensus_values:
            self.current_term_number = message.term_number
            self.committed_values.update(message.consensus_values)
            self.logger.info(f"Updated committed values: {self.committed_values}")
        elif message.term_number > self.current_term_number:
            # Just update term number for empty heartbeats, but don't log
            self.current_term_number = message.term_number
        
        # Only schedule election timeout if we're a follower (not leader or candidate)
        if self.state == RaftState.FOLLOWER:
            self._schedule_election_timeout()
        
        # Only send response if sender is not self
        if sender_id != self.node_id:
            response = AppendEntriesResponse(self.current_term, success, self.node_id, message.term_number)
            self._send_message(response.to_json(), sender_id)
    
    def _handle_append_entries_response(self, message: AppendEntriesResponse, sender_id: int) -> None:
        """Handle AppendEntriesResponse message."""
        if self.state != RaftState.LEADER or message.term != self.current_term:
            return
        
        if message.success:
            self.match_index[sender_id] = message.term_number
            self.next_index[sender_id] = message.term_number + 1
            
            # Check if we can commit based on active nodes majority
            self._check_and_commit_values()
        else:
            # Decrement next_index for retry
            if self.next_index[sender_id] > 1:
                self.next_index[sender_id] -= 1
        
        # Record heartbeat response for failure detection
        if self._heartbeat_detector is not None:
            self._heartbeat_detector.record_heartbeat_response(sender_id, message.success)
    
    def _handle_discovery_heartbeat(self, message: DiscoveryHeartbeat, sender_id: int) -> None:
        """Handle DiscoveryHeartbeat message."""
        # Always respond immediately to discovery heartbeats
        if sender_id != self.node_id:
            response = DiscoveryHeartbeatResponse(self.current_term, self.node_id)
            self._send_message(response.to_json(), sender_id)
            self.logger.debug(f"Responded to discovery heartbeat from {sender_id}")
    
    def _handle_discovery_heartbeat_response(self, message: DiscoveryHeartbeatResponse, sender_id: int) -> None:
        """Handle DiscoveryHeartbeatResponse message."""
        # Only process if we're in discovery mode
        if not self._is_discovering:
            return
        
        # Add to discovered nodes
        self._discovery_responses.add(sender_id)
        self.logger.debug(f"Received discovery response from {sender_id}, total: {len(self._discovery_responses)}")
    
    def _discover_active_nodes_before_election(self) -> int:
        """
        Discover active nodes before starting election.
        
        Returns:
            Number of active nodes discovered
        """
        # Initialize discovery state
        self._discovery_responses.clear()
        self._is_discovering = True
        
        # Calculate discovery timeout (use same randomized timeout as election)
        # This helps distribute discovery timing and reduce cluster border conflicts
        discovery_timeout = self.config.get_random_election_timeout() / 1000.0  # Convert to seconds
        
        self.logger.info(f"Starting discovery of active nodes with timeout {discovery_timeout:.3f}s")
        
        # Send discovery heartbeats to all known nodes
        message = DiscoveryHeartbeat(self.current_term, self.node_id)
        message_str = message.to_json()
        
        # Send to all known nodes except self
        for node_id in self._known_nodes:
            if node_id != self.node_id:
                self._send_message(message_str, node_id)
        
        # Schedule discovery timeout  
        self._discovery_timeout = "discovery_timeout"
        self._schedule_timer(self._discovery_timeout, discovery_timeout)
        self.active_timers.add(self._discovery_timeout)
        
        # Wait for responses (this will be handled by the timeout)
        # For now, return a placeholder - the actual count will be set when timeout occurs
        return 0
    
    def _handle_discovery_timeout(self) -> None:
        """Handle discovery timeout and start election with discovered count."""
        if not self._is_discovering:
            return
        
        # Calculate discovered active count (including self)
        discovered_count = len(self._discovery_responses) + 1  # +1 for self
        self._discovered_active_count = discovered_count
        
        self.logger.info(f"Discovery completed: {discovered_count} active nodes found")
        
        # Clear discovery state
        self._discovery_responses.clear()
        self._is_discovering = False
        self._discovery_timeout = None
        
        # Now start the election with the discovered count
        self._start_election_with_discovered_count()
    
    def _start_election_with_discovered_count(self) -> None:
        """Start leader election with discovered active count."""
        # Check if this node is active before starting election
        if not self._is_active:
            self.logger.debug(f"Node {self.node_id} is inactive, not starting election")
            return
        
        self.current_term += 1
        self.state = RaftState.CANDIDATE
        self.voted_for = self.node_id
        self.votes_received = {self.node_id}  # Vote for self
        self.leader_id = None
        
        self.logger.info(f"Starting election for term {self.current_term} with {self._discovered_active_count} active nodes")
        
        # Send vote requests to all other nodes
        self._send_vote_requests()
        
        # Schedule election timeout
        self._schedule_election_timeout()
    
    def _is_active_count_fresh(self) -> bool:
        """
        Check if active count information is still fresh.
        
        Returns:
            True if active count information is recent enough to be considered valid
        """
        if not hasattr(self, '_known_active_count') or self._known_active_count is None:
            return False
        
        if self._get_current_time:
            current_time = self._get_current_time()
        else:
            raise RuntimeError("No simulation time callback available")
        age = current_time - self._last_active_count_update
        
        # Consider valid for 5x the heartbeat interval
        max_age = self.config._heartbeat_interval * 5 / 1000.0  # Convert to seconds
        return age < max_age
    
    def _is_active_nodes_list_fresh(self) -> bool:
        """
        Check if the active nodes list information from leader is fresh enough to be used.
        
        Returns:
            True if active nodes list is fresh enough to use, False otherwise
        """
        if not hasattr(self, '_known_active_nodes_list') or self._known_active_nodes_list is None:
            return False
        
        if self._get_current_time:
            current_time = self._get_current_time()
        else:
            raise RuntimeError("No simulation time callback available")
        age = current_time - self._last_active_nodes_list_update
        
        # Consider valid for 5x the heartbeat interval (same as count)
        max_age = self.config._heartbeat_interval * 5 / 1000.0  # Convert to seconds
        return age < max_age
    

    
    def _clear_stale_active_count(self) -> None:
        """
        Clear active count information.
        
        This method should be called when the information becomes too old
        or when we become a leader (since we'll calculate our own count).
        """
        self._known_active_count = None
        self._last_active_count_update = 0.0
        self.logger.debug("Cleared active count information")
    
    def _get_active_nodes_for_majority(self) -> Set[int]:
        """
        Get the set of active nodes for majority calculations.
        
        Returns:
            Set of active node IDs, or all known nodes if failure detection is disabled
        """
        # Use failure detection if available
        if self._heartbeat_detector is not None:
            active_nodes = self._heartbeat_detector.get_active_nodes()
            # Always include self in active nodes if we're active
            if self._is_active:
                active_nodes.add(self.node_id)
            
            # If we have active nodes (including self), return them
            if active_nodes:
                return active_nodes
            
            # If no active nodes detected but we're active, at least include self
            if self._is_active:
                return {self.node_id}
        
        # Fallback to known nodes if no failure detection
        if hasattr(self, '_known_nodes') and self._known_nodes:
            return self._known_nodes
        else:
            # Fallback to just self if no known nodes
            return {self.node_id}
    
    def _check_and_commit_values(self) -> None:
        """
        Check if values can be committed based on active nodes majority.
        """
        if not self.consensus_values:
            return
        
        # Check if majority of active nodes have confirmed
        if self.has_majority_confirmation():
            # Check if values are already committed to avoid duplicate logs
            values_changed = False
            for var_name, value in self.consensus_values.items():
                if var_name not in self.committed_values or self.committed_values[var_name] != value:
                    values_changed = True
                    break
            
            if values_changed:
                self.committed_values.update(self.consensus_values)
                self.logger.info(f"✅ New values committed: {self.consensus_values}")
                # Clear consensus values after they are committed to avoid duplicate logs
                self.consensus_values.clear()
    
    def _handle_election_timeout(self) -> None:
        """Handle election timeout."""
        # In classic mode, skip discovery and start election directly
        if self.config.is_classic_mode():
            self.logger.info(f"Election timeout, starting election directly (classic mode)")
            self._start_election()
        else:
            # Fault-tolerant mode: use discovery if needed
            if not self._is_active_count_fresh():
                self.logger.info(f"Election timeout, starting discovery before election")
                self._discover_active_nodes_before_election()
            else:
                self.logger.info(f"Election timeout, starting election directly (active count is fresh)")
                self._start_election()
    
    def _handle_heartbeat_timeout(self) -> None:
        """Handle heartbeat timeout."""
        if self.state == RaftState.LEADER:
            self._send_append_entries()
            self._schedule_heartbeat_timer()
    
    def _start_election(self) -> None:
        """Start leader election."""
        # Check if this node is active before starting election
        if not self._is_active:
            self.logger.debug(f"Node {self.node_id} is inactive, not starting election")
            return
        
        self.current_term += 1
        self.state = RaftState.CANDIDATE
        self.voted_for = self.node_id
        self.votes_received = {self.node_id}  # Vote for self
        self.leader_id = None
        
        self.logger.info(f"Starting election for term {self.current_term}")
        
        # Send vote requests to all other nodes
        self._send_vote_requests()
        
        # Schedule election timeout
        self._schedule_election_timeout()
    
    def _send_vote_requests(self) -> None:
        """Send vote requests to all other nodes."""
        # Check if this node is active before sending vote requests
        if not self._is_active:
            self.logger.debug(f"Node {self.node_id} is inactive, not sending vote requests")
            return
        
        message = RequestVote(self.current_term, self.node_id)
        message_str = message.to_json()
        
        # Send to ALL known nodes (not just active ones) to enable failure detection
        # The failure detection will determine which nodes are actually active
        if hasattr(self, '_known_nodes') and self._known_nodes:
            target_nodes = self._known_nodes
        else:
            # Fallback to active nodes if no known nodes
            target_nodes = self._get_active_nodes_for_majority()
        
        # Use broadcast if available, otherwise use individual messages
        if self._send_broadcast is not None:
            self._send_broadcast(message_str)
            self.logger.info(f"Sent vote request broadcast for term {self.current_term}")
        else:
            # Send individual messages to all nodes except self
            for node_id in target_nodes:
                if node_id != self.node_id:
                    self._send_message(message_str, node_id)
                    self.logger.info(f"Sent vote request to node {node_id}")
            self.logger.info(f"Sent vote requests for term {self.current_term} to all nodes")
    
    def _send_append_entries(self) -> None:
        """Send append entries to all followers."""
        # Check if this node is active before sending append entries
        if not self._is_active:
            self.logger.debug(f"Node {self.node_id} is inactive, not sending append entries")
            return
        
        # Calculate active nodes for sharing with followers
        # IMPORTANT: Always include the leader in the count, even if it might become inactive later
        # This ensures that if the leader becomes inactive, the remaining nodes can still form a majority
        active_nodes = self._get_active_nodes_for_majority()
        active_count = len(active_nodes)
        
        # Ensure the leader is always counted as active for majority calculations
        # This prevents the scenario where the leader becomes inactive and the remaining nodes
        # can't form a majority because the leader didn't include itself in the count
        if self.node_id not in active_nodes:
            active_nodes = active_nodes.copy()  # Don't modify the original set
            active_nodes.add(self.node_id)
            active_count += 1
            self.logger.debug(f"Leader {self.node_id} not in active nodes, adjusting count from {len(active_nodes)-1} to {active_count}")
        
        # Convert active_nodes set to list for message transmission
        active_nodes_list = sorted(list(active_nodes))
        
        message = AppendEntries(
            self.current_term,
            self.node_id,
            self.consensus_values,
            self.current_term_number,
            active_count,        # Include active nodes count (for backward compatibility)
            active_nodes_list    # Include complete list of active nodes
        )
        message_str = message.to_json()
        
        # Send to ALL known nodes (not just active ones) to enable failure detection
        # The failure detection will determine which nodes are actually active
        if hasattr(self, '_known_nodes') and self._known_nodes:
            target_nodes = self._known_nodes
        else:
            # Fallback to active nodes if no known nodes
            target_nodes = self._get_active_nodes_for_majority()
        
        # Use broadcast if available, otherwise use individual messages
        if self._send_broadcast is not None:
            self._send_broadcast(message_str)
            # Only log if there are consensus values to propagate (not just heartbeats)
            if self.consensus_values:
                self.logger.info(f"Sent append entries broadcast for term {self.current_term} with {active_count} active nodes")
        else:
            # Send individual messages to all nodes except self
            for follower_id in target_nodes:
                if follower_id != self.node_id:
                    self._send_message(message_str, follower_id)
            
            # Only log if there are consensus values to propagate (not just heartbeats)
            if self.consensus_values:
                self.logger.info(f"Sent append entries for term {self.current_term} to all nodes with {active_count} active nodes")
        
        # Record heartbeat sent for failure detection
        if self._heartbeat_detector is not None:
            for follower_id in target_nodes:
                if follower_id != self.node_id:
                    self._heartbeat_detector.record_heartbeat_sent(follower_id)
            
            # Notify detector that heartbeats were sent
            self._heartbeat_detector.on_heartbeat_sent()
    
    def _become_leader(self) -> None:
        """Become leader."""
        self.state = RaftState.LEADER
        self.leader_id = self.node_id
        self.logger.info(f"Became leader for term {self.current_term}")
        
        # Clear stale active count information since we'll calculate our own
        self._clear_stale_active_count()
        
        # Clear discovered active count since we're now the leader
        self._discovered_active_count = None
        
        # Initialize leader state
        self.next_index.clear()
        self.match_index.clear()
        
        # Cancel election timeout since we're now the leader
        if "election_timeout" in self.active_timers:
            self._cancel_timer("election_timeout")
            self.active_timers.remove("election_timeout")
        
        # Cancel discovery timeout since we're now the leader
        if "discovery_timeout" in self.active_timers:
            self._cancel_timer("discovery_timeout")
            self.active_timers.remove("discovery_timeout")
            self._discovery_timeout = None
            self._is_discovering = False
        
        # Send initial heartbeat
        self._send_append_entries()
        self._schedule_heartbeat_timer()
    
    def _step_down(self, new_term: int) -> None:
        """Step down to follower state."""
        self.current_term = new_term
        self.state = RaftState.FOLLOWER
        self.voted_for = None
        self.leader_id = None
        self.votes_received.clear()
        
        # Reset election state when becoming follower
        self.election_attempts = 0
        
        # Clear discovered active count since we're now a follower
        self._discovered_active_count = None
        
        # Cancel leader timers
        if "heartbeat" in self.active_timers:
            self._cancel_timer("heartbeat")
            self.active_timers.remove("heartbeat")
        
        # Cancel discovery timeout if active
        if "discovery_timeout" in self.active_timers:
            self._cancel_timer("discovery_timeout")
            self.active_timers.remove("discovery_timeout")
            self._discovery_timeout = None
            self._is_discovering = False
        
        # Schedule election timeout when becoming follower
        self._schedule_election_timeout()
        
        self.logger.info(f"Stepped down to follower for term {new_term}")
    
    def _schedule_election_timeout(self) -> None:
        """Schedule election timeout with randomized interval (Raft standard)."""
        if "election_timeout" in self.active_timers:
            self._cancel_timer("election_timeout")
            self.active_timers.remove("election_timeout")
        
        # Use randomized timeout (Raft standard behavior)
        # No exponential backoff - each timeout is independent
        timeout = self.config.get_random_election_timeout()
        
        # Reset election attempts when scheduling timeout
        # This ensures clean state for each election attempt
        self.election_attempts = 0
        
        self.logger.debug(f"Election timeout scheduled: {timeout}ms")
        
        self._schedule_timer("election_timeout", timeout)
        self.active_timers.add("election_timeout")
    
    def _schedule_heartbeat_timer(self) -> None:
        """Schedule heartbeat timer."""
        if "heartbeat" in self.active_timers:
            self._cancel_timer("heartbeat")
            self.active_timers.remove("heartbeat")
        
        self._schedule_timer("heartbeat", self.config._heartbeat_interval)
        self.active_timers.add("heartbeat")
    
    def set_known_nodes(self, node_ids: List[int]) -> None:
        """
        Set the list of known node IDs.
        
        Args:
            node_ids: List of all node IDs in the cluster
        """
        self._known_nodes = set(node_ids)
        self.vote_requests_sent = self._known_nodes.copy()
        
        # Update failure detection with known nodes (excluding self)
        if self._heartbeat_detector is not None:
            # Add only other nodes to the detector (not self)
            other_nodes = [node_id for node_id in node_ids if node_id != self.node_id]
            for node_id in other_nodes:
                self._heartbeat_detector.add_node(node_id)
            self.logger.info(f"Updated failure detection with {len(other_nodes)} other nodes: {other_nodes}")
    
    def get_state_info(self) -> Dict[str, Any]:
        """
        Get current state information for debugging.
        
        Returns:
            Dictionary with current state information
        """
        info = {
            "node_id": self.node_id,
            "cluster_id": self.cluster_id,
            "state": self.state.name,
            "current_term": self.current_term,
            "voted_for": self.voted_for,
            "leader_id": self.leader_id,
            "consensus_values": self.consensus_values.copy(),
            "committed_values": self.committed_values.copy(),
            "active_timers": list(self.active_timers)
        }
        
        # Add failure detection info if enabled
        if self._heartbeat_detector is not None:
            info["failure_detection"] = self._heartbeat_detector.get_detection_summary()
        
        return info
    
    def get_failed_nodes(self) -> Set[int]:
        """
        Get the set of currently failed nodes.
        
        Returns:
            Set of failed node IDs, empty if failure detection is disabled
        """
        if self._heartbeat_detector is not None:
            return self._heartbeat_detector.get_failed_nodes()
        return set()
    
    def get_simulation_active_nodes(self) -> Set[int]:
        """
        Get the set of nodes that are active in simulation.
        This is based on manual control (active/inactive state).
        
        Returns:
            Set of simulation active node IDs
        """
        active_nodes = set()
        if hasattr(self, '_known_nodes') and self._known_nodes:
            for node_id in self._known_nodes:
                if self.is_simulation_active(node_id):
                    active_nodes.add(node_id)
        else:
            # If no known nodes, at least include self if active
            if self._is_active:
                active_nodes.add(self.node_id)
        return active_nodes
    
    def get_communication_failed_nodes(self) -> Set[int]:
        """
        Get the set of nodes that have communication failures.
        This is based on heartbeat detection.
        
        Returns:
            Set of communication failed node IDs
        """
        if self._heartbeat_detector is not None:
            return self._heartbeat_detector.get_failed_nodes()
        return set()
    
    def get_communication_active_nodes(self) -> Set[int]:
        """
        Get the set of nodes that have active communication.
        This is based on heartbeat detection.
        
        Returns:
            Set of communication active node IDs
        """
        if self._heartbeat_detector is not None:
            active_nodes = self._heartbeat_detector.get_active_nodes()
            # Always include self if we're active in simulation
            if self._is_active:
                active_nodes.add(self.node_id)
            return active_nodes
        return set()
    
    def get_active_nodes(self) -> Set[int]:
        """
        Get the set of currently active nodes.
        DEPRECATED: Use get_simulation_active_nodes() or get_communication_active_nodes() instead.
        
        Returns:
            Set of active node IDs, including self if active, empty if failure detection is disabled
        """
        if self._heartbeat_detector is not None:
            active_nodes = self._heartbeat_detector.get_active_nodes()
            # Always include self in active nodes if we're active
            if self._is_active:
                active_nodes.add(self.node_id)
            return active_nodes
        return set()
    
    def get_active_nodes_info(self) -> Dict[str, Any]:
        """
        Get detailed information about active nodes from this node's perspective.
        This method can be called on any node (leader, candidate, or follower) in any mode.
        
        Behavior differs by Raft mode:
        
        **FAULT_TOLERANT mode:**
        - Leader: Uses direct heartbeat detection (complete active nodes list)
        - Follower/Candidate: Uses active count shared by leader + local knowledge
        
        **CLASSIC mode:**
        - All known nodes are considered active (no failure detection)
        - Returns complete information based on known node list
        
        Returns:
            Dictionary containing:
            - 'active_nodes': List of active node IDs (sorted)
                * FAULT_TOLERANT Leader: Complete list from heartbeat detection
                * FAULT_TOLERANT Follower: Limited list (self + leader + any locally detected)
                * CLASSIC mode: All known nodes
            - 'active_count': Number of active nodes
                * FAULT_TOLERANT Leader: Count from heartbeat detection
                * FAULT_TOLERANT Follower: Count received from leader (if fresh)
                * CLASSIC mode: Total known nodes
            - 'total_known': Total number of known nodes
            - 'majority_threshold': Current majority threshold
            - 'has_majority': Whether cluster has majority
            - 'detection_method': How active nodes were determined
                * 'leader_heartbeat_detection': Leader using heartbeat detector
                * 'leader_shared_complete_list': Follower using complete list from leader
                * 'leader_shared_count_only': Follower using count from leader (limited IDs)
                * 'follower_local_detection': Follower using local detection (fallback)
                * 'classic_mode_all_active': Classic mode (all nodes considered active)
            - 'last_update': Timestamp of last update (if available)
            - 'node_role': Role of this node ('leader', 'candidate', 'follower')
            - 'is_leader': Whether this node is the leader
            - 'leader_id': ID of the current leader (if known)
            - 'current_node_id': ID of this node
            - 'current_term': Current Raft term
            - 'raft_mode': Current Raft operation mode
            - 'failed_nodes': List of failed node IDs (empty in CLASSIC mode)
            - 'failed_count': Number of failed nodes (0 in CLASSIC mode)
            - 'detection_summary': Detailed detection info (if available)
        """
        # Handle different modes
        if self.config.is_classic_mode():
            # Classic mode: All known nodes are considered active
            return self._get_classic_mode_active_info()
        else:
            # Fault-tolerant mode: Use actual failure detection
            return self._get_fault_tolerant_active_info()
    
    def _get_classic_mode_active_info(self) -> Dict[str, Any]:
        """Get active nodes info for Classic mode - all known nodes are considered active."""
        # In classic mode, all known nodes are considered active
        all_known_nodes = set(self._known_nodes) if self._known_nodes else set()
        
        # Always include self
        all_known_nodes.add(self.node_id)
        
        # Include leader if known
        if self.leader_id is not None:
            all_known_nodes.add(self.leader_id)
            
        active_nodes = sorted(list(all_known_nodes))
        active_count = len(active_nodes)
        total_known = active_count
        majority_threshold = (total_known // 2) + 1
        has_majority = active_count >= majority_threshold
        
        # Determine role
        if self.is_leader():
            node_role = "leader"
        elif self.state == RaftState.CANDIDATE:
            node_role = "candidate"
        else:
            node_role = "follower"
            
        return {
            'active_nodes': active_nodes,
            'active_count': active_count,
            'total_known': total_known,
            'majority_threshold': majority_threshold,
            'has_majority': has_majority,
            'detection_method': 'classic_mode_all_active',
            'last_update': self._get_current_time() if self._get_current_time else None,
            'node_role': node_role,
            'is_leader': self.is_leader(),
            'leader_id': self.leader_id,
            'current_node_id': self.node_id,
            'current_term': self.current_term,
            'raft_mode': self.config.get_raft_mode().value,
            'failed_nodes': [],  # No failure detection in classic mode
            'failed_count': 0,
            'detection_summary': "Classic mode: All known nodes considered active (no failure detection)"
        }
    
    def _get_fault_tolerant_active_info(self) -> Dict[str, Any]:
        """Get active nodes info for Fault Tolerant mode - uses actual failure detection."""
        # Fault-tolerant mode: Use different detection methods based on node role
        if self.is_leader():
            # Leader: Use direct heartbeat detection (has complete information)
            if self._heartbeat_detector is not None:
                active_nodes = self._heartbeat_detector.get_active_nodes().copy()
                detection_method = "leader_heartbeat_detection"
                last_update = self._get_current_time() if self._get_current_time else None
            else:
                active_nodes = set()
                detection_method = "leader_no_detection_available"
                last_update = None
            
            # Always include self if we're active
            if self._is_active:
                active_nodes.add(self.node_id)
        
        else:
            # Follower/Candidate: Use information received from leader
            active_nodes = set()
            
            if self._is_active_nodes_list_fresh() and self._known_active_nodes_list is not None:
                # We have fresh complete list from leader - BEST CASE
                active_nodes = self._known_active_nodes_list.copy()
                detection_method = "leader_shared_complete_list"
                last_update = self._last_active_nodes_list_update
                
            elif self._is_active_count_fresh() and self._known_active_count is not None:
                # We have fresh count from leader but no complete list - FALLBACK
                detection_method = "leader_shared_count_only"
                last_update = self._last_active_count_update
                
                # We know the count but not all specific node IDs
                # For followers, we can only reliably know about ourselves and the leader
                if self._is_active:
                    active_nodes.add(self.node_id)
                if self.leader_id is not None:
                    active_nodes.add(self.leader_id)
                
                # Note: active_count will be overridden below with the actual count from leader
                
            else:
                # No fresh information from leader, use local detection (limited) - WORST CASE
                if self._heartbeat_detector is not None:
                    active_nodes = self._heartbeat_detector.get_active_nodes().copy()
                    detection_method = "follower_local_detection"
                    last_update = self._get_current_time() if self._get_current_time else None
                else:
                    detection_method = "follower_no_detection_available"
                    last_update = None
                
                # Always include self if we're active
                if self._is_active:
                    active_nodes.add(self.node_id)
        
        # Calculate majority information (fault-tolerant mode uses active node count)
        if not self.is_leader() and self._is_active_count_fresh() and self._known_active_count is not None:
            # For followers: Use the active count provided by the leader
            active_count = self._known_active_count
            majority_threshold = (active_count // 2) + 1
            has_majority = active_count >= majority_threshold
        else:
            # For leaders or when no fresh leader info: Use local detection
            active_count = len(active_nodes)
            majority_threshold = (active_count // 2) + 1
            has_majority = active_count >= majority_threshold
        
        total_known = len(self._known_nodes) if self._known_nodes else 1
        
        # Determine node role
        if self.state.name == "LEADER":
            node_role = "leader"
        elif self.state.name == "CANDIDATE":
            node_role = "candidate"
        else:
            node_role = "follower"
        
        # Prepare result
        result = {
            'active_nodes': sorted(list(active_nodes)),
            'active_count': active_count,
            'total_known': total_known,
            'majority_threshold': majority_threshold,
            'has_majority': has_majority,
            'detection_method': detection_method,
            'last_update': last_update,
            'node_role': node_role,
            'is_leader': self.is_leader(),
            'leader_id': self.leader_id,
            'current_node_id': self.node_id,
            'current_term': self.current_term,
            'raft_mode': self.config.get_raft_mode().value
        }
        
        # Add failure detection information (always available in fault-tolerant mode)
        if self._heartbeat_detector is not None:
            failed_nodes = self._heartbeat_detector.get_failed_nodes()
            result['failed_nodes'] = sorted(list(failed_nodes))
            result['failed_count'] = len(failed_nodes)
            
            # Add detection summary if available
            try:
                detection_summary = self._heartbeat_detector.get_detection_summary()
                result['detection_summary'] = detection_summary
            except:
                pass  # Detection summary might not be available
        else:
            result['failed_nodes'] = []
            result['failed_count'] = 0
        
        self.logger.debug(f"Active nodes info from node {self.node_id} ({node_role}): {result}")
        return result
    
    def has_quorum(self) -> bool:
        """
        Check if the system has enough active nodes to form a quorum.
        
        Returns:
            True if there are enough active nodes to operate, False otherwise
        """
        active_nodes = self._get_active_nodes_for_majority()
        # Need at least 2 nodes for quorum (minimum for majority)
        return len(active_nodes) >= 2
    
    def has_majority_votes(self) -> bool:
        """
        Check if we have majority votes.
        
        In classic mode: Always uses total known nodes for majority calculation
        In fault-tolerant mode: Uses discovered active count or known active nodes count
        
        Returns:
            True if we have majority votes
        """
        # Classic mode: Always use total known nodes (standard Raft behavior)
        if self.config.is_classic_mode():
            majority_threshold = (len(self._known_nodes) // 2) + 1
            self.logger.debug(f"Using total known nodes ({len(self._known_nodes)}) for majority calculation (classic mode): threshold={majority_threshold}, votes={len(self.votes_received)}")
            return len(self.votes_received) >= majority_threshold
        
        # Fault-tolerant mode: Use dynamic active node count
        # Use discovered active count if available (during elections)
        if self._discovered_active_count is not None:
            majority_threshold = (self._discovered_active_count // 2) + 1
            self.logger.debug(f"Using discovered active count ({self._discovered_active_count}) for majority calculation: threshold={majority_threshold}, votes={len(self.votes_received)}")
            return len(self.votes_received) >= majority_threshold
        
        # Use known active count if available and fresh
        if self._is_active_count_fresh():
            # If the known active count is very low (1 or 2), it might indicate that
            # the previous leader became inactive and didn't include itself in the count
            # In this case, we should use the current active nodes instead
            if self._known_active_count <= 2:
                current_active_nodes = self._get_active_nodes_for_majority()
                current_active_count = len(current_active_nodes)
                # Always include self in the count for majority calculation
                if self.node_id not in current_active_nodes:
                    current_active_count += 1
                
                majority_threshold = (current_active_count // 2) + 1
                self.logger.debug(f"Previous leader count too low ({self._known_active_count}), using current active count ({current_active_count}) for majority calculation: threshold={majority_threshold}, votes={len(self.votes_received)}")
                return len(self.votes_received) >= majority_threshold
            else:
                majority_threshold = (self._known_active_count // 2) + 1
                self.logger.debug(f"Using known active count ({self._known_active_count}) for majority calculation: threshold={majority_threshold}, votes={len(self.votes_received)}")
                return len(self.votes_received) >= majority_threshold
        else:
            # Fallback to total known nodes
            majority_threshold = (len(self._known_nodes) // 2) + 1
            self.logger.debug(f"Using total known nodes ({len(self._known_nodes)}) for majority calculation: threshold={majority_threshold}, votes={len(self.votes_received)}")
            return len(self.votes_received) >= majority_threshold
    
    def has_majority_confirmation(self) -> bool:
        """
        Check if majority of active nodes have confirmed current values.
        
        In classic mode: Uses total known nodes for majority calculation
        In fault-tolerant mode: Uses active nodes for majority calculation
        
        Returns:
            True if majority of active nodes have confirmed, False otherwise
        """
        # Classic mode: Use total known nodes (standard Raft behavior)
        if self.config.is_classic_mode():
            nodes_for_majority = self._known_nodes
            majority_threshold = (len(nodes_for_majority) // 2) + 1
        else:
            # Fault-tolerant mode: Use active nodes
            nodes_for_majority = self._get_active_nodes_for_majority()
            majority_threshold = (len(nodes_for_majority) // 2) + 1
        
        # Count confirmed nodes (including self)
        confirmed_nodes = 1  # Leader always confirms
        for node_id in nodes_for_majority:
            if node_id != self.node_id and node_id in self.match_index:
                if self.match_index[node_id] >= self.current_term_number:
                    confirmed_nodes += 1
        
        return confirmed_nodes >= majority_threshold
    

    
    def get_majority_info(self) -> Dict[str, Any]:
        """
        Get detailed information about majority status.
        
        Returns:
            Dictionary with majority information
        """
        active_nodes = self._get_active_nodes_for_majority()
        total_active = len(active_nodes)
        # Use standard Raft majority: n // 2 + 1
        majority_threshold = (total_active // 2) + 1
        
        # Get information about known active count
        known_active_info = {
            "known_active_count": self._known_active_count,
            "is_fresh": self._is_active_count_fresh(),
            "last_update": self._last_active_count_update
        }
        
        return {
            "active_nodes": list(active_nodes),
            "total_active": total_active,
            "majority_threshold": majority_threshold,
            "has_majority": total_active >= majority_threshold,
            "votes_received": len(self.votes_received) if hasattr(self, 'votes_received') else 0,
            "confirmed_nodes": len([n for n in active_nodes if n in self.match_index and self.match_index[n] >= self.current_term_number]) if hasattr(self, 'match_index') else 0,
            "known_active_info": known_active_info
        }
    
    def on_node_failure_detected(self, failed_node_id: int) -> None:
        """
        Called when a node failure is detected.
        
        Args:
            failed_node_id: ID of the failed node
        """
        self.logger.info(f"Node failure detected: {failed_node_id}")
        
        # Recalculate majority and take action if needed
        if self.state == RaftState.LEADER:
            if not self.has_quorum():
                self.logger.warning("⚠️  Lost quorum due to node failure! Some operations may be affected")
            else:
                self.logger.info("✅ Still have quorum after node failure")
        
        # If we're a candidate, recalculate if we have enough votes
        elif self.state == RaftState.CANDIDATE:
            if self.has_majority_votes():
                self.logger.info("✅ Have majority votes after node failure, becoming leader")
                self._become_leader()
    
    def on_node_recovery_detected(self, recovered_node_id: int) -> None:
        """
        Called when a node recovery is detected.
        
        Args:
            recovered_node_id: ID of the recovered node
        """
        self.logger.info(f"Node recovery detected: {recovered_node_id}")
        
        # Recalculate majority
        if self.state == RaftState.LEADER:
            if self.has_quorum():
                self.logger.info("✅ Regained quorum after node recovery! Full operations restored")
                # Try to commit any pending values
                self._check_and_commit_values()
    
    def is_node_failed(self, node_id: int) -> bool:
        """
        Check if a specific node is currently failed.
        
        Args:
            node_id: ID of the node to check
            
        Returns:
            True if the node is failed, False otherwise
        """
        if self._heartbeat_detector is not None:
            return self._heartbeat_detector.is_node_failed(node_id)
        return False

    def is_simulation_active(self, node_id: int) -> bool:
        """
        Check if a specific node is currently active in simulation.
        This is the manual control state (active/inactive).
        
        Args:
            node_id: ID of the node to check
            
        Returns:
            True if the node is active in simulation, False otherwise
        """
        if node_id == self.node_id:
            # For this node, check the internal active state
            return self._is_active
        else:
            # For other nodes, we assume they are active in simulation
            # unless we have explicit information otherwise
            return True
    
    def is_communication_failed(self, node_id: int) -> bool:
        """
        Check if a specific node has communication failure.
        This is based on heartbeat detection.
        
        Args:
            node_id: ID of the node to check
            
        Returns:
            True if the node has communication failure, False otherwise
        """
        if self._heartbeat_detector is not None:
            return self._heartbeat_detector.is_node_failed(node_id)
        return False
    
    def get_is_active(self, node_id: int) -> bool:
        """
        Check if a specific node is currently active.
        DEPRECATED: Use is_simulation_active() or is_communication_failed() instead.
        
        Args:
            node_id: ID of the node to check
            
        Returns:
            True if the node is active, False otherwise
        """
        if node_id == self.node_id:
            # For this node, check the internal active state
            return self._is_active
        else:
            # For other nodes, check if they haven't failed
            return not self.is_node_failed(node_id)
    

    
    def set_simulation_active(self, node_id: int, active: bool) -> None:
        """
        Set this node's simulation active/inactive state.
        Only affects this node if node_id matches this node's ID.
        
        When inactive, the node cannot send or receive messages, simulating
        a network failure. Internal timers continue to run normally.
        
        Args:
            node_id: ID of the node to set state
            active: True to make node active in simulation, False to make it inactive
        """
        if not isinstance(active, bool):
            raise ValueError("Parameter 'active' must be a boolean")
            
        if node_id == self.node_id:
            previous_state = self._is_active
            self._is_active = active
            
            if active and not previous_state:
                self.logger.info(f"✅ Node {self.node_id} simulation activated (communication enabled)")
            elif not active and previous_state:
                self.logger.info(f"❌ Node {self.node_id} simulation deactivated (communication disabled)")
                
                # If this node is currently leader and becoming inactive, step down
                if self.state == RaftState.LEADER:
                    self.logger.warning(f"Leader {self.node_id} is becoming inactive, stepping down")
                    self._step_down(self.current_term + 1)
            else:
                self.logger.debug(f"Node {self.node_id} simulation state unchanged (already {'active' if active else 'inactive'})")
        else:
            self.logger.debug(f"Simulation command for node {node_id} ignored on node {self.node_id}")
    
    def set_is_active(self, node_id: int, active: bool) -> None:
        """
        Set this node's active/inactive state.
        DEPRECATED: Use set_simulation_active() instead.
        
        Args:
            node_id: ID of the node to set state
            active: True to make node active, False to make it inactive
        """
        self.set_simulation_active(node_id, active)

    def get_failure_detection_metrics(self) -> Dict[str, Any]:
        """
        Get detailed metrics about failure detection performance.
        
        Returns:
            Dictionary with detailed failure detection metrics, or empty dict if not available
        """
        if self._heartbeat_detector is not None:
            return self._heartbeat_detector.get_detection_metrics()
        return {}
    
    def set_cluster_id(self, cluster_id: Optional[int]) -> None:
        """
        Set the cluster ID for this node.
        
        Args:
            cluster_id: Cluster ID to assign to this node, or None to clear
        """
        self.cluster_id = cluster_id
        self.logger.info(f"Cluster ID set to: {cluster_id}")
    
    def get_cluster_id(self) -> Optional[int]:
        """
        Get the cluster ID for this node.
        
        Returns:
            Cluster ID, or None if not set
        """
        return self.cluster_id
    
    

    
 