# Simulation
This page will go into details you the classes used to build and run a python
simulation.

![Simulation builder diagram](../../assets/simulation_builder_diagram.svg)

## Building the simulation

The preferred method of creating a python simulation is making use of the 
[SimulationBuilder][simulator.simulation.SimulationBuilder] class that provides 
an API that helps you build your simulation scenario and properly instantiates 
the [Simulator][simulator.simulation.Simulator] class. A
[SimulationConfiguration][simulator.simulation.SimulationConfiguration] is 
passed to the builder during initialization for simulation-level configuration. 

To help you with positioning your nodes some utility methods are also provided.

::: simulator.simulation.SimulationConfiguration
    options:
        heading_level: 3

::: simulator.simulation.PositionScheme
    options:
        heading_level: 3

::: simulator.simulation.SimulationBuilder
    options:
        heading_level: 3



## Running the simulation

After calling the 
[SimulationBuilder.build()][simulator.simulation.SimulationBuilder.build] method 
you will get a Simulator instance. This instance has alreday been pre-baked with 
all the nodes and handlers you configured using your builder. This class will 
manage your simulation which can be started by calling the 
[start_simulation()][simulator.simulation.Simulator.start_simulation]
method. That's the only [Simulator][simulator.simulation.Simulator] method a user 
has to interact with.

The python simulation has the following overall architecture (open in a new tab
if you want to take a closer look):

![Simulator architecture](../../assets/simulator_architecture.svg)

As an event-based simulator one of the main components in the simulation is an
event loop. Events are compact classes containing a timestamp and a callback. 
Events are inserted into the event loop which is organized as a heap to keep the
events with the smallest timestamps on top. At every simulation iteration the 
simulator class grabs the event with the smallest timestamp and executes its
callback.

Events are created by handlers. Protocols indirectly interact with them through
the provider interface they have access to. These events, when executed, cause
effects on the network nodes, mainly observed through calls to the protocol 
interface methods like `handle_timer`. 

The simulation will run until either no more events exist or one of the 
termination conditions set in `SimulationConfiguration` are fired.

::: simulator.simulation.Simulator
    options:
        heading_level: 3

::: simulator.event.EventLoop
    options:
        heading_level: 3

::: simulator.event.Event
    options:
        heading_level: 3