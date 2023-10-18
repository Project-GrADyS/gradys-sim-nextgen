# Usage
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