import importlib
import os.path
import pathlib
import sys
from pathlib import Path

import pytest

from gradysim.simulator import simulation


class SetupAsLocal:
    def __init__(self, path_from_root: pathlib.Path):
        current_path = Path(os.path.abspath(__file__))
        self.path = str(current_path.parent.parent.parent.joinpath(path_from_root))

    def __enter__(self):
        sys.path.append(self.path)

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        sys.path.remove(self.path)


_FORCE_FAST_EXECUTION = True


@pytest.mark.parametrize("sample_path, main_script", [
    ('showcases/follow-mobility', 'main'),
    ('showcases/ping-pong', 'main'),
    ('showcases/ping-pong', 'main_stepped'),
    ('docs/Guides/counter example/1', 'counter_execution'),
    ('docs/Guides/counter example/2', 'counter_execution'),
    ('docs/Guides/counter example/3', 'counter_execution'),
    ('docs/Guides/counter example/4', 'counter_execution'),
    ('docs/Guides/counter example/5', 'counter_execution'),
    ('docs/Guides/counter example/6', 'counter_execution'),
    ('docs/Guides/simple example/', 'main'),
    ('docs/Guides/camera example/', 'main')
])
def test_sample(sample_path: str, main_script: str):
    with simulation._ForceFastExecution():
        with SetupAsLocal(pathlib.Path(sample_path)):
            module = importlib.import_module(main_script)
            module.main()
            assert True
