import time
import unittest

from alab_management.utils.thread_ops import TaskThread


class TestThreadOps(unittest.TestCase):
    def test_terminate_thread(self):
        def _run():
            nonlocal flag
            time.sleep(10)
            flag = True

        flag = False
        t = TaskThread(target=_run)
        t.start()
        time.sleep(0.1)
        start = time.perf_counter()
        t.terminate()
        t.join()
        self.assertFalse(flag)
        end = time.perf_counter()

        self.assertAlmostEqual(0, end - start, delta=2)

    def test_terminate_hook(self):
        flag = False

        def _run():
            nonlocal flag
            flag = True
            time.sleep(10)
            flag = False

        def _on_terminate():
            nonlocal flag
            flag = False

        t = TaskThread(target=_run)
        t.register_terminate_hook(_on_terminate)
        t.start()
        time.sleep(0.1)
        start = time.perf_counter()
        t.terminate()
        t.join()
        self.assertFalse(flag)
        end = time.perf_counter()
        self.assertAlmostEqual(0, end - start, delta=2)
