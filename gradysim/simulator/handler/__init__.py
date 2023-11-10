"""
The [Simulator][gradysim.simulator.simulation.Simulator] and
[EventLoop][gradysim.simulator.event.EventLoop] provide the backbone upon which handlers
implement functionalities into the simulation. In principle handlers are 
classes that have access to the event loop of the simulation and to it's nodes.

Handlers are registered during the building of the simulation, they are 
associated with a label and providers can access them through this 
label. Protocols can access them indirectly through the providers. 
Handlers can also have indirect effect on protocols indirectly since
they have access to the encapsulated network node.

Every handler implements the [IHandler][gradysim.simulator.handler.interface.INodeHandler]
interface.
"""