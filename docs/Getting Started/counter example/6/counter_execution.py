import math

from counter_protocol import CounterProtocol
from simulator.node.handler.assertion import assert_always_true_for_protocol, AssertionHandler
from simulator.node.handler.communication import CommunicationHandler
from simulator.node.handler.mobility import MobilityHandler
from simulator.node.handler.timer import TimerHandler
from simulator.node.node import Node
from simulator.simulation import SimulationBuilder, SimulationConfiguration

# Trying a much larger simulator to illustrate a scenario
# where visual evaluation would be hard
config = SimulationConfiguration(
    duration=10000
)
builder = SimulationBuilder(config)

for _ in range(10):
    builder.add_node(CounterProtocol, (0, 0, 0))

builder.add_handler(TimerHandler())
builder.add_handler(CommunicationHandler())
builder.add_handler(MobilityHandler())


# Creating an assertion that checks if the number of received
# messages is plausible. Since nodes send a message very second
# it can't possibly be larger than 9 times the current time.
@assert_always_true_for_protocol(CounterProtocol,
                                 name="received_is_plausible",
                                 description="The received messages can't possibly be "
                                             "bigger than 9 * current_time")
def assert_received_is_plausible(node: Node[CounterProtocol]):
    protocol_instance = node.protocol_encapsulator.protocol
    current_time = protocol_instance.provider.current_time()
    received = protocol_instance.received
    return received <= math.floor(current_time) * 9


# Adding an assertion handler, it receives all the desired
# assertions as parameters.
builder.add_handler(AssertionHandler([assert_received_is_plausible]))

simulation = builder.build()
simulation.start_simulation()
