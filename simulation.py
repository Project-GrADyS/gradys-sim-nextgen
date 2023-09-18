from simulator.encapsulator.interop import InteropEncapsulator
from simulator.protocols.simple.protocol_mobile import SimpleProtocolMobile


def create_node():
    encapsulator = InteropEncapsulator()
    encapsulator.encapsulate(SimpleProtocolMobile)
    return encapsulator
