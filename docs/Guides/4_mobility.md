# How Mobility Works

This guide explains how mobility works in the prototype-mode simulator, what a
mobility handler does, how mobility commands are interpreted, and how to switch
between the available mobility models.

Use this page for the conceptual model. For the API reference, see:

- [Mobility handler reference](../Modules/Simulator/handlers/mobility.md)
- [Dynamic velocity handler reference](../Modules/Simulator/handlers/dynamic_velocity.md)
- [Mobility message reference](../Modules/Protocol/messages/mobility.md)

## The mobility flow

Mobility in the simulator is split between the protocol and the active mobility
handler:

1. Your protocol decides that the node should move.
2. It sends a [`MobilityCommand`][gradysim.protocol.messages.mobility.MobilityCommand]
   through [`self.provider.send_mobility_command(...)`][gradysim.protocol.interface.IProvider.send_mobility_command].
3. The provider forwards that command to the handler registered under the label
   `"mobility"`.
4. The selected mobility handler interprets the command and updates the node's
   mobility state on each simulation tick.
5. The handler emits telemetry back to the protocol through
   [`handle_telemetry(...)`][gradysim.protocol.interface.IProtocol.handle_telemetry].

This separation is intentional. The protocol decides *what it wants*. The
handler decides *what that command means in the current mobility model*.

## What a handler is

A handler is a simulator component that is injected into the event loop. It can
interact with the event loop by scheduling events and has access to node 
instances.

Mobility handlers are responsible for:

- receiving mobility commands from protocols
- updating positions over time
- optionally keeping extra internal state, such as targets or current velocity
- sending telemetry back to protocols

In practice, the mobility handler is the simulator-side implementation of
movement. The same protocol API stays stable, while different handlers can model
different kinds of motion.

## Why the mobility message is generic

[`MobilityCommand`][gradysim.protocol.messages.mobility.MobilityCommand] is a
generic message with a command type plus up to six numeric parameters.

That means the command object itself does not fully define the behavior. The
meaning comes from two things together:

- the `command_type`
- the handler that receives it

This is why the project provides typed helpers such as:

- [`GotoCoordsMobilityCommand`][gradysim.protocol.messages.mobility.GotoCoordsMobilityCommand]
- [`GotoGeoCoordsMobilityCommand`][gradysim.protocol.messages.mobility.GotoGeoCoordsMobilityCommand]
- [`SetSpeedMobilityCommand`][gradysim.protocol.messages.mobility.SetSpeedMobilityCommand]
- [`SetVelocityMobilityCommand`][gradysim.protocol.messages.mobility.SetVelocityMobilityCommand]

These wrappers make protocol code clearer, but they still serialize into the
same generic `MobilityCommand` structure.

## How the existing handlers interpret commands

The simulator currently exposes two mobility handler families.

### Massless mobility

`MobilityHandler` is the backwards-compatible alias for
[`MasslessMobilityHandler`][gradysim.simulator.handler.mobility.MasslessMobilityHandler].

This model treats nodes as points with no inertia:

- `GOTO_COORDS` sets a target point in Cartesian coordinates
- `GOTO_GEO_COORDS` converts geographic coordinates and sets a target point
- `SET_SPEED` sets the scalar travel speed in meters per second
- movement toward the target is updated every `update_rate`
- telemetry reports position using the base `Telemetry` type

This handler is useful when you want simple target-based movement and do not
need acceleration or velocity-state dynamics.

### Dynamic velocity mobility

[`DynamicVelocityMobilityHandler`][gradysim.simulator.handler.mobility.DynamicVelocityMobilityHandler]
uses a different interpretation.

This model does not move toward waypoints. Instead:

- `SET_SPEED` is interpreted as a desired velocity vector
- `param_1`, `param_2`, and `param_3` are treated as `vx`, `vy`, and `vz`
- the handler tracks that desired velocity subject to acceleration and speed
  limits
- position is integrated from the current velocity on each update
- telemetry reports both position and velocity through
  [`DynamicVelocityTelemetry`][gradysim.simulator.handler.mobility.dynamic_velocity.telemetry.DynamicVelocityTelemetry]

In protocol code, the clearest way to express this is
[`SetVelocityMobilityCommand`][gradysim.protocol.messages.mobility.SetVelocityMobilityCommand]:

```python
from gradysim.protocol.messages.mobility import SetVelocityMobilityCommand

command = SetVelocityMobilityCommand(3.0, 0.0, 1.5)
self.provider.send_mobility_command(command)
```

The important detail is that the message is still generic internally. The
dynamic velocity handler gives `SET_SPEED` a velocity-vector meaning.

## How telemetry changes with the handler

Protocols always receive mobility state through
[`handle_telemetry(...)`][gradysim.protocol.interface.IProtocol.handle_telemetry].
What changes is the telemetry payload.

With the massless handler:

- telemetry contains current position

With the dynamic velocity handler:

- telemetry contains current position
- telemetry also contains current velocity

Example:

```python
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.simulator.handler.mobility.dynamic_velocity.telemetry import DynamicVelocityTelemetry

def handle_telemetry(self, telemetry: Telemetry) -> None:
    position = telemetry.current_position

    if isinstance(telemetry, DynamicVelocityTelemetry):
        velocity = telemetry.current_velocity
```

## How to switch handlers

Switching handlers is done when building the simulation. There is no separate
runtime toggle. The active mobility model is whichever handler you register with
the label `"mobility"` through
[`SimulationBuilder.add_handler(...)`][gradysim.simulator.simulation.SimulationBuilder.add_handler].

### Using the default massless mobility handler

```python
from gradysim.simulator.handler.mobility import MobilityConfiguration, MobilityHandler

builder.add_handler(
    MobilityHandler(
        MobilityConfiguration(
            update_rate=0.05,
            default_speed=10.0,
        )
    )
)
```

This is the same model already used by most existing examples and plugins.

### Switching to the dynamic velocity handler

```python
from gradysim.simulator.handler.mobility import (
    DynamicVelocityMobilityConfiguration,
    DynamicVelocityMobilityHandler,
)

builder.add_handler(
    DynamicVelocityMobilityHandler(
        DynamicVelocityMobilityConfiguration(
            update_rate=0.05,
            max_speed_xy=10.0,
            max_speed_z=5.0,
            max_acc_xy=4.0,
            max_acc_z=4.0,
            tau_xy=0.5,
            tau_z=0.8,
        )
    )
)
```

After this change, the protocol still calls
`self.provider.send_mobility_command(...)`, but the command should now match the
dynamic velocity semantics.

## Choosing the right handler

Use the massless handler when:

- your protocol thinks in destinations or waypoints
- you want simple movement with minimal configuration
- you are using plugins built around target-based movement

Use the dynamic velocity handler when:

- your controller outputs velocity vectors directly
- you need acceleration limits or first-order velocity tracking
- your protocol needs current velocity in telemetry

## Practical rule

Write protocol code against the provider interface, but choose mobility command
helpers that match the handler you registered.

That is the main contract:

- the provider API is stable
- the message container is generic
- the handler defines the actual motion model
