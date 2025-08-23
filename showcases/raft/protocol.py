import logging

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.plugin.raft import RaftConfig, RaftMode, RaftConsensus


class RaftProtocol(IProtocol):
    def initialize(self):
        # We initialize our counter at zero
        self.counter = 0

        self.node_id = self.provider.get_id()

        # Use the adapter to schedule timer for election monitoring
        self.provider.schedule_timer(
            "counter_timer",  # Timer name
            1000  # 1000 milliseconds = 1 second
        )

        # Use the adapter to schedule timer for failure simulation
        self.provider.schedule_timer(
            "failure_simulation_timer",  # Timer name
            3000  # 3000 milliseconds = 3 seconds
        )

        # Use the adapter to schedule timer for recovery simulation
        self.provider.schedule_timer(
            "recovery_simulation_timer",  # Timer name
            7000  # 7000 milliseconds = 7 seconds
        )

        # Create configuration
        config = RaftConfig()
        config.set_election_timeout(150, 300)  # 150-300ms
        config.set_heartbeat_interval(50)      # 50ms (aumentado para respeitar timeout mínimo)
        config.add_consensus_variable("v_int", int)
        config.set_logging(enable=True, level="INFO")
            
        # For testing instability issues, try CLASSIC mode to see standard Raft behavior
        #config.set_raft_mode(RaftMode.CLASSIC)  # Use classic Raft mode for testing
        config.set_raft_mode(RaftMode.FAULT_TOLERANT)  # Use fault-tolerant Raft mode (current behavior)

        # Configure failure detection parameters if RaftMode is FAULT_TOLERANT
        failure_config = config.get_failure_config()
        failure_config.set_failure_threshold(2)      # 2 failed heartbeats to mark as failed
        failure_config.set_recovery_threshold(3)     # 3 successful heartbeats to recover
        failure_config.set_detection_interval(2)     # Check every 2 heartbeats
        failure_config.set_heartbeat_timeout(4)      # 4× heartbeat_interval = 200ms timeout

        # Create the Raft consensus instance
        self.consensus = RaftConsensus(
            config=config,
            protocol=self
        )

        # Set known nodes and start consensus
        total_nodes = 40  # 40 nós conhecidos
        known_nodes = list(range(total_nodes))
        self.consensus.set_known_nodes(known_nodes)
        self.consensus.start()

    def handle_timer(self, timer: str):
        # Handle user specific timers
        if timer == "counter_timer":
            self.counter += 1
            # Schedule next monitoring
            self.provider.schedule_timer("counter_timer", 1000)

        if timer == "failure_simulation_timer":
            inactive_nodes = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
            #inactive_nodes = []
            for node in inactive_nodes:
                self.consensus.set_simulation_active(node, False)

        if timer == "recovery_simulation_timer":
            recovery_nodes = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
            #recovery_nodes = []
            for node in recovery_nodes:
                self.consensus.set_simulation_active(node, True)

    def handle_packet(self, message: str):
        pass

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        # Update position in adapter
        #position = self.adapter.get_node_position(telemetry)
        
        # If this node is leader, propose a value occasionally
        if self.consensus and self.consensus.is_leader():
            if self.counter % 2 == 0:  # Every 5 iterations
                self.consensus.propose_value("v_int", 1)
                
        # paint the node according to its state
        if self.consensus.is_leader():
            self.consensus.adapter.paint_node("green", self.node_id)
        elif self.consensus.is_simulation_active(self.node_id):
            self.consensus.adapter.paint_node("blue", self.node_id)
        else:
            self.consensus.adapter.paint_node("red", self.node_id)

    def finish(self):
        # print the counter
        logging.info(f"Counter: {self.counter}")
        
        if self.consensus:
            # Stop consensus
            self.consensus.stop()