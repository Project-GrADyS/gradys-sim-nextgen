# Introduction

GrADyS-SIM TNG is a network simulation framework whose primary focus are
usability and flexibility. Usability is achieved by opting for a simple to
use python simulation API that allows you to quickly build and prototype
decentralized algorithms in a network simulation environment. Flexibility
is achieved by enabling the user to reuse his algorithm implementations
on a more realistic network simulation scenario by integrating with OMNeT++
and, in the future, even reuse his algorithms in the real world through a
MAVLINK integration.

The framework was created to be used in three main ways: **prototype mode**,
**integrated mode** and **experiment mode**. As mentioned one of the main
features of this framework is that you can use the exact same implemented
logic on all three modes, without changing a line of code. You can understand
more about these modes in the execution mode documentation [here](execution.md).

What's being executed in these three modes is a central piece of code called
**protocols**. Protocols are user-defined classes that implement some kind of
logic, they dictate the behaviour of a **simulation node**. A simulation node
is an entity that exists within the simulation environment. It interacts with
the environment through movement and with other nodes through network communication.

The way protocols are build they can interact with the environment without
being dependent on a specific environment implementation. They observe and
act through interfaces provided to them during execution in a technique
commonly called dependency injection. What this means is that you can re-utilize
that same code in completely different environments as long as someone has done
the work of integrating that environment with the interfaces that the protocol
expects. GrADyS-SIM TNG provides integrations to three environment types which
are the previously mentioned modes.

## Quick Setup

Write

## Building a Protocol

Protocols are classes that implements your algorithms main logic. The class is
called protocol because it defines the behaviour protocol of the node. If you
are satisfied with the simulation environment provided ready to use by **GrADyS-SIM
TNG**, this is the only class you need to code. You can use your protocol on any
simulation environment. We will be using [prototype mode](execution.md#prototype-mode)
to run a protocol within a python environment

Before building a protocol it is important to have a basic idea of what you are
building. Protocols are classes that implement node behaviour on an event based
environment. Event based means that you will program your logic in a reactive
way. In other words the program's execution flow will only run code within your
class when something happens to the node whose logic you are programming. This
"something" can be a timer firing, a message being received or some information
about your mobility being transferred to it. This is very similar to how user
interfaces are build, they lay idle and react to user inputs.

Protocols have to inherit from the `IProtocol` class and define the abstract
methods that the interface specifies. These methods are called to react to some
event relevant to the network node hosting your protocol. The logic of your
protocol is implemented in these reactions. 

``` py title="protocol.interface.py"
--8<-- "protocol/interface.py"
```

Let's take a look at a very simple protocol:

``` py title="counter_protocol.py"
--8<-- "docs/counter_protocol.py"
```

Now that we have created a protocol, we just have to execute it. As mentioned we
will be using [prototype mode](execution.md#prototype-mode) for this example. 