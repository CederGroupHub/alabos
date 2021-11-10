import os
from pathlib import Path
from unittest import TestCase

os.environ["ALAB_CONFIG"] = (Path(__file__).parent.parent /
                             "examples" / "fake_lab" / "config.toml").as_posix()

from alab_management import TaskView
from alab_management.scripts import setup_lab


class TestTaskView(TestCase):
    def setUp(self) -> None:
        setup_lab()
        self.task_view = TaskView()

    def tearDown(self) -> None:
        self.task_view._task_collection.drop()
