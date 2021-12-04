import ctypes
import sys
import threading
import time
from typing import Optional, Callable, Tuple, Any, Dict

_sleep = time.sleep


def _patched_sleep(sec: float):
    """
    A workaround for stoppable thread, as the thread
    cannot detect SystemExit exception when executing time.sleep

    The behavior of ``time.sleep`` with not change in main thread. But in child thread,
    it will sleep 1 sec until reaching the set ``sec``
    """
    if sec <= 1 or threading.current_thread() is threading.main_thread():
        _sleep(sec)

    sec_i = int(sec)
    sec_f = sec - sec_i

    for _ in range(sec_i):
        _sleep(1)

    _sleep(sec_f)


if _sleep is not _patched_sleep:
    time.sleep = _patched_sleep


def _async_raise(tid, exctype):
    """
    Raises the exception in a thread
    """
    if ctypes.pythonapi.Py_IsInitialized() == 0:
        raise SystemError("_async_raise can only be called after interpreter initialized.")
    if sys.version_info >= (3, 7):
        tid = ctypes.c_ulong(tid)
    else:
        tid = ctypes.c_long(tid)
    if not isinstance(exctype, type):
        raise ValueError(f"exctype should be a type, but get instance of {type(exctype)}.")
    ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if ret == 0:
        raise ValueError("Invalid thread id")
    if ret != 1:
        # if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread: threading.Thread):
    _async_raise(thread.ident, SystemExit)


class TaskThread(threading.Thread):
    """
    A stoppable thread, which can be used to hold a task object
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._terminate_hook: Optional[Callable[[], None]] = None

    def register_terminate_hook(self, hook: Callable[..., None], args: Tuple[Any] = tuple(),
                                kwargs: Optional[Dict[str, Any]] = None):
        if kwargs is None:
            kwargs = {}

        self._terminate_hook = lambda: hook(*args, **kwargs)

    def run(self) -> None:
        try:
            super().run()
        except SystemExit:
            pass

    def terminate(self):
        """
        Stop the threading

        If there is a terminate hook registered, call that hook function before exiting.
        """
        if self._terminate_hook is not None:
            self._terminate_hook()

        stop_thread(self)
