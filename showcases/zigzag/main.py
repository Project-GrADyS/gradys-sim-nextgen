from gradysim.simulator.handler.communication import CommunicationHandler, CommunicationMedium
from gradysim.simulator.handler.mobility import MobilityHandler
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.handler.visualization import VisualizationHandler
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration
from protocol_sensor import ZigZagProtocolSensor
from protocol_mobile import ZigZagProtocolMobile
from protocol_sensor import ZigZagProtocolSensor


def run_simulation(real_time: bool):
    builder = SimulationBuilder(SimulationConfiguration(duration=180, debug=True, real_time=real_time))
    builder.add_handler(CommunicationHandler(CommunicationMedium(transmission_range=50)))
    builder.add_handler(TimerHandler())
    builder.add_handler(MobilityHandler())

    if real_time:
        builder.add_handler(VisualizationHandler())

    builder.add_node(ZigZagProtocolSensor, (-6.9, 0.0, 0.0))
    
    # Drone locations 
    builder.add_node(ZigZagProtocolMobile, (-6.9, 0.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (-3.9000000000000004, -3.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (-3.9000000000000004, 3.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (-0.9000000000000004, -6.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (-0.9000000000000004, 6.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (2.0999999999999996, -6.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (2.0999999999999996, 0.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (2.0999999999999996, 6.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (5.1, -6.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (5.1, 6.0, 0.0))
    
    # Sensor locations 
    builder.add_node(ZigZagProtocolSensor, (-3.9000000000000004, -3.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (-3.9000000000000004, 3.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (-0.9000000000000004, -6.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (-0.9000000000000004, 6.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (2.0999999999999996, -6.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (2.0999999999999996, 0.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (2.0999999999999996, 6.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (5.1, -6.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (5.1, 6.0, 0.0))
    
    # Simulation
    simulation = builder.build()
    simulation.start_simulation()


if __name__ == '__main__':
    run_simulation(True)
