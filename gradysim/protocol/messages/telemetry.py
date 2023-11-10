from gradysim.simulator.position import Position


# TODO: Josef, I heavily simplified this class, this will probably change the calls from the OMNeT++
#  side, can you update them?
class Telemetry:
    current_position: Position

    def __init__(
        self,
        current_position: Position
    ):
        self.current_position = current_position
