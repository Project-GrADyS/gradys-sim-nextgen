"""
Raft Message Definitions

Defines all message types used in the Raft consensus algorithm:
- RequestVote: Sent by candidates during elections
- RequestVoteResponse: Response to vote requests
- AppendEntries: Heartbeat and log replication messages
- AppendEntriesResponse: Response to append entries

This module provides message classes with JSON serialization/deserialization
capabilities and a factory pattern for message creation.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union


class RaftMessage(ABC):
    """
    Abstract base class for all Raft messages.
    
    Provides common functionality for message serialization and deserialization.
    All Raft messages should inherit from this class.
    """
    
    @abstractmethod
    def to_json(self) -> str:
        """Convert message to JSON string."""
        pass
    
    @classmethod
    @abstractmethod
    def from_json(cls, json_str: str) -> 'RaftMessage':
        """Create message instance from JSON string."""
        pass


class RequestVote(RaftMessage):
    """
    RequestVote message sent by candidates during leader election.
    
    Attributes:
        term: Candidate's term
        candidate_id: ID of the candidate requesting vote
    """
    
    def __init__(self, term: int, candidate_id: int):
        """
        Initialize RequestVote message.
        
        Args:
            term: Current term of the candidate
            candidate_id: ID of the candidate requesting the vote
        """
        self.term = term
        self.candidate_id = candidate_id
    
    def to_json(self) -> str:
        """Convert RequestVote to JSON string."""
        return json.dumps({
            "type": "RequestVote",
            "term": self.term,
            "candidate_id": self.candidate_id,
            "sender_id": self.candidate_id  # Include sender_id for Gradysim
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'RequestVote':
        """Create RequestVote from JSON string."""
        data = json.loads(json_str)
        return cls(data["term"], data["candidate_id"])


class RequestVoteResponse(RaftMessage):
    """
    Response to RequestVote message.
    
    Attributes:
        term: Current term of the responding node
        vote_granted: Whether the vote was granted
        voter_id: ID of the node that voted
    """
    
    def __init__(self, term: int, vote_granted: bool, voter_id: int):
        """
        Initialize RequestVoteResponse message.
        
        Args:
            term: Current term of the responding node
            vote_granted: Whether the vote was granted
            voter_id: ID of the node that voted
        """
        self.term = term
        self.vote_granted = vote_granted
        self.voter_id = voter_id
    
    def to_json(self) -> str:
        """Convert RequestVoteResponse to JSON string."""
        return json.dumps({
            "type": "RequestVoteResponse",
            "term": self.term,
            "vote_granted": self.vote_granted,
            "voter_id": self.voter_id,
            "sender_id": self.voter_id  # Include sender_id for Gradysim
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'RequestVoteResponse':
        """Create RequestVoteResponse from JSON string."""
        data = json.loads(json_str)
        return cls(data["term"], data["vote_granted"], data["voter_id"])


class AppendEntries(RaftMessage):
    """
    AppendEntries message for heartbeats and consensus value replication.
    
    Attributes:
        term: Leader's term
        leader_id: ID of the leader
        consensus_values: Dictionary of consensus variable names and their values
        term_number: Term number for this consensus round
        active_nodes_count: Number of active nodes known by the leader (optional, for backward compatibility)
        active_nodes_list: List of active node IDs known by the leader (optional)
    """
    
    def __init__(self, term: int, leader_id: int, consensus_values: Dict[str, Any], term_number: int, 
                 active_nodes_count: Optional[int] = None, active_nodes_list: Optional[list] = None):
        """
        Initialize AppendEntries message.
        
        Args:
            term: Current term of the leader
            leader_id: ID of the leader
            consensus_values: Dictionary of consensus variable names and their values
            term_number: Term number for this consensus round
            active_nodes_count: Number of active nodes known by the leader (optional, for backward compatibility)
            active_nodes_list: List of active node IDs known by the leader (optional)
        """
        self.term = term
        self.leader_id = leader_id
        self.consensus_values = consensus_values
        self.term_number = term_number
        self.active_nodes_count = active_nodes_count
        self.active_nodes_list = active_nodes_list
    
    def to_json(self) -> str:
        """Convert AppendEntries to JSON string."""
        data = {
            "type": "AppendEntries",
            "term": self.term,
            "leader_id": self.leader_id,
            "consensus_values": self.consensus_values,
            "term_number": self.term_number,
            "sender_id": self.leader_id  # Include sender_id for Gradysim
        }
        
        # Include active_nodes_count only if it's not None (backward compatibility)
        if self.active_nodes_count is not None:
            data["active_nodes_count"] = self.active_nodes_count
            
        # Include active_nodes_list only if it's not None
        if self.active_nodes_list is not None:
            data["active_nodes_list"] = sorted(list(self.active_nodes_list))  # Ensure consistent ordering
        
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AppendEntries':
        """Create AppendEntries from JSON string."""
        data = json.loads(json_str)
        active_nodes_count = data.get("active_nodes_count")  # Will be None if not present
        active_nodes_list = data.get("active_nodes_list")    # Will be None if not present
        return cls(data["term"], data["leader_id"], data["consensus_values"], data["term_number"], 
                  active_nodes_count, active_nodes_list)


class AppendEntriesResponse(RaftMessage):
    """
    Response to AppendEntries message.
    
    Attributes:
        term: Current term of the responding node
        success: Whether the append was successful
        follower_id: ID of the follower responding
        term_number: Term number that was acknowledged
    """
    
    def __init__(self, term: int, success: bool, follower_id: int, term_number: int):
        """
        Initialize AppendEntriesResponse message.
        
        Args:
            term: Current term of the responding node
            success: Whether the append was successful
            follower_id: ID of the follower responding
            term_number: Term number that was acknowledged
        """
        self.term = term
        self.success = success
        self.follower_id = follower_id
        self.term_number = term_number
    
    def to_json(self) -> str:
        """Convert AppendEntriesResponse to JSON string."""
        return json.dumps({
            "type": "AppendEntriesResponse",
            "term": self.term,
            "success": self.success,
            "follower_id": self.follower_id,
            "term_number": self.term_number,
            "sender_id": self.follower_id  # Include sender_id for Gradysim
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AppendEntriesResponse':
        """Create AppendEntriesResponse from JSON string."""
        data = json.loads(json_str)
        return cls(data["term"], data["success"], data["follower_id"], data["term_number"])


class DiscoveryHeartbeat(RaftMessage):
    """
    Discovery heartbeat message sent during node discovery before elections.
    
    Attributes:
        term: Current term of the discovering node
        discoverer_id: ID of the node performing discovery
    """
    
    def __init__(self, term: int, discoverer_id: int):
        """
        Initialize DiscoveryHeartbeat message.
        
        Args:
            term: Current term of the discovering node
            discoverer_id: ID of the node performing discovery
        """
        self.term = term
        self.discoverer_id = discoverer_id
    
    def to_json(self) -> str:
        """Convert DiscoveryHeartbeat to JSON string."""
        return json.dumps({
            "type": "DiscoveryHeartbeat",
            "term": self.term,
            "discoverer_id": self.discoverer_id,
            "sender_id": self.discoverer_id  # Include sender_id for Gradysim
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DiscoveryHeartbeat':
        """Create DiscoveryHeartbeat from JSON string."""
        data = json.loads(json_str)
        return cls(data["term"], data["discoverer_id"])


class DiscoveryHeartbeatResponse(RaftMessage):
    """
    Response to DiscoveryHeartbeat message.
    
    Attributes:
        term: Current term of the responding node
        responder_id: ID of the node that responded
    """
    
    def __init__(self, term: int, responder_id: int):
        """
        Initialize DiscoveryHeartbeatResponse message.
        
        Args:
            term: Current term of the responding node
            responder_id: ID of the node that responded
        """
        self.term = term
        self.responder_id = responder_id
    
    def to_json(self) -> str:
        """Convert DiscoveryHeartbeatResponse to JSON string."""
        return json.dumps({
            "type": "DiscoveryHeartbeatResponse",
            "term": self.term,
            "responder_id": self.responder_id,
            "sender_id": self.responder_id  # Include sender_id for Gradysim
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DiscoveryHeartbeatResponse':
        """Create DiscoveryHeartbeatResponse from JSON string."""
        data = json.loads(json_str)
        return cls(data["term"], data["responder_id"])


class MessageFactory:
    """
    Factory class for creating Raft messages from JSON strings.
    
    Provides a centralized way to deserialize messages based on their type.
    """
    
    _message_types = {
        "RequestVote": RequestVote,
        "RequestVoteResponse": RequestVoteResponse,
        "AppendEntries": AppendEntries,
        "AppendEntriesResponse": AppendEntriesResponse,
        "DiscoveryHeartbeat": DiscoveryHeartbeat,
        "DiscoveryHeartbeatResponse": DiscoveryHeartbeatResponse
    }
    
    @classmethod
    def create_from_json(cls, json_str: str) -> RaftMessage:
        """
        Create a Raft message from JSON string.
        
        Args:
            json_str: JSON string representation of the message
            
        Returns:
            Appropriate Raft message instance
            
        Raises:
            ValueError: If message type is not recognized
        """
        try:
            data = json.loads(json_str)
            message_type = data.get("type")
            
            if message_type not in cls._message_types:
                raise ValueError(f"Unknown message type: {message_type}")
            
            return cls._message_types[message_type].from_json(json_str)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
    
    @classmethod
    def register_message_type(cls, message_type: str, message_class: type) -> None:
        """
        Register a new message type with the factory.
        
        Args:
            message_type: String identifier for the message type
            message_class: Class that implements the message
        """
        cls._message_types[message_type] = message_class 