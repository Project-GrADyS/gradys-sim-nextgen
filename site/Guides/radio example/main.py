from __future__ import annotations

import logging

from gradysim.simulator.simulation import SimulationBuilder
from gradysim.simulator.handler.communication import CommunicationHandler
from gradysim.protocol.position import Position

from radio_protocol import RadioProtocol


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    builder = SimulationBuilder()

    # Three nodes in a line: 0 at origin, 1 at 5m (in short range), 2 at 50m (out of short range)
    positions: list[Position] = [
        (0.0, 0.0, 0.0),  # Node 0
        (5.0, 0.0, 0.0),  # Node 1 – should get short broadcast
        (50.0, 0.0, 0.0),  # Node 2 – outside short, inside long and provider default
    ]

    for pos in positions:
        builder.add_node(RadioProtocol, pos)

    builder.add_handler(CommunicationHandler())

    sim = builder.build()
    sim.start_simulation()


if __name__ == "__main__":
    main()
