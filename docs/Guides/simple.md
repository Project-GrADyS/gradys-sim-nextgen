# Simulating a data collection scenario

!!!info
    This guide will step through the complete implementation of a protocol and execution in **prototype-mode**.

??? example "Full code of the protocols implemented in this guide"
    ```py
    --8<--
    docs/Guides/simple example/simple_protocol.py
    --8<--
    ```

??? example "Full code needed to execute this example"
    ```py
    --8<--
    docs/Guides/simple example/main.py
    --8<--
    ```

## Scenario description
We have sensors spread around some location. These sensors collect information about their local 
environment which is of interest to us. The deployment location has no communication infrastructure and is hard to 
access, so to get the information out of these sensors we will employ a UAV swarm. The UAVs will fly autonomously to 
the deployment location, retrieve data from the sensors through local communication and fly back to a central ground
station where the data will be offloaded and analysed. 

The number of UAVs that are available for this mission is equal to the number of sensors deployed in the field, thus 
each UAV will only monitor one sensor.

Here is some additional information about the scenario's requirements:

- UAVs should continuously fly between the deployment location and the ground station
- Sensors are continuously collecting data and generate new packets periodically at a steady rate
- Every packet a sensor has will be transferred once a UAV makes contact with it
- There is no limit to how many packets any agent can carry
- The ground station is effectively a packet sink
- Communication is local and it's range is limited

## Designing the simulation

We have three different types of agents in this scenario: sensors, UAVs and the ground station. Since each agent type
behaves differently, three protocol classes will be created. The protocols that will implement the agent type behaviours are very simple and can each be described in a couple of 
steps:

```markdown title="Sensor protocol"
1. Periodically generates packets and stores them
2. Listens for any UAV messages and responds by sending to the UAV every packet 
   stored in the sensor
```

```markdown title="UAV protocol"
1. Repeatedly flies between the ground station and a sensor
2. Periodically tries to communicate with nearby agents, advertising the number 
   of packets it contains
3. Stores packets received from sensors
4. Drops packets after sending them to the ground station
```

```markdown title="Ground station protocol"
1. Listens for any UAV communication and absorbs their packets
2. Responds to the sender UAV confirming that their packets were received
```

Although independent the three protocol types will need to communicate to complete their task. In GrADyS-SIM NextGen
communication is done through messages containing a string payload. In order to facilitate implementation we need to
define a common message format that is serializable and has every field necessary for communication. 

Interactions in the protocols above are defined between agent types, `UAV <-> sensor` and `UAV <-> ground station` 
message exchanges are handled in different ways. So, if we want to use a common message format, we need to include 
the **agent type** in the format to allow these interactions to be defined. 

Protocols talk to each other in a request-response manner, generally with the UAV initiating the exchange. In order to
know who to respond to we need to have the **agent id** in  the message definition.

Finally, in our interactions the sensor transmits packets to the UAVs, and they transmit packets to the ground station. 
We need to know the agent's **packet count** in order to implement the transmission.

## Implementing the protocols
With our requirements ready all that is left is translating all this into protocol code. Our use-case is very simple
so it will be easy to present the code step-by-step. Let's first show the SimpleMessage implementation. Following
our requirements we implemented the simple message as a dictionary. In order to have typing hints we create a `TypedDict`
class containing the desired fields. GrADyS-SIM NextGen doesn't impose any 

```py title="Message declaration"
--8<--
docs/Guides/simple example/simple_protocol.py:19:22
--8<--
```

To identify the types of agents in our simulation we will use the `SimpleSender`
enum shown below. 

```py title="SimpleSender enum"
--8<--
docs/Guides/simple example/simple_protocol.py:13:17
--8<--
```

To help us with logging a `report_message` function is defined. It receives
a SimpleMessage and appropriately logs it.

```py title="Message logging"
--8<--
docs/Guides/simple example/simple_protocol.py:19:23
--8<--
```

### Sensor

The first protocol we will implement in the sensor is the periodic data generation. Below is a snippet from the protocol's
initialize method, we are storing the generated packets in the `self.packet_count` variable, at simulation start 0 
packets are in storage. The `_generate_packet` method increments this counter by one and schedules a timer for  one
second later. The `handle_timer` is called when this timer fires and in turn calls the `_generate_packet` method again.
This creates an infinite loop which with a periodicity of 1 second increments the packet counter.

```py title="Sensor initialization and timer"
--8<--
docs/Guides/simple example/simple_protocol.py:33:34
docs/Guides/simple example/simple_protocol.py:36:41
docs/Guides/simple example/simple_protocol.py:43:46
--8<--
```

Next we need to implement the interaction with other modules. The `handle_packet` method will be called when a message
is recieved from another module. This missage will be a SimpleMessage and needs to be deserialized. The only relevant
interaction in the sensor is with an UAV, so we will only implement that. The code below shows a snipped from the 
`handle_packet` method. After receiving a message from a UAV the sensor will send every one of its packets to the UAV
and zero out the `self.packet_count` counter.

```py title="Sensor interactions"
--8<--
docs/Guides/simple example/simple_protocol.py:48:49
docs/Guides/simple example/simple_protocol.py:51:64
--8<--
```

??? example "Full sensor code"
    ```py
    --8<--
    docs/Guides/simple example/simple_protocol.py:30:70
    --8<--
    ```

### Ground Station

The ground station is the second protocol we will implement. It is even more simple them the sensor since it doesn't
require any periodic timer to function. The snipped below covers the initialization of a `self.packet_count` property
storing the number of packets that have been delivered to the ground station and the definition of the `handle_packet`
method. The handling behaviour only cares about messages that came from UAVs, when received the ground station adds the
packets the UAV contains to its packet count and sends a message back to the UAV, so it can know his packets have been
delivered.

