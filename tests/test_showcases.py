import os.path
import sys
import unittest
from pathlib import Path


class TestShowcases(unittest.TestCase):
    def setup_showcase(self, showcase_path):
        current_path = Path(os.path.abspath(__file__))
        showcase_path = current_path.parent.parent.joinpath("showcases").joinpath(showcase_path)
        print(showcase_path)
        sys.path.append(str(showcase_path))

    def test_ping_pong(self):
        self.setup_showcase("ping-pong")
        from main import run_simulation
        run_simulation(False)

    def test_follow_mobility(self):
        self.setup_showcase("follow-mobility")
        from main import run_simulation
        run_simulation(False)

    # TODO: Add simple showcase here