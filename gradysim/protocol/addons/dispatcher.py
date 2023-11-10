"""
This module contains a function that creates a dispatcher which wraps a protocol instance and it's methods. Implements
 a call chain for each of the protocol interface's methods.

 Use this module through the **create_dispatcher**][gradysim.protocol.addons.dispatcher.create_dispatcher] method,
**never** instantiate the ProtocolWrapper directly.

This module is useful if you want to implement an addon on or some other functionality that relies on overriding the
protocol's methods. Protocols using this addon will still be compatible with all execution modes as only the protocol
itself is tampered with and not any of the layers that allow it to run on different environments.

Beware that this module uses monkey patching and may result in broken protocols if someone else tries to tamper with
the protocol's methods.
"""

import types
from enum import Enum
from typing import Dict, List, Callable

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.telemetry import Telemetry


class DispatchReturn(Enum):
    """
    Return value for the dispatched funcions. INTERRUPT should be returned if your handler completely handled
    the call and it shouldn't be passed forward. CONTINUE should be called if the call should continue down
    the call chain.
    """
    INTERRUPT = 1
    CONTINUE = 2


def _wrap_functionality(protocol: IProtocol, functionality: str, queue: List[Callable]):
    def wrapped_functionality(self: IProtocol, *args, **kwargs):
        for handler in queue:
            result = handler(self, *args, **kwargs)
            if result == DispatchReturn.INTERRUPT:
                break

    queue.append(getattr(protocol, functionality).__func__)

    setattr(protocol, functionality, types.MethodType(wrapped_functionality, protocol))


