"""
Raft State Management

Defines the three fundamental states of a Raft node:
- FOLLOWER: Default state, responds to requests from leaders and candidates
- CANDIDATE: Used during leader election
- LEADER: Handles all client requests and values replication

This module provides a clean enumeration of Raft states with proper
documentation for each state's responsibilities.
"""

from enum import Enum, auto


class RaftState(Enum):
    """
    Raft node states enumeration.
    
    Each state represents a different role and behavior in the Raft consensus algorithm.
    """
    
    FOLLOWER = auto()
    """
    Follower state - Default state for all nodes.
    
    Responsibilities:
    - Respond to requests from leaders and candidates
    - Start election if election timeout elapses
    - Vote for candidates during elections
    - Accept log entries from leader
    """
    
    CANDIDATE = auto()
    """
    Candidate state - Used during leader election.
    
    Responsibilities:
    - Increment current term
    - Vote for self
    - Request votes from other nodes
    - Become leader if majority votes received
    - Return to follower if another leader discovered
    """
    
    LEADER = auto()
    """
    Leader state - Handles all client requests and log replication.
    
    Responsibilities:
    - Send periodic heartbeats to all followers
    - Handle client requests
    - Replicate log entries to followers
    - Commit entries when majority replicated
    - Step down if higher term discovered
    """
    
    def __str__(self) -> str:
        """Return string representation of the state."""
        return self.name
    
    def __repr__(self) -> str:
        """Return detailed string representation of the state."""
        return f"RaftState.{self.name}" 