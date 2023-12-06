"""
The `simulator` module implements an event-based network simulation populated by nodes whose behaviours are implemented
as **protocols**. Use this module to implement simulations that run in [prototype-mode][] completely in python,
easy to run and setup.

This package implements a python event-based network simulator that is used to run protocols in **prototype-mode**. As
an event-based simulator it is built around an [event loop][gradysim.simulator.event.EventLoop] that is responsible for
executing events in the simulator. You can use the [simulation builder][gradysim.simulator.simulation.SimulationBuilder]
to create new simulations populated by [nodes][gradysim.simulator.node.Node] and enhanced by
[handlers][gradysim.simulator.handler] that implement specific behaviour.
"""