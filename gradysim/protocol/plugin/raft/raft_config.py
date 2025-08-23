"""
Raft Configuration Management

Provides a flexible configuration system for Raft consensus using the Builder pattern.
Allows users to configure election timeouts, heartbeat intervals, consensus variables,
and logging options in a clean, chainable interface.

This module implements the Builder pattern to provide a fluent interface for
configuring Raft consensus parameters.
"""

from typing import Any, Dict, List, Optional, Tuple, Type
import random
from .failure_detection import FailureConfig
from enum import Enum


class RaftMode(Enum):
    """
    Enumeration for Raft operation modes.
    
    CLASSIC: Classic Raft mode - uses fixed cluster size for all calculations
    FAULT_TOLERANT: Fault-tolerant Raft mode - uses active node count for majority calculations
    """
    CLASSIC = "classic"
    FAULT_TOLERANT = "fault_tolerant"


class RaftConfig:
    """
    Configuration class for Raft consensus using Builder pattern.
    
    Provides a fluent interface for configuring all aspects of Raft consensus:
    - Election timeouts
    - Heartbeat intervals
    - Consensus variables
    - Logging options
    
    Example:
        config = RaftConfig()
        config.set_election_timeout(150, 300)
        config.set_heartbeat_interval(50)
        config.add_consensus_variable("sequence", int)
        config.set_logging(True, "INFO")
    """
    
    def __init__(self):
        """Initialize RaftConfig with default values."""
        # Election parameters
        self._election_timeout_min = 150  # milliseconds
        self._election_timeout_max = 300  # milliseconds
        
        # Heartbeat parameters
        self._heartbeat_interval = 50  # milliseconds
        
        # Consensus variables
        self._consensus_variables: Dict[str, Type] = {}
        
        # Logging and debugging
        self._enable_logging = True
        self._log_level = "INFO"
        
        # Failure detection (always enabled for system reliability)
        self._failure_config = FailureConfig()
        
        # Raft operation mode
        self._raft_mode = RaftMode.FAULT_TOLERANT  # Default to fault-tolerant (current behavior)
        

    
    def set_election_timeout(self, min_timeout: int, max_timeout: int) -> 'RaftConfig':
        """
        Set election timeout range.
        
        Args:
            min_timeout: Minimum election timeout in milliseconds
            max_timeout: Maximum election timeout in milliseconds
            
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If min_timeout >= max_timeout or timeouts are negative
        """
        if min_timeout >= max_timeout:
            raise ValueError("min_timeout must be less than max_timeout")
        if min_timeout < 0 or max_timeout < 0:
            raise ValueError("Timeouts must be non-negative")
        
        self._election_timeout_min = min_timeout
        self._election_timeout_max = max_timeout
        return self
    
    def set_heartbeat_interval(self, interval: int) -> 'RaftConfig':
        """
        Set heartbeat interval.
        
        Args:
            interval: Heartbeat interval in milliseconds
            
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If interval is negative
        """
        if interval < 0:
            raise ValueError("Heartbeat interval must be non-negative")
        
        self._heartbeat_interval = interval
        
        # Update failure detection configuration with heartbeat interval reference
        self._failure_config.set_heartbeat_interval_reference(interval)
        
        return self
    
    def add_consensus_variable(self, name: str, var_type: Type) -> 'RaftConfig':
        """
        Add a consensus variable.
        
        Args:
            name: Name of the consensus variable
            var_type: Type of the variable (e.g., int, str, float)
            
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If variable name is empty or already exists
        """
        if not name or not name.strip():
            raise ValueError("Variable name cannot be empty")
        if name in self._consensus_variables:
            raise ValueError(f"Consensus variable '{name}' already exists")
        
        self._consensus_variables[name] = var_type
        return self
    
    def remove_consensus_variable(self, name: str) -> 'RaftConfig':
        """
        Remove a consensus variable.
        
        Args:
            name: Name of the consensus variable to remove
            
        Returns:
            Self for method chaining
        """
        if name in self._consensus_variables:
            del self._consensus_variables[name]
        return self
    
    def set_logging(self, enable: bool, level: str = "INFO") -> 'RaftConfig':
        """
        Configure logging.
        
        Args:
            enable: Whether to enable logging
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            
        Returns:
            Self for method chaining
        """
        self._enable_logging = enable
        self._log_level = level.upper()
        return self
    
    def set_raft_mode(self, mode: RaftMode) -> 'RaftConfig':
        """
        Set the Raft operation mode.
        
        Args:
            mode: Raft operation mode
                  CLASSIC - Classic Raft behavior (fixed cluster size)
                  FAULT_TOLERANT - Fault-tolerant Raft behavior (dynamic active node count)
            
        Returns:
            Self for method chaining
        """
        if not isinstance(mode, RaftMode):
            raise ValueError("mode must be a RaftMode enum value")
        
        self._raft_mode = mode
        return self
    

    

    
    def get_failure_config(self) -> FailureConfig:
        """
        Get the failure detection configuration.
        
        Returns:
            FailureConfig instance for configuring failure detection
        """
        return self._failure_config
    
    def get_raft_mode(self) -> RaftMode:
        """
        Get the current Raft operation mode.
        
        Returns:
            Current Raft operation mode
        """
        return self._raft_mode
    
    def is_classic_mode(self) -> bool:
        """
        Check if running in classic Raft mode.
        
        Returns:
            True if classic mode, False if fault-tolerant mode
        """
        return self._raft_mode == RaftMode.CLASSIC
    
    def is_fault_tolerant_mode(self) -> bool:
        """
        Check if running in fault-tolerant Raft mode.
        
        Returns:
            True if fault-tolerant mode, False if classic mode
        """
        return self._raft_mode == RaftMode.FAULT_TOLERANT
    

    

    
    def get_random_election_timeout(self) -> int:
        """
        Get a random election timeout within the configured range.
        
        Returns:
            Random election timeout in milliseconds
        """
        return random.randint(self._election_timeout_min, self._election_timeout_max)
    
    def get_consensus_variables(self) -> Dict[str, Type]:
        """
        Get all configured consensus variables.
        
        Returns:
            Dictionary mapping variable names to their types
        """
        return self._consensus_variables.copy()
    
    def has_consensus_variable(self, name: str) -> bool:
        """
        Check if a consensus variable exists.
        
        Args:
            name: Name of the consensus variable
            
        Returns:
            True if the variable exists, False otherwise
        """
        return name in self._consensus_variables
    
    def get_consensus_variable_type(self, name: str) -> Optional[Type]:
        """
        Get the type of a consensus variable.
        
        Args:
            name: Name of the consensus variable
            
        Returns:
            Type of the variable, or None if not found
        """
        return self._consensus_variables.get(name)
    
    def validate(self) -> List[str]:
        """
        Validate the configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check election timeout
        if self._election_timeout_min >= self._election_timeout_max:
            errors.append("min_election_timeout must be less than max_election_timeout")
        
        # Check heartbeat interval
        if self._heartbeat_interval >= self._election_timeout_min:
            errors.append("heartbeat_interval should be less than min_election_timeout")
        
        # Check consensus variables
        if not self._consensus_variables:
            errors.append("At least one consensus variable must be configured")
        

        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of the configuration
        """
        config_dict = {
            "election_timeout_min": self._election_timeout_min,
            "election_timeout_max": self._election_timeout_max,
            "heartbeat_interval": self._heartbeat_interval,
            "consensus_variables": {name: var_type.__name__ 
                                  for name, var_type in self._consensus_variables.items()},
            "enable_logging": self._enable_logging,
            "log_level": self._log_level,
            "raft_mode": self._raft_mode.value,
            "failure_config": str(self._failure_config)
        }
        
        # Add heartbeat timeout multiplier information if available
        multiplier = self._failure_config.get_timeout_multiplier()
        if multiplier is not None:
            config_dict["heartbeat_timeout_multiplier"] = multiplier
        
        return config_dict
    
    def __str__(self) -> str:
        """Return string representation of the configuration."""
        return f"RaftConfig({self.to_dict()})"
    
    def __repr__(self) -> str:
        """Return detailed string representation of the configuration."""
        return f"RaftConfig(election_timeout=({self._election_timeout_min}, {self._election_timeout_max}), " \
               f"heartbeat_interval={self._heartbeat_interval}, " \
               f"consensus_variables={list(self._consensus_variables.keys())})" 