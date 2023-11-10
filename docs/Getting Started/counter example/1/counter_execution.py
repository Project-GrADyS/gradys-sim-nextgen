from gradysim.simulator import TimerHandler
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration
from counter_protocol import CounterProtocol

# Configuring the simulator. The only option that interests us
# is limiting the simulator to 10 real-world seconds.
config = SimulationConfiguration(
    duration=10
)
# Instantiating the simulator builder with the created config
builder = SimulationBuilder(config)

# Calling the add_node function we create a network node that
# will run the CounterProtocol we created. 
builder.add_node(CounterProtocol, (0, 0, 0))

# Handlers enable certain simulator features. In the case of our
# simulator all we really need is a timer.
builder.add_handler(TimerHandler())

# Calling the build functions creates a simulator from the previously
# specified options.
simulation = builder.build()

# The start_simulation() method will run the simulator until our 10-second
# limit is reached.
simulation.start_simulation()

