# Introduction

## What is GrADyS-SIM TNG?

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

## Why does GrADyS-SIM TNG exist?

![GrADyS and LAC](assets/gradys-and-lac.png){ align=center }

[GrADyS](https://www.lac.inf.puc-rio.br/index.php/gradys/) is a project member of 
a laboratory called [LAC](https://www.lac.inf.puc-rio.br/) from PUC-Rio university. 
Our main work is focused on exploring the coordination of autonomous vehicles through 
descentralized algorithms.

We created GrADyS-SIM to enable us to test our algorithms in a controlled, cheap and
fast environment. Field tests are expensive and consume large amounts of time. Having
a simulation environment helps us understand and validate things before we take them
to the field.

GrADyS-SIM was created first and foremost to serve as a tool for the GrADyS project. As
we developed it we noticed that this could be a very useful tool not only for us but for
the scientific community in general. 

GrADyS-SIM runs in the [OMNeT++](https://omnetpp.org/) which is an event-based 
network simulator that enabled us to quickly model very complex network architectures 
and test the effects ofdifferent scenarios, network protocols and components on our 
algorithms. OMNeT++ although stillvery useful has a very steep learning curve, even 
setting it up is a very involved process thatrequires specific setups to get it working 
perfectly. Even for the people inside our project it is cumbersome to work with so we 
concluded that some new tool needed to be built to remedy this.

GrADyS-SIM-TNG was envisoned as a low-dependency, light and easy to use simulator that
would not substitute OMNeT++ but fill the niche of being a tool for quick prototyping 
before more realistic results would be collected from OMNeT++. An issue we already had
was translating results from the OMNeT++ simulation to the real world. Introducing a 
new link in this chain would only make this disconnect between our imlpementation
environments greather, so GrADyS-SIM TNG would need to somehow generate code that could
be run everywhere, in python, OMNeT++ and the real world. 

These were our motivations to create this tool. We are also taking extra care to make
sure this won't be a tool only for the GrADyS project, but for anyone with similar
interests to ours. This means creating a very general implementation that can be 
used to implement all kinds of different ideas, instead of something focused only
on our area of research.

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
will be using [prototype mode](execution.md#prototype-mode) for this example. Creating
a simulation is preferably done through the [SimulationBuilder](modules/simulation.md#Simulation Builder) 
class. This class presents a simple API for instantiating python simulations. 

``` py title="counter_execution.py"
--8<-- "docs/counter_execution.py"
```


Running the file above we will notice the following output on our terminal:

```
INFO     [--------- Simulation started ---------]
INFO     [--------- Simulation finished ---------]
INFO     [it=0 time=0:00:00 | Node 0 Finalization] Final counter value: 10
INFO     Real time elapsed: 0:00:00.000195      Total iterations: 10    Simulation time: 0:00:10
```

We can see that the simulation ran for 10 simulation seconds which took 0.000195 
real-world seconds to execute. In that time we ran 10 simulation iterations. Remember
that our CounterProtocol sets a timer for every second, so the number of iterations
is expected. What is also expected is the "Final counter value" logged, which is 10.