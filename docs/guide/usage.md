# Usage
## Understanding a protocol

Protocols are classes that implements your algorithms main logic. The class is
called protocol because it defines the behaviour protocol of the node. If you
are satisfied with the simulation environment provided ready to use by **GrADyS-SIM
TNG**, this is the only class you need to code. You can use your protocol on any
simulation environment. We will be using [prototype mode](execution.md#prototype-mode)
to run a protocol within a python environment.

Before building a protocol it is important to have a basic idea of what you are
building. Protocols are classes that implement node behaviour on an event based
environment. Event based means that you will program your logic in a reactive
way. In other words the program's execution flow will only run code within your
class when something happens to the node whose logic you are programming. This
"something" can be a timer firing, a message being received or some information
about your mobility being transferred to it. This is very similar to how user
interfaces are build, they lay idle and react to user inputs.

![protocol diagram](../assets/protocol_diagram.png)

Protocols have to inherit from the `IProtocol` class and implement the protocol
interface this base class defines. These methods are called to react to some
event relevant to the network node hosting your protocol. The logic of your
protocol is implemented in these reactions. 

Protocols have use to a set of methods accessible through a `IProvider` instance
which is available through `self.provider` defined in the base protocol class. 
These methods are how the protocol interacts with its environment. Methods are 
available to send messages, move to specific places, schedule timers and more.

## Building our first protocol

``` py title="counter_protocol.py"
--8<-- "docs/guide/counter example/1/counter_protocol.py"
```

The protocol above is very simple. All it does is use the _provider_ methods available
to the protocol to schedule a timer that fires every second. When this timer
fires the protocol increments a counter and sets the timer again.

Now that we have created a protocol, we just have to execute it. As mentioned we
will be using [prototype mode](execution.md#prototype-mode) for this example. Creating
a simulation is preferably done through the [SimulationBuilder](modules/simulation.md#Simulation Builder) 
class. This class presents a simple API for instantiating python simulations. 

``` py title="counter_execution.py"
--8<-- "docs/guide/counter example/1/counter_execution.py"
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

## Adding Communication
The last example, while useful to demonstrate how a protocol is the class that 
implements your logic in an event-based manner, didn't demonstrate one of the
main features of the simulator: communication. One of the biggest challenges
of building distributed systems is that they rely on asynchronous communication
to share information between nodes. 

GrADyS-SIM TNG will help you build these kinds of systems by providing support
for communication between network nodes. Nodes share messages with each other by
using communication commands. 