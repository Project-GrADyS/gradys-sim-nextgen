from typing import List

from gradysim.simulator.handler.assertion import assert_always_true_for_simulation, AssertionHandler
from gradysim.simulator.handler.communication import CommunicationHandler
from gradysim.simulator.handler.mobility import MobilityHandler
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.handler.visualization import VisualizationHandler
from gradysim.simulator.node import Node
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration
from ping import PingProtocol


@assert_always_true_for_simulation(name="received_equals_sent")
def assert_received_equals_sent(nodes: List[Node[PingProtocol]]) -> bool:
    received = 0
    sent = 0
    for node in nodes:
        received += node.protocol_encapsulator.protocol.received
        sent += node.protocol_encapsulator.protocol.received
    return received == sent


def run_simulation(real_time: bool):
    builder = SimulationBuilder(SimulationConfiguration(duration=30, debug=True, real_time=real_time))
    builder.add_handler(CommunicationHandler())
    builder.add_handler(TimerHandler())
    builder.add_handler(MobilityHandler())
    if real_time:
        builder.add_handler(VisualizationHandler())
    builder.add_handler(AssertionHandler([assert_received_equals_sent]))

    builder.add_node(PingProtocol, (0, 0, 0))
    builder.add_node(PingProtocol, (1, 1, 0))

    simulation = builder.build()
    simulation.start_simulation()


if __name__ == '__main__':
    run_simulation(True)
