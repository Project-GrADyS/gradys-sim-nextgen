"""
Raft Lite Adapters

This module provides adapters for integrating Raft Lite with different
simulation platforms and frameworks.

Available adapters:
- GradysimAdapter: For Gradysim simulation platform
"""

from .gradysim_adapter import GradysimAdapter

__all__ = ['GradysimAdapter'] 