import os.path
import sys
import unittest
from pathlib import Path


class TestShowcases(unittest.TestCase):
    def setup_showcase(self, relative_path):
        current_path = Path(os.path.abspath(__file__))
        showcase_path = current_path.joinpath(relative_path)
        sys.path.append(str(showcase_path))

    def test_ping(self):
        sys.path.append("")