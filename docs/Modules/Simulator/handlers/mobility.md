# Mobility

The mobility subsystem currently exposes two handler families:

- `MasslessMobilityHandler`: target-based motion with instantaneous speed changes and no inertia.
- `DynamicVelocityMobilityHandler`: dynamic velocity mobility with velocity commands, acceleration limits, and velocity telemetry.

For a conceptual explanation of how protocols, mobility commands, handlers, and
telemetry fit together, see [How Mobility Works](../../../Guides/4_mobility.md).

For the dynamic velocity mobility API, see [Dynamic Velocity Mobility Handler](dynamic_velocity.md).

:::gradysim.simulator.handler.mobility

## Massless Mobility Handler

:::gradysim.simulator.handler.mobility.massless.MasslessMobilityHandler

:::gradysim.simulator.handler.mobility.massless.MasslessMobilityConfiguration

## Dynamic Velocity Mobility Handler

See [Dynamic Velocity Mobility Handler](dynamic_velocity.md) for the full handler,
configuration, telemetry, and core API reference.
