import logging

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.plugin.random_mobility import RandomMobilityPlugin, RandomMobilityConfig
from gradysim.simulator.extension.camera import CameraHardware, CameraConfiguration


class PointOfInterest(IProtocol):
    def initialize(self) -> None:
        pass

    def handle_timer(self, timer: str) -> None:
        pass

    def handle_packet(self, message: str) -> None:
        pass

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    def finish(self) -> None:
        pass


class Drone(IProtocol):
    camera: CameraHardware

    def initialize(self) -> None:
        plugin = RandomMobilityPlugin(self, RandomMobilityConfig(x_range=(-50, 50), y_range=(-50, 50), z_range=(10, 10)))
        plugin.initiate_random_trip()

        self.provider.schedule_timer("", self.provider.current_time())

        configuration = CameraConfiguration(
            20, # Reach of the camera
            30, # Angle of the cone
            180, # Facing elevation - facing downwards
            0 # Facing rotation
        )
        self.camera = CameraHardware(self, configuration)

    def handle_timer(self, timer: str) -> None:
        detected = self.camera.take_picture()
        logging.info(f"Detected {len(detected)} points of interest")
        self.provider.schedule_timer("", self.provider.current_time() + 5)

    def handle_packet(self, message: str) -> None:
        pass

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    def finish(self) -> None:
        pass