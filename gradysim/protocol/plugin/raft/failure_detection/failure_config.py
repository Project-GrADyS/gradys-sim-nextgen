"""
Failure Detection Configuration

This module provides configuration options for heartbeat-based failure detection.
"""

from typing import Optional


class FailureConfig:
    """
    Configuration for heartbeat-based failure detection.
    
    This class manages all parameters related to failure detection,
    including thresholds, intervals, and timeouts.
    """
    
    def __init__(self):
        # Default configuration
        self._failure_threshold = 3          # Failed heartbeats to mark as failed
        self._recovery_threshold = 2         # Successful heartbeats to recover
        self._detection_interval = 2         # Check failures every N heartbeats
        self._heartbeat_interval_ms = None   # Reference to heartbeat_interval for calculation
        self._timeout_multiplier = 4         # Default multiplier (4× heartbeat_interval)
        self._heartbeat_timeout_ms = None    # Will be calculated when heartbeat_interval is set
        
        # Absolute timeout configuration
        self._absolute_timeout_ms = None     # Absolute timeout in milliseconds
        self._use_absolute_timeout = False   # Whether to use absolute timeout instead of relative
    
    def set_failure_threshold(self, threshold: int) -> None:
        """
        Set the number of consecutive failed heartbeats to mark a node as failed.
        
        Args:
            threshold: Number of failed heartbeats (default: 3)
        """
        if threshold < 1:
            raise ValueError("Failure threshold must be at least 1")
        self._failure_threshold = threshold
    
    def set_recovery_threshold(self, threshold: int) -> None:
        """
        Set the number of consecutive successful heartbeats to mark a node as recovered.
        
        Args:
            threshold: Number of successful heartbeats (default: 2)
        """
        if threshold < 1:
            raise ValueError("Recovery threshold must be at least 1")
        self._recovery_threshold = threshold
    
    def set_detection_interval(self, interval: int) -> None:
        """
        Set how often to check for failures (in heartbeat intervals).
        
        Args:
            interval: Check every N heartbeats (default: 2)
        """
        if interval < 1:
            raise ValueError("Detection interval must be at least 1")
        self._detection_interval = interval
    
    def set_heartbeat_timeout(self, multiplier: int) -> None:
        """
        Set the timeout for heartbeat responses as a multiple of heartbeat_interval.
        
        Args:
            multiplier: Number of heartbeat intervals to wait (e.g., 4 = 4× heartbeat_interval)
        """
        if multiplier < 1:
            raise ValueError("Timeout multiplier must be at least 1")
        
        self._timeout_multiplier = multiplier
        self._use_absolute_timeout = False  # Switch back to relative timeout
        
        # Validate timeout if heartbeat_interval is already set
        if self._heartbeat_interval_ms is not None:
            timeout_ms = multiplier * self._heartbeat_interval_ms
            if timeout_ms < 100:
                raise ValueError(f"Resulting timeout {timeout_ms}ms must be at least 100ms")
    
    def set_absolute_timeout(self, timeout_ms: int) -> None:
        """
        Set an absolute timeout for heartbeat responses independent of heartbeat_interval.
        
        Args:
            timeout_ms: Timeout in milliseconds (must be positive)
        """
        if timeout_ms <= 0:
            raise ValueError("Absolute timeout must be positive")
        
        # Warning for very low values that may cause false positives
        if timeout_ms < 50:
            import warnings
            warnings.warn(f"Very low timeout ({timeout_ms}ms) may cause false positives in some network conditions")
        
        self._absolute_timeout_ms = timeout_ms
        self._use_absolute_timeout = True  # Switch to absolute timeout
    
    def set_heartbeat_interval_reference(self, interval_ms: int) -> None:
        """
        Set the heartbeat interval reference.
        This is called internally by RaftConfig when heartbeat_interval is set.
        
        Args:
            interval_ms: Heartbeat interval in milliseconds
        """
        if interval_ms <= 0:
            raise ValueError("Heartbeat interval must be positive")
        
        self._heartbeat_interval_ms = interval_ms
        
        # Validate timeout if multiplier is already set
        if self._timeout_multiplier is not None:
            timeout_ms = self._timeout_multiplier * interval_ms
            if timeout_ms < 100:
                raise ValueError(f"Resulting timeout {timeout_ms}ms must be at least 100ms")
    
    def get_heartbeat_interval_reference(self) -> Optional[int]:
        """
        Get the heartbeat interval reference.
        
        Returns:
            Heartbeat interval in milliseconds, or None if not set
        """
        return self._heartbeat_interval_ms
    
    def get_timeout_multiplier(self) -> Optional[int]:
        """
        Get the current timeout as a multiplier of heartbeat interval.
        
        Returns:
            Multiplier value, or None if heartbeat_interval is not set
        """
        if self._heartbeat_interval_ms is None or self._heartbeat_interval_ms == 0:
            return None
        
        # Calculate timeout dynamically
        timeout_ms = self.get_timeout_ms()
        return timeout_ms // self._heartbeat_interval_ms
    
    def get_absolute_timeout_ms(self) -> Optional[int]:
        """
        Get the absolute timeout value.
        
        Returns:
            Absolute timeout in milliseconds, or None if not set
        """
        return self._absolute_timeout_ms
    
    def is_using_absolute_timeout(self) -> bool:
        """
        Check if absolute timeout is being used.
        
        Returns:
            True if absolute timeout is enabled, False otherwise
        """
        return self._use_absolute_timeout
    
    def get_timeout_ms(self) -> int:
        """
        Get the timeout in milliseconds.
        
        Returns:
            Timeout in milliseconds (absolute or calculated as multiplier × heartbeat_interval)
        Raises:
            ValueError: If neither absolute timeout nor heartbeat_interval/multiplier is set
        """
        # If absolute timeout is configured, use it
        if self._use_absolute_timeout and self._absolute_timeout_ms is not None:
            return self._absolute_timeout_ms
        
        # Otherwise, use relative timeout calculation
        if self._heartbeat_interval_ms is None:
            raise ValueError("heartbeat_interval must be set before calculating timeout")
        if self._timeout_multiplier is None:
            raise ValueError("Timeout multiplier must be set before calculating timeout")
        return self._timeout_multiplier * self._heartbeat_interval_ms
    
    @property
    def failure_threshold(self) -> int:
        """Get the failure threshold."""
        return self._failure_threshold
    
    @property
    def recovery_threshold(self) -> int:
        """Get the recovery threshold."""
        return self._recovery_threshold
    
    @property
    def detection_interval(self) -> int:
        """Get the detection interval."""
        return self._detection_interval
    
    @property
    def heartbeat_timeout_ms(self) -> int:
        """Get the heartbeat timeout in milliseconds (calculated dynamically)."""
        return self.get_timeout_ms()
    
    def __str__(self) -> str:
        """String representation of the configuration."""
        if self._use_absolute_timeout and self._absolute_timeout_ms is not None:
            timeout_info = f"absolute_timeout={self._absolute_timeout_ms}ms"
        else:
            timeout_info = f"timeout={self.get_timeout_ms()}ms"
            if self._heartbeat_interval_ms is not None and self._timeout_multiplier is not None:
                timeout_info = f"timeout={self._timeout_multiplier}×{self._heartbeat_interval_ms}ms={self.get_timeout_ms()}ms"
        
        return (f"FailureConfig(failure_threshold={self._failure_threshold}, "
                f"recovery_threshold={self._recovery_threshold}, "
                f"detection_interval={self._detection_interval}, "
                f"{timeout_info})") 