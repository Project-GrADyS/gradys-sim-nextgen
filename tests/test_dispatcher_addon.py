import unittest

from gradysim.protocol.addons.dispatcher import create_dispatcher, DispatchReturn
from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.telemetry import Telemetry


class DispatchAddonTestCase(unittest.TestCase):
    def test_dispatcher_still_calls_default(self):
        class DummyProtocol(IProtocol):
            variable: int

            def __init__(self):
                self.variable = 0

            def initialize(self, stage: int):
                self.variable += 1

            def handle_timer(self, timer: str):
                self.variable += 1

            def handle_packet(self, message: str):
                self.variable += 1

            def handle_telemetry(self, telemetry: str):
                self.variable += 1

            def finish(self):
                self.variable += 1

        protocol = DummyProtocol()
        create_dispatcher(protocol)
        protocol.initialize(0)
        self.assertEqual(protocol.variable, 1)
        protocol.handle_timer("timer")
        self.assertEqual(protocol.variable, 2)
        protocol.handle_packet("packet")
        self.assertEqual(protocol.variable, 3)
        protocol.handle_telemetry("telemetry")
        self.assertEqual(protocol.variable, 4)
        protocol.finish()
        self.assertEqual(protocol.variable, 5)

    def test_dispatcher_registers_calls(self):
        class DummyProtocol(IProtocol):
            variable: int

            def __init__(self):
                self.variable = 0

            def initialize(self, stage: int):
                self.variable += 1

            def handle_timer(self, timer: str):
                self.variable += 1

            def handle_packet(self, message: str):
                self.variable += 1

            def handle_telemetry(self, telemetry: str):
                self.variable += 1

            def finish(self):
                self.variable += 1

        protocol = DummyProtocol()
        dispatcher = create_dispatcher(protocol)

        counter = 0

        def initialize(_instance: IProtocol, stage: int):
            nonlocal counter
            counter += 1

        def handle_timer(_instance: IProtocol, timer: str):
            nonlocal counter
            counter += 1
            return DispatchReturn.CONTINUE

        def handle_packet(_instance: IProtocol, message: str):
            nonlocal counter
            counter += 1
            return DispatchReturn.CONTINUE

        def handle_telemetry(_instance: IProtocol, telemetry: Telemetry):
            nonlocal counter
            counter += 1
            return DispatchReturn.CONTINUE

        def finish(_instance: IProtocol):
            nonlocal counter
            counter += 1

        dispatcher.register_initialize(initialize)
        dispatcher.register_handle_timer(handle_timer)
        dispatcher.register_handle_packet(handle_packet)
        dispatcher.register_handle_telemetry(handle_telemetry)
        dispatcher.register_finish(finish)

        protocol.initialize(0)
        self.assertEqual(protocol.variable, 1)
        self.assertEqual(counter, 1)

        protocol.handle_timer("timer")
        self.assertEqual(protocol.variable, 2)
        self.assertEqual(counter, 2)

        protocol.handle_packet("packet")
        self.assertEqual(protocol.variable, 3)
        self.assertEqual(counter, 3)

        protocol.handle_telemetry("telemetry")
        self.assertEqual(protocol.variable, 4)
        self.assertEqual(counter, 4)

        protocol.finish()
        self.assertEqual(protocol.variable, 5)
        self.assertEqual(counter, 5)

    def test_dispatcher_unregisters_calls(self):
        class DummyProtocol(IProtocol):
            variable: int

            def __init__(self):
                self.variable = 0

            def initialize(self, stage: int):
                self.variable += 1

            def handle_timer(self, timer: str):
                self.variable += 1

            def handle_packet(self, message: str):
                self.variable += 1

            def handle_telemetry(self, telemetry: str):
                self.variable += 1

            def finish(self):
                self.variable += 1

        protocol = DummyProtocol()
        dispatcher = create_dispatcher(protocol)

        counter = 0

        def initialize(_instance: IProtocol, stage: int):
            nonlocal counter
            counter += 1

        def handle_timer(_instance: IProtocol, timer: str):
            nonlocal counter
            counter += 1
            return DispatchReturn.CONTINUE

        def handle_packet(_instance: IProtocol, message: str):
            nonlocal counter
            counter += 1
            return DispatchReturn.CONTINUE

        def handle_telemetry(_instance: IProtocol, telemetry: Telemetry):
            nonlocal counter
            counter += 1
            return DispatchReturn.CONTINUE

        def finish(_instance: IProtocol):
            nonlocal counter
            counter += 1

        dispatcher.register_initialize(initialize)
        dispatcher.register_handle_timer(handle_timer)
        dispatcher.register_handle_packet(handle_packet)
        dispatcher.register_handle_telemetry(handle_telemetry)
        dispatcher.register_finish(finish)

        dispatcher.unregister_initialize(initialize)
        dispatcher.unregister_handle_timer(handle_timer)
        dispatcher.unregister_handle_packet(handle_packet)
        dispatcher.unregister_handle_telemetry(handle_telemetry)
        dispatcher.unregister_finish(finish)

        protocol.initialize(0)
        self.assertEqual(protocol.variable, 1)
        self.assertEqual(counter, 0)

        protocol.handle_timer("timer")
        self.assertEqual(protocol.variable, 2)
        self.assertEqual(counter, 0)

        protocol.handle_packet("packet")
        self.assertEqual(protocol.variable, 3)
        self.assertEqual(counter, 0)

        protocol.handle_telemetry("telemetry")
        self.assertEqual(protocol.variable, 4)
        self.assertEqual(counter, 0)

        protocol.finish()
        self.assertEqual(protocol.variable, 5)
        self.assertEqual(counter, 0)

    def test_dispatcher_stops_on_return_interrupt(self):
        class DummyProtocol(IProtocol):
            variable: int

            def __init__(self):
                self.variable = 0

            def initialize(self, stage: int):
                self.variable += 1

            def handle_timer(self, timer: str):
                self.variable += 1

            def handle_packet(self, message: str):
                self.variable += 1

            def handle_telemetry(self, telemetry: str):
                self.variable += 1

            def finish(self):
                self.variable += 1

        protocol = DummyProtocol()
        dispatcher = create_dispatcher(protocol)

        counter = 0

        def initialize(_instance: IProtocol, stage: int):
            nonlocal counter
            counter += 1

        def handle_timer(_instance: IProtocol, timer: str):
            nonlocal counter
            counter += 1
            return DispatchReturn.INTERRUPT

        def handle_packet(_instance: IProtocol, message: str):
            nonlocal counter
            counter += 1
            return DispatchReturn.INTERRUPT

        def handle_telemetry(_instance: IProtocol, telemetry: Telemetry):
            nonlocal counter
            counter += 1
            return DispatchReturn.INTERRUPT

        def finish(_instance: IProtocol):
            nonlocal counter
            counter += 1

        dispatcher.register_initialize(initialize)
        dispatcher.register_handle_timer(handle_timer)
        dispatcher.register_handle_packet(handle_packet)
        dispatcher.register_handle_telemetry(handle_telemetry)
        dispatcher.register_finish(finish)

        protocol.initialize(0)
        self.assertEqual(protocol.variable, 1)
        self.assertEqual(counter, 1)

        protocol.handle_timer("timer")
        self.assertEqual(protocol.variable, 1)
        self.assertEqual(counter, 2)

        protocol.handle_packet("packet")
        self.assertEqual(protocol.variable, 1)
        self.assertEqual(counter, 3)

        protocol.handle_telemetry("telemetry")
        self.assertEqual(protocol.variable, 1)
        self.assertEqual(counter, 4)

        protocol.finish()
        self.assertEqual(protocol.variable, 2)
        self.assertEqual(counter, 5)