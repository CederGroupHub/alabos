import multiprocessing
from typing import Callable, Optional, Tuple, Any, Dict


class TaskProcess(multiprocessing.Process):
    """
    A process class with terminate callback
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._terminate_callback: Optional[Callable[..., None]] = None
        self._terminate_args: Tuple[Any] = tuple()
        self._terminate_kwargs: Dict[str, Any] = {}

    def register_terminate_callback(self, f: Callable[..., None], args: Tuple[Any] = tuple(),
                                    kwargs: Optional[Dict[str, Any]] = None):
        if kwargs is None:
            kwargs = {}
        self._terminate_callback = f
        self._terminate_args = args
        self._terminate_kwargs = kwargs

    def terminate(self) -> None:
        if self._terminate_callback is not None:
            self._terminate_callback(*self._terminate_args, **self._terminate_kwargs)
        super().terminate()
