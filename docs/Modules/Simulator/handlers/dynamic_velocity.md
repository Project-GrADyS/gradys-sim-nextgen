# Dynamic Velocity Mobility Handler

The Dynamic Velocity Mobility Handler is the mobility model for nodes that are
controlled through velocity commands instead of waypoint targets.

For the conceptual overview of mobility command interpretation, telemetry flow,
and handler switching, see [How Mobility Works](../../../Guides/4_mobility.md).

Use it when you need:

- bounded horizontal and vertical speed
- bounded horizontal and vertical acceleration
- optional first-order velocity tracking with `tau_xy` and `tau_z`
- telemetry that includes both position and current velocity

Related example:

- `showcases/dynamic-velocity-mobility/main.py`

## Package

:::gradysim.simulator.handler.mobility.dynamic_velocity

## Handler

:::gradysim.simulator.handler.mobility.dynamic_velocity.handler.DynamicVelocityMobilityHandler

## Configuration

:::gradysim.simulator.handler.mobility.dynamic_velocity.config.DynamicVelocityMobilityConfiguration

## Telemetry

:::gradysim.simulator.handler.mobility.dynamic_velocity.telemetry.DynamicVelocityTelemetry

## Core Utilities

:::gradysim.simulator.handler.mobility.dynamic_velocity.core
