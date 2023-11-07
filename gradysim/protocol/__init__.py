"""
Use this module to create protocols. What GrADyS-SIM TNG calls protocols is the logic that powers network nodes. Each
network node has a protocol instance that is responsible for the node's behavior. Protocols define how a node reacts
to its environment and enable it to interact with it.

Protocols are environment agnostic, meaning they are not coupled to a specific environment. This allows for the same
protocol to be used in different environments. For example, a protocol that defines how a node reacts to its environment
can be used in different simulation environments and even in a real-world environment.

Protocols are created by subclassing the [IProtocol][gradysim.protocol.interface.IProtocol] interface. The IProtocol interface
defines the methods that a protocol must implement. These methods are reactive in nature, meaning they are called to
react to events that occur in the environment. For example, a protocol may implement a method that is called when a node
 receives a message from another node. The protocol can then react to the message by sending a message back to the
 sender or by sending a message to another node.

The protocol interface also guides how the protocol can affect its environment, through a
[IProvider][gradysim.protocol.interface.IProvider] instance that is injected into the protocol when it is instantiated. The
IProvider instance provides the protocol with the necessary tools to interact with the environment. It enables the
protocol to send messages to other nodes, schedule timers, and more.

Messages are sent using the [CommunicationCommand][gradysim.protocol.messages.communication.CommunicationCommand] class. It
instructs the node's communication module to perform some communication action, generally sending a message to another
node. The node's communication module is not known by the protocol and shouldn't be its concern. The protocol only
needs to know how to send messages and the IProvider instance provides it with the necessary tools to do so.

The protocol can affect its node's mobility by sending [MobilityCommand][gradysim.protocol.messages.mobility.MobilityCommand] via
the IProvider instance. The MobilityCommand class instructs the node's mobility module to perform some mobility action,
generally moving the node to a new location. The node's mobility module is not known by the protocol and shouldn't be
its concern. The protocol only needs to know how to move the node and the IProvider instance provides it with the
necessary tools to do so.

The protocol can also schedule timers using the IProvider instance. Timers are scheduled using the schedule_timer()
method. The method takes a timer and a timestamp as arguments.
"""