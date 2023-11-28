from gradysim.simulator.handler.communication import CommunicationHandler, CommunicationMedium
from gradysim.simulator.handler.mobility import MobilityHandler
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.handler.visualization import VisualizationHandler
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration, PositionScheme
from protocol_sensor import ZigZagProtocolSensor
from protocol_mobile import ZigZagProtocolMobile


def run_simulation(real_time: bool):
    builder = SimulationBuilder(SimulationConfiguration(duration=180, debug=True, real_time=real_time))
    builder.add_handler(CommunicationHandler(CommunicationMedium(transmission_range=50)))
    builder.add_handler(TimerHandler())
    builder.add_handler(MobilityHandler())

    if real_time:
        builder.add_handler(VisualizationHandler())

    # Drone locations 
    builder.add_node(ZigZagProtocolMobile, (-23.0, 0.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (-13.0, -10.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (-13.0, 10.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (-3.0, -20.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (-3.0, 20.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (7.0, -20.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (7.0, 0.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (7.0, 20.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (17.0, -20.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (17.0, 20.0, 0.0))
    
    # Sensor locations 
    builder.add_node(ZigZagProtocolSensor, (-23.0, 0.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (-13.0, -10.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (-13.0, 10.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (-3.0, -20.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (-3.0, 20.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (7.0, -20.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (7.0, 0.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (7.0, 20.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (17.0, -20.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (17.0, 20.0, 0.0))
    
    # Simulation
    simulation = builder.build()
    simulation.start_simulation()


if __name__ == '__main__':
    run_simulation(True)