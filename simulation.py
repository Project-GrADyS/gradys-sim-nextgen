from simulator.encapsulator.interop import InteropEncapsulator
from simulator.protocols.simple.protocol_mobile import SimpleProtocolMobile


def create_node():
    return InteropEncapsulator.encapsulate(SimpleProtocolMobile)
