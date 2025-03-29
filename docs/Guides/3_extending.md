# Extending the Simulation

The simulation may not have all possible features that you need. We urge you to
use the tools for extensibility provided by the simulator itself, instead of
modifying the simulator code directly. This will make it easier to update the
simulator to newer versions and sharing your creations with others.

There are a few ways to extend the simulator. We are going to showcase them
in this guide.

## Extension Classes

Extension classes, documented [here][gradysim.simulator.extension], allow a 
protocol to interact directly with the simulation through an extension class.
These classes have access to simulation internals and can modify them as needed.

To be more specific, extension classes have access to 
[handlers][gradysim.simulator.handler]; which are the classes that implement 
parts of the simulation logic. Some examples of handlers are ones that 
implement [mobility][gradysim.simulator.handler.mobility.MobilityHandler] or 
[communication][gradysim.simulator.handler.communication.CommunicationHandler].

To showcase how to create an extension class, we are going to analyze the code
of one of our extension classes, the camera hardware. This extension class
implements a camera attached to a node that can "visually" detect other nodes'
presence within it's field of view.

Before we start, let's take a look at the base extension class code:

```py title="Base extension class"
--8<--
gradysim/simulator/extension/extension.py
--8<--
```

The base extension class is a simple class designed to be subclassed. It only
a single method, the initializer itself. The initializer receives a protocol
instance and, through its provider, acceses simulation internals. Beware that
the protocol itself should no do this if you are interested in keeping your
protocol code abstraction in order. The extension intentionally breaks the 
abstraction layer to allow for mode flexibility.

The extension class can only be used when the protocol is running on the 
python simulator. Every operation of an extension class should become a
no-op when the runtime environment is not the python simulator. The type
of provider is PythonProvider when the runtime environment is the python
simulator, if another provider is present the base extension class is 
set to None.

Now, let's take a look at the camera extension class code. The camera
extension class introduces a simulated camera hardware to the simulation. The
camera can take pictures of the nodes within its field of view and detect
their position and class. The camera integrates with the mobility module 
like this:

```py title="Camera hardware extension class initializer"
--8<--
gradysim/simulator/extension/camera.py:32:32
gradysim/simulator/extension/camera.py:44:47
--8<--
```
??? example "Full code of the camera extension class initializer"
    ```py
    --8<--
    gradysim/simulator/extension/camera.py
    --8<--
    ```

The picture taking process is implemented by looking at every sensor's position
and calculating if its within the camera's field of view. The calculation is 
out of the scope of this tutorial, but you can check the code and 
[documentation][gradysim.simulator.extension.camera.CameraHardware] to 
understand how it works. The camera extension class uses the information
available in the mobility handler to determine the full list of node's and 
their positions here:

```py title="Camera hardware extension class using mobility handler"
--8<--
gradysim/simulator/extension/camera.py:68:68
--8<--
        ...
--8<--
gradysim/simulator/extension/camera.py:80:84
--8<--
```

??? example "Full code of the camera extension class"
    ```py
    --8<--
    gradysim/simulator/extension/camera.py
    --8<--
    ```

To use the camera extension class, simply instantiate it during initialization.
To illustrate a potential use case, we'll implement a simple simulation where
a couple of drones fly over an area and take pictures of the nodes below them,
logging how many they see. The code for this simulation is shown below:

```py title="Protocols using the camera hardware"
--8<--
docs/Guides/camera example/protocol.py
--8<--
```

The point of interest protocol implements no behaviour, it serves simply as a
point of interest for the camera hardware to detect. The Drone protocol randomly
flies above the area and takes pictures of the nodes below it at 5 second
intervals. The simulation code is shown below:

```py title="Simulation using the camera hardware"
--8<--
docs/Guides/camera example/main.py
--8<--
```

The expected output of the simulation is:

