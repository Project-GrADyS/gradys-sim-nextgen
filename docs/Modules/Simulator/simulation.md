# Simulation
This page will go into details you the classes used to build and run a python
simulation.

![Simulation builder diagram](../../assets/simulation_builder_diagram.svg)

## Building the simulation

The preferred method of creating a python simulation is making use of the 
[SimulationBuilder][gradys.simulator.simulation.SimulationBuilder] class that provides 
an API that helps you build your simulation scenario and properly instantiates 
the [Simulator][gradys.simulator.simulation.Simulator] class. A
[SimulationConfiguration][gradys.simulator.simulation.SimulationConfiguration] is 
passed to the builder during initialization for simulation-level configuration. 

To help you with positioning your nodes some utility methods are also provided.

:::gradys.simulator.simulation.SimulationConfiguration
    options:
        heading_level: 3

:::gradys.simulator.simulation.PositionScheme
    options:
        heading_level: 3

:::gradys.simulator.simulation.SimulationBuilder
    options:
        heading_level: 3



## Running the simulation

After calling the 
[SimulationBuilder.build()][gradys.simulator.simulation.SimulationBuilder.build] method 
you will get a Simulator instance. This instance has already been pre-baked with 
all the nodes and handlers you configured using your builder. This class will 
manage your simulation which can be started by calling the 
[start_simulation()][gradys.simulator.simulation.Simulator.start_simulation]
method. That's the only [Simulator][gradys.simulator.simulation.Simulator] method a user 
has to interact with.

The python simulation has the following overall architecture (open in a new tab
if you want to take a closer look):

![Simulator architecture](../../assets/simulator_architecture.svg)

The simulation will run until either no more events exist or one of the 
termination conditions set in [SimulationConfiguration][gradys.simulator.simulation.SimulationConfiguration] 
are fired. To better understand the simulation you can check how the
[EventLoop][gradys.simulator.event.EventLoop] works.

:::gradys.simulator.simulation.Simulator
    options:
        heading_level: 3