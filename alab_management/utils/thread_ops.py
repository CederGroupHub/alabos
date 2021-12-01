import ctypes
import sys
import threading


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
        exctype = type(exctype)
    ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype)).value
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

    def terminate(self):
        stop_thread(self)
