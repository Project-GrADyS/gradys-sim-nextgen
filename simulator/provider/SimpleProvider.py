from simulator.messages.CommunicationCommand import CommunicationCommand
from simulator.messages.MobilityCommand import MobilityCommand
from simulator.provider.IProvider import IProvider


class SimpleProvider(IProvider):
    def send_communication_command(self, command: CommunicationCommand):
        pass

    def send_mobility_command(self, command: MobilityCommand):
        pass

    def schedule_timer(self, timer: dict, timestamp: float):
        pass

    def current_time(self) -> int:
        pass