```py title="Ground station initialization and interactions"
--8<--
docs/Guides/simple example/simple_protocol.py:151:151
docs/Guides/simple example/simple_protocol.py:153:154
docs/Guides/simple example/simple_protocol.py:158:159
docs/Guides/simple example/simple_protocol.py:161:172
--8<--
```

??? example "Full ground station code"
    ```py
    --8<--
    docs/Guides/simple example/simple_protocol.py:147:179
    --8<--
    ```

### UAV

The UAV protocol is the most complicated one as it has to interact to both sensors and the ground station. It also needs
to periodically broadcast the number of packets it has to initiate interactions with other agents. The snipped bellow
illustrates the protocol's initialization and this timer, it is implemented in a similar way to the sensor packet 
generation timer. The `_send_heartbeat` function implements a recurrent timer with a periodicity of 1 second that 
broadcasts the message.

```py title="UAV initialization and timer"
--8<--
docs/Guides/simple example/simple_protocol.py:100:100
docs/Guides/simple example/simple_protocol.py:102:102
docs/Guides/simple example/simple_protocol.py:110:110
docs/Guides/simple example/simple_protocol.py:111:112
docs/Guides/simple example/simple_protocol.py:115:123
--8<--
```

Another thing the UAV needs to do is actually travel from the sensors to the ground station. We will use the
[MissionMobilityPlugin][gradysim.protocol.plugin.mission_mobility.MissionMobilityPlugin] to implement this. This plugin
allows us to specify a list of waypoints and configure a looping mission that will have our node follow this list of 
waypoints infinitely. Since we want each of our UAVs to go to a different sensor, we will prepare a list of missions
that the UAVs will pick from during initialization. Each mission starts at (0,0), where the ground station will be
and flies to one of the sensor's deployment locations which we will define later. The UAVs always fly 20 meters above
the ground.

```py title="List of missions"
--8<--
docs/Guides/simple example/simple_protocol.py:73:90
--8<--
```

```py title="UAV mission initalization"
--8<--
docs/Guides/simple example/simple_protocol.py:104:108
--8<--
```

Next let's define our interactions with other protocols in the `handle_packet` method. A message from a sensor means 
that one of our messages has been received, and it is sending us its packets, in that case we accept them and add them
to our `self.packet_count` property. If a message is received from the ground station it means that we have succesfully
delivered our packets to it, and we should discard them. The snippet below shows this behaviour.

```py title="UAV interactions"
--8<--
docs/Guides/simple example/simple_protocol.py:128:129
docs/Guides/simple example/simple_protocol.py:131:133
docs/Guides/simple example/simple_protocol.py:136:136
docs/Guides/simple example/simple_protocol.py:138:138
--8<--
```

??? example "Full UAV code"
    ```py
    --8<--
    docs/Guides/simple example/simple_protocol.py:73:145
    --8<--
    ```

## Executing what we've built

Everything up to this point has been related only to protocols. The protocol we created above should be able to run in
any execution-mode. We will create a prototype-mode simulation to test it.

!!!warning
    Although the protocol will run on any environment it doesn't mean that all interactions will work exactly the same.
    Different environments bring with them new complexities that you might not have anticipated when you built your
    protocol. These protocols, for example, would have issues in integrated-mode as OMNeT++ simulates message colisions
    and all our UAVs send messages exactly every 1 second. A simple way to fix this would be introducing a small random
    delay to UAV messages. This is an example of how having varied environments can help you build more robust protocols.

```py title="Execution code for prototype-mode"
--8<--
docs/Guides/simple example/main.py
--8<--
```

!!!danger
    This pattern of defining a main function and running it only if the file is being executed directly is required if
    you are using the VisualizationHandler as it will spawn a new process to run the visualization thread. Read more
    about this in [the handler's documentation][gradysim.simulator.handler.visualization.VisualizationHandler]. 

The code above configures a python simulation that will run for 200 seconds. Four sensors are added to the
simulation at specific deployment locations around a 300x300 meter area centered around (0,0). Four UAVs are 
instantiated, each of them will serve one of these sensors. Last, the ground station is created at (0,0)) on the
ground. 

After all the node's have been added we will add the handlers required for this simulation to run. The timer handler
is required to enable timers, communication handler is also added and configured for a communication range of 30
meters. Mobility is also necessary to enable movement and finally visualization is added so we can watch the simulation
progress.

Finally, we build the simulation and run it.

# Results

After running the simulation you will see that some useful stats have been logged. They indicate that the UAVs were 
successful in transporting messages from the sensors to the ground station. Over the entire simulation over 600
packets were delivered to the ground station by them.

```
INFO     [it=0 time=0:00:00 | SimpleSensorProtocol 0 Finalization] Final packet count: 43
INFO     [it=0 time=0:00:00 | SimpleSensorProtocol 1 Finalization] Final packet count: 43
INFO     [it=0 time=0:00:00 | SimpleSensorProtocol 2 Finalization] Final packet count: 43
INFO     [it=0 time=0:00:00 | SimpleSensorProtocol 3 Finalization] Final packet count: 43
INFO     [it=0 time=0:00:00 | SimpleUAVProtocol 4 Finalization] Final packet count: 0
INFO     [it=0 time=0:00:00 | SimpleUAVProtocol 5 Finalization] Final packet count: 0
INFO     [it=0 time=0:00:00 | SimpleUAVProtocol 6 Finalization] Final packet count: 0
INFO     [it=0 time=0:00:00 | SimpleUAVProtocol 7 Finalization] Final packet count: 0
INFO     [it=0 time=0:00:00 | SimpleGroundStationProtocol 8 Finalization] Final packet count: 632
```

