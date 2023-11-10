import unittest

from gradysim.simulator.event import EventLoop, EventLoopException


class TestEventLoop(unittest.TestCase):
    def test_length(self):
        ev_loop = EventLoop()
        ev_loop.schedule_event(1, lambda: 0)
        self.assertEqual(len(ev_loop), 1)
        ev_loop.schedule_event(1, lambda: 0)
        self.assertEqual(len(ev_loop), 2)
        ev_loop.pop_event()
        self.assertEqual(len(ev_loop), 1)
        ev_loop.pop_event()
        self.assertEqual(len(ev_loop), 0)

    def test_scheduling_popping(self):
        ev_loop = EventLoop()

        def callback():
            pass

        ev_loop.schedule_event(1, callback)
        event = ev_loop.pop_event()
        self.assertEqual(event.timestamp, 1)
        self.assertEqual(event.callback, callback)

    def test_invalid_scheduling(self):
        ev_loop = EventLoop()
        with self.assertRaises(EventLoopException):
            ev_loop.schedule_event(-1, lambda: 0)

    def test_invalid_popping(self):
        ev_loop = EventLoop()
        with self.assertRaises(EventLoopException):
            ev_loop.pop_event()

    def test_time_updating(self):
        ev_loop = EventLoop()
        ev_loop.schedule_event(10, lambda: 0)
        self.assertEqual(ev_loop.current_time, 0)
        ev_loop.pop_event()
        self.assertEqual(ev_loop.current_time, 10)

    def test_event_sorting(self):
        ev_loop = EventLoop()
        ev_loop.schedule_event(10, lambda: 0)
        ev_loop.schedule_event(1, lambda: 0)
        ev_loop.schedule_event(4, lambda: 0)
        ev_loop.schedule_event(5, lambda: 0)

        self.assertEqual(ev_loop.pop_event().timestamp, 1)
        self.assertEqual(ev_loop.pop_event().timestamp, 4)
        self.assertEqual(ev_loop.pop_event().timestamp, 5)
        self.assertEqual(ev_loop.pop_event().timestamp, 10)
