# Adapters for Raft Fault

This directory contains adapters that integrate Raft Fault with different platforms or simulation systems.

## Purpose

Adapters encapsulate the integration logic between the Raft core and external environments, such as Gradysim, facilitating code reuse and portability. They implement the **Callback Pattern** to provide a clean separation between the Raft consensus logic and the underlying platform.

## Architecture: The Callback Pattern

Adapters use a callback-based architecture where the Raft core receives function references (callbacks) for platform-specific operations:

```python
# The adapter provides callbacks
callbacks = {
    'send_message_callback': adapter.send_message,
    'send_broadcast_callback': adapter.send_broadcast,
    'schedule_timer_callback': adapter.schedule_timer,
    'cancel_timer_callback': adapter.cancel_timer,
    'get_current_time_callback': adapter.get_current_time,
    'get_node_id_callback': adapter.get_node_id,
    'get_node_position_callback': adapter.get_node_position
}

# Raft uses these callbacks without knowing the platform
raft_node = RaftNode(node_id=1, config=config, callbacks=callbacks)
```

## Available Adapters

### GradysimAdapter

**File**: `gradysim_adapter.py`

Integration adapter for the Gradysim multi-robot simulation platform.

#### Features

- **Communication**: Point-to-point and broadcast messaging
- **Timing**: Timer scheduling and cancellation
- **Node Information**: Dynamic node ID and position retrieval
- **Visualization**: Node coloring for debugging
- **Failure Detection**: Integration with heartbeat-based failure detection
- **Fallback Support**: Graceful handling of different Gradysim versions

#### Required Gradysim Provider Methods

The adapter expects a Gradysim provider with these methods:

```python
provider.send_communication_command(command)  # Send messages
provider.schedule_timer(timer_name, delay_ms) # Schedule timers
provider.cancel_timer(timer_name)             # Cancel timers
provider.current_time()                       # Get current time
provider.get_id()                             # Get node ID
```

#### Usage Examples

**Basic Integration**:
```python
from raft_fault.adapters import GradysimAdapter
from raft_fault import RaftConsensus, RaftConfig

# Create adapter with Gradysim provider
adapter = GradysimAdapter(provider)

# Create Raft consensus with adapter
config = RaftConfig()
consensus = RaftConsensus(config=config, adapter=adapter)

# Start consensus
consensus.start()
```

**Advanced Usage with Failure Detection**:
```python
from raft_fault.failure_detection import HeartbeatDetector, FailureConfig

# Create failure detector
failure_config = FailureConfig()
detector = HeartbeatDetector(
    config=failure_config,
    known_nodes={1, 2, 3, 4, 5},
    on_failure_callback=lambda node_id: print(f"Node {node_id} failed"),
    on_recovery_callback=lambda node_id: print(f"Node {node_id} recovered"),
    get_current_time_callback=adapter.get_current_time
)

# Set failure detector in adapter
adapter.set_failure_detector(detector)

# Create consensus
consensus = RaftConsensus(config=config, adapter=adapter)
```

**Node Visualization**:
```python
# Paint nodes for debugging
adapter.paint_node("red", node_id=1)      # Paint specific node red
adapter.paint_node("blue")                # Paint current node blue
adapter.paint_node("green", node_id=3)    # Paint node 3 green
```

**Position Tracking**:
```python
# Get node position from telemetry
position = adapter.get_node_position(telemetry)
print(f"Node position: {position}")  # (x, y, z)
```

#### Callback Methods

The adapter provides these callbacks to Raft:

| Callback | Method | Description |
|----------|--------|-------------|
| `send_message_callback` | `send_message(message, target_id)` | Send point-to-point message |
| `send_broadcast_callback` | `send_broadcast(message)` | Send broadcast message |
| `schedule_timer_callback` | `schedule_timer(timer_name, delay_ms)` | Schedule timer |
| `cancel_timer_callback` | `cancel_timer(timer_name)` | Cancel timer |
| `get_current_time_callback` | `get_current_time()` | Get simulation time |
| `get_node_id_callback` | `get_node_id()` | Get current node ID |
| `get_node_position_callback` | `get_node_position(telemetry)` | Get node position |

#### Error Handling

The adapter includes robust error handling:

- **Fallback Values**: Returns safe defaults when operations fail
- **Version Compatibility**: Handles different Gradysim versions
- **Graceful Degradation**: Continues operation even with partial failures
- **Logging**: Comprehensive error logging for debugging

## Creating a New Adapter

To create an adapter for a new platform:

### 1. Implement Required Methods

```python
class MyPlatformAdapter:
    def __init__(self, platform_provider):
        self.provider = platform_provider
    
    def send_message(self, message: str, target_id: int) -> None:
        """Send message to specific node"""
        # Platform-specific implementation
        pass
    
    def send_broadcast(self, message: str) -> None:
        """Send broadcast message"""
        # Platform-specific implementation
        pass
    
    def schedule_timer(self, timer_name: str, delay_ms: int) -> None:
        """Schedule timer"""
        # Platform-specific implementation
        pass
    
    def cancel_timer(self, timer_name: str) -> None:
        """Cancel timer"""
        # Platform-specific implementation
        pass
    
    def get_current_time(self) -> float:
        """Get current time"""
        # Platform-specific implementation
        pass
    
    def get_node_id(self) -> int:
        """Get current node ID"""
        # Platform-specific implementation
        pass
    
    def get_callbacks(self) -> dict:
        """Return all callbacks as dictionary"""
        return {
            'send_message_callback': self.send_message,
            'send_broadcast_callback': self.send_broadcast,
            'schedule_timer_callback': self.schedule_timer,
            'cancel_timer_callback': self.cancel_timer,
            'get_current_time_callback': self.get_current_time,
            'get_node_id_callback': self.get_node_id
        }
```

### 2. Export in `__init__.py`

```python
from .my_platform_adapter import MyPlatformAdapter

__all__ = ['GradysimAdapter', 'MyPlatformAdapter']
```

### 3. Add Documentation

Update this README with:
- Platform description
- Usage examples
- Required provider methods
- Special features

## Benefits of the Adapter Pattern

### 1. **Decoupling**
- Raft core doesn't know about specific platforms
- Easy to switch between platforms
- Platform changes don't affect consensus logic

### 2. **Testability**
```python
# Mock adapter for testing
mock_callbacks = {
    'send_message_callback': lambda msg, target: None,
    'schedule_timer_callback': lambda name, timeout: None,
    'get_current_time_callback': lambda: 1000.0
}
node = RaftNode(0, config, mock_callbacks)
```

### 3. **Reusability**
- Same Raft implementation works with different platforms
- Adapters can be shared across projects
- Easy to maintain and update

### 4. **Flexibility**
- Support for platform-specific features
- Custom error handling per platform
- Version compatibility management

## Integration with RaftConsensus

The `RaftConsensus` class provides a simplified interface for using adapters:

```python
# Simple way (recommended)
consensus = RaftConsensus(config, adapter=adapter)

# Alternative way (manual callbacks)
callbacks = adapter.get_callbacks()
consensus = RaftConsensus(config, **callbacks)
```

## Testing Adapters

When testing adapters:

1. **Unit Tests**: Test each method independently
2. **Integration Tests**: Test with actual platform provider
3. **Mock Tests**: Test with mock providers
4. **Error Tests**: Test error handling and fallbacks

## Future Adapters

Potential adapters for future development:

- **ROS2 Adapter**: For Robot Operating System 2
- **ArduPilot Adapter**: For ArduPilot autopilot system
- **WebSocket Adapter**: For web-based simulations
- **Network Adapter**: For real network communication 