class ProtocolWrapper:
    """
    Do not use this class directly, instead use
    [create_dispatcher][gradysim.protocol.addons.dispatcher.create_dispatcher].

    Wraps the protocol's calls into a call chain. Instead of going directly to the protocol's methods calls to the
    protocol interface will be passed down a chain of registered handlers. The protocol's own method is at the end
    of the chain. Methods should return a value in the DispatchReturn Enum, INTERRUPT do interrupt the chain and
    CONTINUE if the message should be passed through.
    """
    _protocol: IProtocol

    _handle_initialize_chain: List[Callable[[IProtocol, int], None]]
    _handle_timer_chain: List[Callable[[IProtocol, str], DispatchReturn]]
    _handle_telemetry_chain: List[Callable[[IProtocol, Telemetry], DispatchReturn]]
    _handle_packet_chain: List[Callable[[IProtocol, str], DispatchReturn]]
    _finish_queue_chain: List[Callable[[], None]]

    def __init__(self, protocol: IProtocol):
        """
        Instantiates a protocol wrapper. Should not be instantiated directly, create a dispatcher using the
        [create_dispatcher][gradysim.protocol.addons.dispatcher.create_dispatcher] method.

        **Do not instantiate this class directly**

        Args:
            protocol: Protocol whose calls will be wrapped
        """
        self._protocol = protocol

        self._handle_initialize_chain = []
        self._handle_timer_chain = []
        self._handle_telemetry_chain = []
        self._handle_packet_chain = []
        self._finish_queue_chain = []

        _wrap_functionality(protocol, 'initialize', self._handle_initialize_chain)
        _wrap_functionality(protocol, 'handle_timer', self._handle_timer_chain)
        _wrap_functionality(protocol, 'handle_telemetry', self._handle_telemetry_chain)
        _wrap_functionality(protocol, 'handle_packet', self._handle_packet_chain)
        _wrap_functionality(protocol, 'finish', self._finish_queue_chain)

    def register_initialize(self, handler: Callable[[IProtocol, int], None]) -> None:
        """
        Registers a handler for the [initialize][gradysim.protocol.interface.IProtocol.initialize] method. Handlers should
        have the same signature as the initialize method. DispatcherReturn is not supported for this method, the call
        chain is always followed.

        Args:
            handler: Handler being registered
        """
        self._handle_initialize_chain.insert(0, handler)

    def register_handle_timer(self, handler: Callable[[IProtocol, str], DispatchReturn]) -> None:
        """
        Registers a handler for the [handle_timer][gradysim.protocol.interface.IProtocol.handle_timer] method. Handlers should
        have the same signature as the handle_timer method but return a value in the DispatcherReturn enum.

        Args:
            handler: Handler being registered
        """
        self._handle_timer_chain.insert(0, handler)

    def register_handle_telemetry(self, handler: Callable[[IProtocol, Telemetry], DispatchReturn]) -> None:
        """
        Registers a handler for the [handle_telemetry][gradysim.protocol.interface.IProtocol.handle_telemetry] method. Handlers
        should have the same signature as the handle_telemetry method but return a value in the DispatcherReturn enum.

        Args:
            handler: Handler being registered
        """
        self._handle_telemetry_chain.insert(0, handler)

    def register_handle_packet(self, handler: Callable[[IProtocol, str], DispatchReturn]) -> None:
        """
        Registers a handler for the [handle_packet][gradysim.protocol.interface.IProtocol.handle_packet] method. Handlers should
        have the same signature as the handle_packet method but return a value in the DispatcherReturn enum.

        Args:
            handler: Handler being registered
        """
        self._handle_packet_chain.insert(0, handler)

    def register_finish(self, handler: Callable[[IProtocol], None]) -> None:
        """
        Registers a handler for the [handle_timer][gradysim.protocol.interface.IProtocol.finish] method. Handlers should
        have the same signature as the finish. This method doesn't support returning DispatchReturn values, the
        call chain is always followed.

        Not following this chain, since it is only called once, could result in improper finalization of protocols and
        other handlers.

        Args:
            handler: Handler being registered
        """
        self._finish_queue_chain.insert(0, handler)

    def unregister_initialize(self, handler: Callable[[IProtocol, int], None]) -> None:
        """
        Unregisters a handle_initialize handler. Raises ValueError if handler was not registered

        Args:
            handler: Handler instance being unregistered
        """
        self._handle_initialize_chain.remove(handler)

    def unregister_handle_timer(self, handler: Callable[[IProtocol, str], DispatchReturn]) -> None:
        """
        Unregisters a handle_timer handler. Raises ValueError if handler was not registered

        Args:
            handler: Handler instance being unregistered
        """
        self._handle_timer_chain.remove(handler)

    def unregister_handle_telemetry(self, handler: Callable[[IProtocol, Telemetry], DispatchReturn]) -> None:
        """
        Unregisters a handle_timer handler. Raises ValueError if handler was not registered

        Args:
            handler: Handler instance being unregistered
        """
        self._handle_telemetry_chain.remove(handler)

    def unregister_handle_packet(self, handler: Callable[[IProtocol, str], DispatchReturn]) -> None:
        """
        Unregisters a handle_timer handler. Raises ValueError if handler was not registered

        Args:
            handler: Handler instance being unregistered
        """
        self._handle_packet_chain.remove(handler)

    def unregister_finish(self, handler: Callable[[IProtocol], None]) -> None:
        """
        Unregisters a handle_timer handler. Raises ValueError if handler was not registered

        Args:
            handler: Handler instance being unregistered
        """
        self._finish_queue_chain.remove(handler)


_protocol_wrappers: Dict[IProtocol, ProtocolWrapper] = {}


def create_dispatcher(protocol: IProtocol) -> ProtocolWrapper:
    """
    Creates a dispatcher which wraps a protocol instance and it's methods. Implements a call chain for each of the
    protocol interface's methods. The class returned from this function can be used to add functions to the call chain
    of those wrapped methods. The original method implementation is not lost.

    Is a protocol that was already wrapped is passed as an argument, return the wrapper for that protocol.

    Beware that this module uses monkey patching and may result in broken protocols if someone else tries to tamper with
    the protocol's methods.

    If you want to implement an addon or some other behaviour that requires overriding protocol's
    methods you should use this function

    Args:
        protocol: Protocol being wrapped

    Returns:
        ProtocolWrapper instance that allows methods to be added to the call chain
    """
    global _protocol_wrappers
    if protocol not in _protocol_wrappers:
        _protocol_wrappers[protocol] = ProtocolWrapper(protocol)

    return _protocol_wrappers[protocol]
