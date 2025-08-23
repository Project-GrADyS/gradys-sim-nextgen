# This is an example file to test the RAFT protocol
# It creates 40 nodes at random positions on the ground level
# and executes consensus among them


# Import the necessary Gradysim libraries, the protocol of the nodes and other necessary libraries
from gradysim.simulator.handler.communication import CommunicationHandler, CommunicationMedium
from gradysim.simulator.handler.mobility import MobilityHandler, MobilityConfiguration
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.handler.visualization import VisualizationHandler, VisualizationConfiguration
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration
from protocol import RaftProtocol
import winsound
import random

# Main function to execute the simulation
def main():

    # Simulation parameters
    duration = 10 # Simulation duration in seconds
    debug = False # Simulation debug mode
    real_time = True # Simulation real time mode
    builder = SimulationBuilder(SimulationConfiguration(duration=duration, debug=debug, real_time=real_time))

    # Add the communication handler
    transmission_range = 200 # Communication transmission range in meters
    delay = 0.0 # Communication delay in seconds
    failure_rate = 0.0 # Communication failure rate in percentage
    medium = CommunicationMedium(transmission_range=transmission_range, delay=delay, failure_rate=failure_rate)
    builder.add_handler(CommunicationHandler(medium))

    # Add the timer handler
    builder.add_handler(TimerHandler())

    # Add the mobility handler
    update_rate = 0.01 # Mobility update rate in seconds
    builder.add_handler(MobilityHandler(MobilityConfiguration(update_rate=update_rate)))

    # Add the visualization handler
    open_browser = True # Visualization open browser - True: open browser, False: do not open browser
    builder.add_handler(VisualizationHandler(VisualizationConfiguration(open_browser=open_browser, )))

    # Define node positions for 4 clusters (10 nodes each)
    cluster_positions = [
        # Cluster 1: Top-left quadrant (-30 to -50, 30 to 50)
        ((-50, 50), (-50, 50)),
        # Cluster 2: Top-right quadrant (30 to 50, 30 to 50)  
        ((-50, 50), (-50, 50)),
        # Cluster 3: Bottom-left quadrant (-30 to -50, -30 to -50)
        ((-50, 50), (-50, 50)),
        # Cluster 4: Bottom-right quadrant (30 to 50, -30 to -50)
        ((-50, 50), (-50, 50))
    ]
    
    # Add 40 nodes distributed across 4 clusters
    nodes_per_cluster = 10
    for cluster_idx, ((x_min, x_max), (y_min, y_max)) in enumerate(cluster_positions):
        start_idx = cluster_idx * nodes_per_cluster
        end_idx = start_idx + nodes_per_cluster
        
        for i in range(start_idx, end_idx):
            x = random.uniform(x_min, x_max)
            y = random.uniform(y_min, y_max)
            builder.add_node(RaftProtocol, (x, y, 0))

    simulation = builder.build()
    simulation.start_simulation()

    # Beep when the simulation ends
    winsound.Beep(1000, 2000)

if __name__ == "__main__":
    main() 