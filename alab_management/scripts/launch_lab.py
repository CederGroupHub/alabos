"""The script to launch task_view and executor, which are the core of the system."""

import contextlib
import multiprocessing
import sys
import time
from threading import Thread
from gevent.pywsgi import WSGIServer  # type: ignore
import multiprocessing
with contextlib.suppress(RuntimeError):
    multiprocessing.set_start_method("spawn")

class RestartableProcess:
    """A class for creating processes that can be automatically restarted after failures."""

    def __init__(self, target, args=(), live_time=None, termination_event=None):
        self.target = target
        self.live_time = live_time
        self.process = None
        self.termination_event = termination_event or multiprocessing.Event()

    def run(self):
        start = time.time()
        while not self.termination_event.is_set() and (self.live_time is None or time.time() - start < self.live_time):
            try:
                process = multiprocessing.Process(target=self.target, args=self.args)
                process.start()
                process.join()  # Wait for process to finish

                # Check exit code, handle errors, and restart if needed
                if process.exitcode == 0:
                    print(f"Process {process.name} exited normally. Restarting...")
                else:
                    print(f"Process {process.name} exited with code {process.exitcode}.")
            except Exception as e:
                print(f"Error occurred while running process: {e}")

            # Check for termination before restarting
            if self.termination_event.is_set():
                break

            time.sleep(self.live_time or 0)  # Restart after live_time or immediately if None

def launch_dashboard(host: str, port: int, debug: bool = False):
    """Launch the dashboard alone."""
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


def launch_experiment_manager():
    """Launch the experiment manager."""
    from alab_management.experiment_manager import ExperimentManager
    from alab_management.utils.module_ops import load_definition

    load_definition()
    experiment_manager = ExperimentManager()
    experiment_manager.run()


def launch_task_manager():
    """Launch the task manager."""
    from alab_management.task_manager.task_manager import TaskManager
    from alab_management.utils.module_ops import load_definition

    load_definition()
    task_launcher = TaskManager(live_time=3600)
    task_launcher.run()


def launch_device_manager():
    """Launch the device manager."""
    from alab_management.device_manager import DeviceManager
    from alab_management.utils.module_ops import load_definition

    load_definition()
    device_manager = DeviceManager()
    device_manager.run()


def launch_resource_manager():
    """Launch the resource manager."""
    from alab_management.resource_manager.resource_manager import ResourceManager
    from alab_management.utils.module_ops import load_definition

    load_definition()
    resource_manager = ResourceManager()
    resource_manager.run()


def launch_lab(host, port, debug):
    """Start to run the lab."""
    from alab_management.device_view import DeviceView

    dv = DeviceView()

    if len(list(dv.get_all())) == 0:
        print(
            "No devices found in the database. Please setup the lab using `alabos setup` first!"
        )
        sys.exit(1)

    # Create RestartableProcess objects for each process
    dashboard_process = RestartableProcess(target=launch_dashboard, args=(host, port, debug), live_time=3600)  # Restart every hour
    experiment_manager_process = RestartableProcess(target=launch_experiment_manager, args=(host, port, debug), live_time=3600)
    task_launcher_process = RestartableProcess(target=launch_task_manager, args=(host, port, debug), live_time=3600)
    device_manager_process = RestartableProcess(target=launch_device_manager, args=(host, port, debug), live_time=3600)
    resource_manager_process = RestartableProcess(target=launch_resource_manager, args=(host, port, debug), live_time=3600)

    # Start the processes
    dashboard_process.run()
    experiment_manager_process.run()
    task_launcher_process.run()
    device_manager_process.run()
    resource_manager_process.run()

    """With RestartableProcess, each process is designed to handle restarts automatically.
    So, there's no need to worry about the program exiting before background tasks finish -
    they will be restarted by RestartableProcess if necessary."""