```txt
INFO     [--------- Simulation started ---------]
INFO     [it=0 time=0:00:00 | Drone 100 Initialization] RandomMobilityPlugin: Initiating a random trip
INFO     [it=0 time=0:00:00 | Drone 100 Initialization] RandomMobilityPlugin: traveling to waypoint (14.370034502815273, 12.48244048437983, 10.0)
INFO     [it=0 time=0:00:00 | Drone 101 Initialization] RandomMobilityPlugin: Initiating a random trip
INFO     [it=0 time=0:00:00 | Drone 101 Initialization] RandomMobilityPlugin: traveling to waypoint (-24.720737786286406, 32.04056460547929, 10.0)
INFO     [it=0 time=0:00:00 | Drone 102 Initialization] RandomMobilityPlugin: Initiating a random trip
INFO     [it=0 time=0:00:00 | Drone 102 Initialization] RandomMobilityPlugin: traveling to waypoint (-1.4705086519382746, 5.365903305621153, 10.0)
INFO     [it=0 time=0:00:00 | Drone 103 Initialization] RandomMobilityPlugin: Initiating a random trip
INFO     [it=0 time=0:00:00 | Drone 103 Initialization] RandomMobilityPlugin: traveling to waypoint (-22.70707551545876, -36.412604020078106, 10.0)
INFO     [it=0 time=0:00:00 | Drone 100 handle_timer] Detected 3 points of interest
INFO     [it=1 time=0:00:00 | Drone 103 handle_timer] Detected 3 points of interest
INFO     [it=2 time=0:00:00 | Drone 101 handle_timer] Detected 3 points of interest
INFO     [it=3 time=0:00:00 | Drone 102 handle_timer] Detected 3 points of interest
INFO     [it=11037 time=0:00:01.050000 | Drone 102 handle_telemetry] RandomMobilityPlugin: traveling to waypoint (30.939559651294985, 4.471458779580473, 10.0)
INFO     [it=21745 time=0:00:02.060000 | Drone 100 handle_telemetry] RandomMobilityPlugin: traveling to waypoint (10.641625971935532, -43.2282648851834, 10.0)
INFO     [it=43050 time=0:00:04.070000 | Drone 101 handle_telemetry] RandomMobilityPlugin: traveling to waypoint (37.52680363429771, 37.89473119809303, 10.0)
INFO     [it=44321 time=0:00:04.190000 | Drone 102 handle_telemetry] RandomMobilityPlugin: traveling to waypoint (17.293162626366794, 27.386533869882385, 10.0)
INFO     [it=45592 time=0:00:04.310000 | Drone 103 handle_telemetry] RandomMobilityPlugin: traveling to waypoint (-26.725198762915912, 8.771431035907064, 10.0)
INFO     [it=53004 time=0:00:05 | Drone 102 handle_timer] Detected 0 points of interest
INFO     [it=53005 time=0:00:05 | Drone 101 handle_timer] Detected 0 points of interest
INFO     [it=53006 time=0:00:05 | Drone 103 handle_timer] Detected 1 points of interest
INFO     [it=53007 time=0:00:05 | Drone 100 handle_timer] Detected 1 points of interest
INFO     [it=71143 time=0:00:06.720000 | Drone 102 handle_telemetry] RandomMobilityPlugin: traveling to waypoint (-26.91921588222399, 38.910668436612625, 10.0)
INFO     [it=79307 time=0:00:07.490000 | Drone 100 handle_telemetry] RandomMobilityPlugin: traveling to waypoint (-9.859851685045506, -22.136296678139523, 10.0)
INFO     [it=91918 time=0:00:08.680000 | Drone 103 handle_telemetry] RandomMobilityPlugin: traveling to waypoint (8.848617474256883, 18.21708387682807, 10.0)
INFO     [it=106008 time=0:00:10 | Drone 100 handle_timer] Detected 1 points of interest
INFO     [it=106009 time=0:00:10 | Drone 102 handle_timer] Detected 1 points of interest
INFO     [it=106010 time=0:00:10 | Drone 103 handle_timer] Detected 1 points of interest
INFO     [it=106011 time=0:00:10 | Drone 101 handle_timer] Detected 3 points of interest

...

INFO     [it=2120160 time=0:03:20 | Drone 102 handle_timer] Detected 3 points of interest
INFO     [it=2120161 time=0:03:20 | Drone 101 handle_timer] Detected 0 points of interest
INFO     [it=2120162 time=0:03:20 | Drone 103 handle_timer] Detected 1 points of interest
INFO     [it=2120163 time=0:03:20 | Drone 100 handle_timer] Detected 0 points of interest
INFO     [--------- Simulation finished ---------]
INFO     Real time elapsed: 0:00:22.017243	Total iterations: 2120165	Simulation time: 0:03:20.010000
```