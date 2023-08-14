from simulator.encapsulator.InteropEncapsulator import InteropEncapsulator
from simulator.protocols.simple.SimpleProtocolMobile import SimpleProtocolMobile


def create_node():
    return InteropEncapsulator.encapsulate(SimpleProtocolMobile)
