"""The script to launch task_view and executor, which are the core of the system."""

import contextlib
import importlib
import multiprocessing
import sys
import time

from gevent.pywsgi import WSGIServer  # type: ignore

import alab_management.dashboard
from alab_management.utils.versioning import get_version

with contextlib.suppress(RuntimeError):
    multiprocessing.set_start_method("spawn")

# Create a global termination event
termination_event = multiprocessing.Event()


class RestartableProcess:
    """A class for creating processes that can be automatically restarted after failures."""

    def __init__(self, target, args=(), termination_event=None):
        self.target = target
        self.process = None
        self.args = args
        self.termination_event = termination_event or multiprocessing.Event()

    def run(self):
        """Start the process."""
        try:
            self.process = multiprocessing.Process(target=self.target, args=self.args)
            self.process.daemon = True
            self.process.start()
        except Exception as e:
            print(f"Error occurred while running process: {e}")

    def join(self):
        """Join the process."""
        try:
            if self.process:
                self.process.join()
        except Exception as e:
            print(f"Error occurred while joining process: {e}")

    def check_alive(self):
        """Check if the process is alive."""
        # Check exit code, handle errors, and restart if needed
        is_alive = self.process.is_alive() if self.process is not None else False
        if not is_alive:
            if self.process is not None:
                if self.process.exitcode == 0:
                    print(f"Process {self.process.name} exited normally. Restarting...")
                else:
                    print(
                        f"Process {self.process.name} exited with code {self.process.exitcode}."
                    )
                return False, self.process.exitcode
            else:
                return False, None
        return True, None

    def stop(self):
        """Stop the process."""
        if self.process:
            self.process.terminate()
            self.process.join()


def launch_dashboard(host: str, port: int, debug: bool = False, live_time: float = 10):
    """Launch the dashboard alone."""
    importlib.reload(alab_management.dashboard)
    from alab_management.dashboard import create_app

    if debug:
        print("Debug mode is on, the dashboard will be served with CORS enabled!")
    app = create_app(cors=debug)  # if debug enabled, allow cross-origin requests to API
    server = (
        WSGIServer((host, port), app)
        if debug
        else WSGIServer((host, port), app, log=None, error_log=None)
    )
    server.serve_forever()


def launch_experiment_manager(live_time: float):
    """Launch the experiment manager."""
    from alab_management.experiment_manager import ExperimentManager
    from alab_management.utils.module_ops import load_definition

    load_definition(get_version())
    experiment_manager = ExperimentManager(
        live_time=live_time, termination_event=termination_event
    )
    experiment_manager.run()


def launch_task_manager(live_time: float):
    """Launch the task manager."""
    from alab_management.task_manager.task_manager import TaskManager
    from alab_management.utils.module_ops import load_definition

    load_definition(get_version())
    task_launcher = TaskManager(
        live_time=live_time, termination_event=termination_event
    )
    task_launcher.run()


def launch_resource_manager(live_time: float):
    """Launch the resource manager."""
    from alab_management.resource_manager.resource_manager import ResourceManager
    from alab_management.utils.module_ops import load_definition

    load_definition(get_version())
    resource_manager = ResourceManager(
        live_time=live_time, termination_event=termination_event
    )
    resource_manager.run()


def launch_lab(host, port, debug, live_time: float):
    """Start to run the lab."""
    from alab_management.device_view import DeviceView

    dv = DeviceView()

    if len(list(dv.get_all())) == 0:
        print(
            "No devices found in the database. Please setup the lab using `alabos setup` first!"
        )
        sys.exit(1)

    # Create RestartableProcess objects for each process with shared termination_event
    dashboard_process = RestartableProcess(
        target=launch_dashboard,
        args=(host, port, debug, live_time),
        termination_event=termination_event,
    )
    experiment_manager_process = RestartableProcess(
        target=launch_experiment_manager,
        args=([live_time]),
        termination_event=termination_event,
    )
    task_launcher_process = RestartableProcess(
        target=launch_task_manager,
        args=([live_time]),
        termination_event=termination_event,
    )
    resource_manager_process = RestartableProcess(
        target=launch_resource_manager,
        args=([live_time]),
        termination_event=termination_event,
    )

    # Start the internally timed processes using multiprocessing
    processes = [
        experiment_manager_process,
        task_launcher_process,
        resource_manager_process,
    ]
    # Start the processes using multiprocessing and run them until termination_event is set
    while not termination_event.is_set():
        any_alive = False
        for process in processes:
            print(not process.check_alive()[0])
            if process.check_alive()[0]:
                any_alive = True
                break
        if not any_alive:
            if dashboard_process.check_alive()[0]:
                dashboard_process.stop()
            for process in processes:
                process.run()
            dashboard_process.run()
        else:
            if process.check_alive()[1] not in [0, None]:
                raise Exception(
                    f"Process {process.process.name} exited with code {process.check_alive()[1]}"
                )
        time.sleep(0.1)

    # Join all processes before exiting
    for process in processes:
        process.join()


def terminate_all_processes():
    """Set the termination event to stop all processes."""
    termination_event.set()
