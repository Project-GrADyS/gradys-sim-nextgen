# Follow Mobility

The Follow Mobility plugin implements a **leader/follower** pattern where one or more leader nodes
broadcast their position and follower nodes autonomously track and move towards them.

## How It Works

The plugin is split into two independent components, a **leader** and a **follower**, that
communicate through the simulation's broadcast messaging system via the
[Dispatcher](dispatcher.md) plugin.

### Leader (`MobilityLeaderPlugin`)

The leader periodically broadcasts its current position and orientation to all nodes in range.
It does not control the node's movement, your protocol is free to move the leader however you like
(e.g., via a mission mobility plugin or manual commands). The leader also tracks which followers
are currently connected by listening for acknowledgment messages.

Key behaviors:

- Broadcasts position + orientation at a configurable interval (`broadcast_interval`).
- Automatically tracks its own position via telemetry updates.
- Culls followers that haven't responded within `follower_timeout` seconds.
- Exposes a `followers` property to query currently connected followers.

### Follower (`MobilityFollowerPlugin`)

The follower listens for leader broadcasts and moves to maintain a configurable relative
position offset from the followed leader. It periodically scans for available leaders and
handles leader disconnections.

Key behaviors:

- Maintains a list of available leaders based on received broadcasts.
- By default, auto-follows the first available leader (`auto_follow=True`). This can be
  disabled to require explicit calls to `follow_leader()`.
- Moves to `leader_position + relative_position` on each leader broadcast.
- Sends an acknowledgment message back to the leader on each update.
- Detects leader disconnection after `leader_timeout` seconds of silence.

## Orientation Support

The leader has a configurable **orientation** (in degrees, counter-clockwise from the +X axis)
that is included in every broadcast. When orientation-aware following is enabled
(`follow_orientation=True`, the default), the follower's relative position offset is rotated
by the leader's orientation before being applied.

This means the follower formation rotates together with the leader's heading. For example, a
follower at relative position `(10, 0, 0)` (10 units ahead) will always stay 10 units ahead
of the leader in the direction the leader is facing, rather than always staying at a fixed
world-coordinate offset.

The leader's orientation can be changed at any time via `set_orientation()`.

!!! warning "Mobility Control"
    The **follower plugin controls your protocol's mobility**. You should not use any other
    mobility plugin alongside it or implement custom mobility behavior in a follower protocol.
    The leader plugin does **not** affect movement and is safe to combine with other mobility
    plugins.

## Quick Usage Example

```python
from gradysim.protocol.interface import IProtocol
from gradysim.protocol.plugin.follow_mobility import (
    MobilityLeaderPlugin,
    MobilityLeaderConfiguration,
    MobilityFollowerPlugin,
    MobilityFollowerConfiguration,
)


class LeaderProtocol(IProtocol):
    def initialize(self):
        self.leader = MobilityLeaderPlugin(
            self,
            MobilityLeaderConfiguration(
                broadcast_interval=0.1,
                initial_orientation=90.0,  # facing +Y
            ),
        )

    def handle_timer(self, timer):
        pass

    def handle_packet(self, message):
        pass

    def handle_telemetry(self, telemetry):
        pass

    def finish(self):
        pass


class FollowerProtocol(IProtocol):
    def initialize(self):
        self.follower = MobilityFollowerPlugin(
            self,
            MobilityFollowerConfiguration(
                follow_orientation=True,
            ),
        )
        # Stay 10 units behind the leader (relative to leader's heading)
        self.follower.set_relative_position((-10, 0, 0))

    def handle_timer(self, timer):
        pass

    def handle_packet(self, message):
        pass

    def handle_telemetry(self, telemetry):
        pass

    def finish(self):
        pass
```

## API Reference


:::gradysim.protocol.plugin.follow_mobility