"""
Simulator extensions or simply *extensions* are modules that extend the functionality of the **python** simulator.
They are used to implement new features or to provide new ways to interact with the simulation environment.

Extensions are implemented as classes that inherit from the [Extension][gradysim.simulator.extension.extension.Extension]
class. Extensions are attached to a protocol instance but have ways of interacting with the simulation environment
that the protocol does not. In practice, extensions can directly access [handlers][gradysim.simulator.handler] and
modify the simulation environment.

!!!warning
    Extensions are attached to an initialized protocol. Instantiating an extension on an uninitialized protocol will
    raise a `ReferenceError`.

!!!info
    Most extensions rely on a specific handler being present in the simulation. Check their own documentation to see
    which handlers they rely on.
"""