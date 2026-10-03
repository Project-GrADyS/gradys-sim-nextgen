# Using Ardupilot SITL for realistic UAV simulation

!!!info
    This guide walks through adapting the data collection scenario from 
    [Guide 2](2_simple.md) to use **ArdupilotMobilityHandler** for realistic
    Software-In-The-Loop (SITL) simulation. If you haven't read Guide 2 yet,
    we recommend going through it first to understand the base scenario.

??? example "Full code of the protocols implemented in this guide"
    ```py
    --8<--
    docs/Guides/ardupilot example/simple_protocol.py
    --8<--
    ```

??? example "Full code needed to execute this example"
    ```py
    --8<--
    docs/Guides/ardupilot example/main.py
    --8<--
    ```

## Why use ArdupilotMobilityHandler?

The standard [MobilityHandler][gradysim.simulator.handler.mobility.MobilityHandler] moves nodes using simple 
linear interpolation. While great for prototyping, it doesn't capture the physical reality of flying a vehicle: 
there is no takeoff sequence, no banking in turns, no battery drain, and no realistic flight dynamics.

The [ArdupilotMobilityHandler][gradysim.simulator.handler.ardupilot_mobility.ArdupilotMobilityHandler] solves this 
by integrating with [ArduPilot's SITL (Software In The Loop)](https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html) 
simulator. Each drone in your simulation runs an actual ArduPilot firmware instance, providing:

- **Realistic flight dynamics** — vehicles accelerate, decelerate, and bank through turns like real UAVs
- **Battery simulation** — track battery consumption over the course of a mission
- **Proper startup sequences** — vehicles arm, take off, and navigate to their starting positions before the simulation begins
- **MAVLink protocol** — the same communication protocol used by real vehicles
- **Ground station compatibility** — optionally connect a ground control station (like QGroundControl or Mission Planner) to monitor your simulation

The key insight is that **your protocols don't need to change**. GrADyS-SIM NextGen's handler-agnostic design means 
the same protocol code works with both `MobilityHandler` and `ArdupilotMobilityHandler`. You only change the 
execution setup.

## Prerequisites

!!!danger
    ArdupilotMobilityHandler requires ArduPilot SITL to be installed and built on your machine. The easiest way to
    do this is the `uav-api setup-sitl` command described below.

Before running an Ardupilot-based simulation you need:

1. **ArduPilot SITL** — [UAV API](https://github.com/Project-GrADyS/uav_api), which is installed together with
   GrADyS-SIM NextGen, ships a command that sets up SITL for you. Run it once per machine, as your normal user
   (not root). It asks for your password when it needs sudo:

    ```bash
    uav-api setup-sitl
    source ~/.bashrc
    ```

    It takes several minutes and is safe to re-run, since every step that is already done is skipped. It clones
    ArduPilot into `~/ardupilot`, installs its prerequisites (Debian/Ubuntu only), builds the SITL binaries and
    adds ArduPilot's `Tools/autotest` directory to your `PATH`. Useful options:

    | Option | Description |
    |--------|-------------|
    | `--ardupilot_path` | Where the ArduPilot checkout lives or will be cloned (default `~/ardupilot`) |
    | `--vehicle copter` | Only build the copter binary, which is the one used by ArdupilotMobilityHandler |
    | `--skip_prereqs` | Don't run the prerequisites script (no sudo/apt), if you installed them yourself |

    See the [UAV API documentation](https://github.com/Project-GrADyS/uav_api#setting-up-sitl-setup-sitl) for
    every option. On other systems, follow the
    [official ArduPilot SITL setup documentation](https://ardupilot.org/dev/docs/building-setup-linux.html) instead.

    Once `sim_vehicle.py` is on your `PATH`, you can leave the `ardupilot_path` configuration parameter as `None`.
    Otherwise, point it at your ArduPilot checkout (`~/ardupilot` if you used `setup-sitl`).

2. **Python dependencies** — The following packages are required and included in GrADyS-SIM NextGen's dependencies:
    - `uav-api>=0.3.1` — HTTP interface to ArduPilot SITL
    - `aiohttp>=3.14.3` — Async HTTP client for drone communication
    - `pandas>=2.2.3` — Used for report generation

3. **Available network ports** — Each drone spawns a UAV API process on a sequential port starting from 
   `starting_api_port` (default 8000). Make sure these ports are not in use.

## The data collection scenario

We will reuse the same data collection scenario from [Guide 2](2_simple.md):

- **Sensors** spread around a location, continuously collecting data
- **UAVs** fly between sensors and a ground station, picking up and delivering data packets
- **A ground station** that receives packets from UAVs

The difference is that instead of idealized linear movement, our UAVs will now fly using ArduPilot's realistic 
flight model.

## Adapting the protocols

Since protocols are handler-agnostic, the sensor and ground station protocols remain **identical** to those 
in Guide 2. The only change to the UAV protocol is adjusting the mission waypoints and tolerance for realistic 
flight.

### Adjusting waypoints

Our mission waypoints need to match the physical scale of the scenario. With sensors placed 100 meters from 
the origin, the UAV missions fly between `(0, 0, 10)` (near the ground station) and the sensor location at 
altitude 10 meters.

```py title="Mission waypoints for Ardupilot"
--8<--
docs/Guides/ardupilot example/simple_protocol.py:73:90
--8<--
```

!!!warning
    All positions in GrADyS-SIM use an XYZ coordinate frame. The ArdupilotMobilityHandler automatically converts 
    these to ArduPilot's NED (North-East-Down) frame by negating the Z coordinate. You don't need to handle 
    this conversion yourself.

### Adjusting tolerance

SITL drones have realistic flight characteristics and may not stop exactly at a waypoint. The default 
`MissionMobilityPlugin` tolerance of 0.5 meters is too tight for SITL. We increase it to 10 meters for 
reliable waypoint detection.

```py title="UAV protocol initialization with increased tolerance"
--8<--
docs/Guides/ardupilot example/simple_protocol.py:100:111
--8<--
```

## Configuring the simulation

The main change is in the execution code where we replace `MobilityHandler` with `ArdupilotMobilityHandler`.

### ArdupilotMobilityConfiguration

The handler is configured through 
[ArdupilotMobilityConfiguration][gradysim.simulator.handler.ardupilot_mobility.ArdupilotMobilityConfiguration]. 
Here are the key fields:

```py title="Ardupilot configuration"
--8<--
docs/Guides/ardupilot example/main.py:22:29
--8<--
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `simulate_drones` | `True` | Set to `True` for SITL simulation |
| `ardupilot_path` | `None` | Path to your cloned ArduPilot repository |
| `starting_api_port` | `8000` | Base port for UAV API. Node N uses port `starting_api_port + node_id` |
| `update_rate` | `0.5` | Interval in seconds between telemetry updates |
| `default_speed` | `10` | Default airspeed in m/s |
| `generate_report` | `True` | Generate a CSV report with battery and telemetry statistics |
| `ground_station_ip` | `None` | Optional IP to connect a ground control station (e.g., `"127.0.0.1:14550"`) |
| `uav_api_log_path` | `None` | Optional directory for UAV API log files |
| `simulation_startup_speedup` | `5` | SITL speedup during drone setup, applied when UAV API is spawned. SITL then runs at the simulation's `real_time` factor; capped so `mavlink_streamrate × speedup` ≤ 50 Hz per drone |
| `mavlink_streamrate` | `10` | Rate in Hz of the MAVLink telemetry streams requested from the autopilot (applied when UAV API is spawned). Under SITL the effective rate is multiplied by the SITL speedup |
| `uav_api_startup_timeout` | `120` | Maximum time in seconds a UAV API has to start accepting requests, and each setup step (arm, takeoff, reaching the initial position) has to complete |

### SimulationConfiguration

!!!warning
    `real_time=True` is **required** in `SimulationConfiguration` when using `ArdupilotMobilityHandler`. The
    handler communicates with external SITL processes that run in real time, so the simulation must be 
    synchronized with real-world time.

Since SITL drones fly at realistic speeds, the simulation duration should be longer than with the standard 
`MobilityHandler`. We use 300 seconds here.

```py title="Simulation configuration"
--8<--
docs/Guides/ardupilot example/main.py:15:19
--8<--
```

### Adding nodes

Nodes are added exactly as in the standard simulation. Note that sensors and the ground station are placed 
at their respective positions, while UAVs start at the origin.

```py title="Adding nodes to the simulation"
--8<--
docs/Guides/ardupilot example/main.py:38:51
--8<--
```

!!!warning
    **All nodes** in the simulation are registered with the ArdupilotMobilityHandler, including sensors and 
    the ground station. This means each node spawns its own SITL instance. Nodes that don't issue mobility 
    commands will simply remain stationary, but they still consume resources. In this example with 9 nodes, 
    9 SITL instances will be created. Keep this in mind when sizing your simulation.

### Full execution code

```py title="Complete execution code"
--8<--
docs/Guides/ardupilot example/main.py
--8<--
```

## Coordinate systems

GrADyS-SIM uses an **XYZ** coordinate frame where Z points up. ArduPilot uses **NED** (North-East-Down) where 
the third axis points downward. The handler converts between them automatically by negating the Z coordinate:

- **Simulation frame**: `(x, y, z)` — Z positive means higher altitude
- **ArduPilot NED frame**: `(north, east, down)` — Down positive means lower altitude
- **Conversion**: `NED = (x, y, -z)`

You can also use GPS coordinates with the `GOTO_GEO_COORDS` mobility command. These are passed directly to 
ArduPilot without conversion.

The handler supports the following mobility commands:

| Command | Description |
|---------|-------------|
| `GOTO_COORDS` | Move to XYZ position (automatically converted to NED) |
| `GOTO_GEO_COORDS` | Move to GPS coordinates (latitude, longitude, altitude) |
| `SET_SPEED` | Change the vehicle's airspeed in m/s |
| `STOP` | Stop current movement |

## Running the simulation

To run the simulation, pass the path to your ArduPilot repository as a command-line argument (`~/ardupilot` if
you used `uav-api setup-sitl`):

```bash
python main.py ~/ardupilot
```

### What happens at startup

When the simulation starts, the following sequence occurs for every drone, with all drones starting in parallel:

1. **UAV API process spawns** — Each node gets its own UAV API HTTP server on a sequential port. Its output is
   discarded (set `uav_api_log_console=True` to see it); UAV API still writes its own log file
2. **SITL initializes** — ArduPilot SITL firmware boots up for each vehicle, running at
   `simulation_startup_speedup` to make the setup faster. The handler's requests are retried until UAV API
   answers, for up to `uav_api_startup_timeout` seconds
3. **Arming** — Each vehicle arms its motors
4. **Takeoff** — Vehicles take off to 10 meters altitude
5. **Navigate to start position** — Vehicles fly to their initial XYZ positions
6. **Speedup adjusted** — SITL is set to match the simulation's `real_time` factor
7. **Telemetry starts** — Periodic telemetry updates begin at the configured rate

!!!info
    Startup usually takes from a few seconds to a minute, since each SITL instance needs time to boot and the
    vehicles must physically fly to their starting positions. If a UAV API process dies during startup, the
    handler reports it right away together with the path of its log file.

### Expected console output

During startup the handler reports the progress of every drone:

```
INFO     [ArdupilotMobility] Starting simulated drone 0 (UAV API on port 8000)...
INFO     [ArdupilotMobility] Starting simulated drone 1 (UAV API on port 8001)...
INFO     [ArdupilotMobility] Waiting for 2 drones to reach their initial positions...
INFO     [ArdupilotMobility] Drone 0 ready (UAV API on port 8000, at initial position (0.0, 0.0, 20.0))
INFO     [ArdupilotMobility] Drone 1 ready (UAV API on port 8001, at initial position (100.0, 0.0, 20.0))
INFO     [ArdupilotMobility] All 2 drones initialized
```

Once running, you will see telemetry updates and protocol messages similar to the standard simulation. 
At the end, the handler logs a report and shuts every drone down:

```
INFO     [ArdupilotMobility] Mobility report
  Node  Telemetry updates  Dropped  Drop rate  Battery start  Battery end  Consumed
  ----  -----------------  -------  ---------  -------------  -----------  --------
     0                540       12      2.22%           100%          87%       13%
     1                540        8      1.48%           100%          89%       11%
Report saved to /path/to/ardupilot_mobility_report.csv
INFO     [ArdupilotMobility] Drone 0 shut down
INFO     [ArdupilotMobility] Drone 1 shut down
INFO     [ArdupilotMobility] All 2 drones shut down cleanly
```

## Understanding the report

When `generate_report=True`, the handler outputs a CSV file named `ardupilot_mobility_report.csv` with the 
following columns:

| Column | Description |
|--------|-------------|
| `node_id` | The identifier of the node |
| `telemetry_requests` | Total number of telemetry updates requested |
| `telemetry_drops` | Number of telemetry requests that were skipped because the previous request hadn't completed yet |
| `battery_wasted` | Percentage of battery consumed during the simulation (`initial_battery - final_battery`) |

A high number of **telemetry drops** indicates that the `update_rate` is too fast for the system to keep 
up. Consider increasing the `update_rate` value (longer interval between updates) if you see many drops.

The **battery_wasted** value gives you a measure of the energy cost of your protocol's mobility pattern, 
which can be useful for optimizing flight paths and comparing different strategies.
