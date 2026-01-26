"""
Mobility handlers introduce mobility to nodes in the simulation. Different mobility handlers can implement
different mobility models, from simple static nodes to complex models that simulate real-world movement patterns.
They are responsible for updating the position of nodes based on mobility commands received from protocols
and for sending updated position telemetry back to the protocols.
"""


from .massless import MasslessMobilityConfiguration, MasslessMobilityHandler, MasslessMobilityException
from .intertial import InertialMobilityConfiguration, InertialMobilityHandler

# The MasslessMobility classes were at one point the only mobility classes available and were named
# simply Mobility*. To maintain backwards compatibility with past versions, we alias their names here.
MobilityConfiguration = MasslessMobilityConfiguration
MobilityHandler = MasslessMobilityHandler
MobilityException = MasslessMobilityException

__all__ = [
    "MobilityException",

    "MasslessMobilityException",
    "MobilityHandler",
    "MasslessMobilityHandler",
    "MobilityConfiguration",
    "MasslessMobilityConfiguration",

    "InertialMobilityHandler",
    "InertialMobilityConfiguration",
]
