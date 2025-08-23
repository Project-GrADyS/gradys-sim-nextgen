"""
Failure Detection Module for Raft Lite

This module provides heartbeat-based failure detection for Raft consensus nodes.
"""

from .failure_config import FailureConfig
from .failure_state import FailureState
from .heartbeat_detector import HeartbeatDetector

__all__ = ['FailureConfig', 'FailureState', 'HeartbeatDetector'] 