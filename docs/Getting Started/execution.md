# Execution Modes

## Prototype mode
The user-defined protocol is executed in a very simple python event-based network
simulator. The idea behind this mode is that it is very quick to set up, basically
dependency free and very light. These characteristics make it perfect for prototyping
and learning. Changes can be quickly implemented and tested and the simple nature of
the simulator makes it a good learning tool for people unfamiliar with how these 
distributed algorithms are typically implemented.

The simulator doesn't offer many tools to accurately simulate a real-world simulation.
This is an intentional decision to keep this execution mode as simple as possible. 
You will be working with an abstraction, a simplified representation of the real world 
that allows you to validate the protocol you implemented.

Although simple don't underestimate how useful this execution mode is. The tools 
provided can help validate your protocol under a surprising amount of conditions. 
The instructions on how to use this mode and the full list of features are available
in the documentation for the simulation module [here](../Modules/Simulator/index.md).

## Integrated mode
Integrated mode uses the OMNeT++ network simulator to execute the user-defined 
protocols in a realistic network simulation environment. The OMNeT++ simulation
and integration are hosted in a different repository accesible 
[here](https://github.com/Project-GrADyS/gradys-simulations). There you will find
installation instructions and a guide on how to use it.

## Experiment mode
The idea behing this mode is allowing the user to run their protocols integrated
with an actual real vehicle running Ardupilot.

This mode has not been implemented yet. Check back later for updates!