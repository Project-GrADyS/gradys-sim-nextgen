import warnings
from typing import Optional

from gradysim.encapsulator.python import PythonProvider
from gradysim.protocol.interface import IProtocol


class Extension:
    """
    Base class for all extensions. Extensions are classes that can be used to extend the functionality of the simulation
    environment. They are designed to be used by protocols to interact with the simulation environment in a more
    sophisticated way.
    """

    _provider: Optional[PythonProvider]

    def __init__(self, protocol: IProtocol):
        provider = protocol.provider

        if protocol.provider is None:
            raise ReferenceError("Protocol provider is not initialized. Make sure you are not creating this extension "
                                 "before the protocol's initialize method is called.")

        if not isinstance(provider, PythonProvider):
            warnings.warn("Extensions can only be ran in a python simulation environment. "
                          "Every functionality in this extension will be a no-op.")
            self._provider = None
        else:
            self._provider = provider