from protocol.messages.communication import CommunicationCommand
from protocol.messages.mobility import MobilityCommand
from protocol.provider import IProvider


class SimpleProvider(IProvider):
    def send_communication_command(self, command: CommunicationCommand):
        pass

    def send_mobility_command(self, command: MobilityCommand):
        pass

    def schedule_timer(self, timer: str, timestamp: float):
        pass

    def current_time(self) -> int:
        pass
