"""The script to launch task_view and executor, which are the core of the system."""

import contextlib
import multiprocessing
import sys
import time
from threading import Thread

from gevent.pywsgi import WSGIServer  # type: ignore

with contextlib.suppress(RuntimeError):
    multiprocessing.set_start_method("spawn")


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
    task_launcher = TaskManager()
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
    import logging

    from alab_management.device_view import DeviceView

    logging.basicConfig(level=logging.INFO)

    dv = DeviceView()

    if len(list(dv.get_all())) == 0:
        print(
            "No devices found in the database. Please setup the lab using `alabos setup` first!"
        )
        sys.exit(1)

    dashboard_thread = Thread(target=launch_dashboard, args=(host, port, debug))
    experiment_manager_thread = Thread(target=launch_experiment_manager)
    task_launcher_thread = Thread(target=launch_task_manager)
    device_manager_thread = Thread(target=launch_device_manager)
    resource_manager_thread = Thread(target=launch_resource_manager)

    dashboard_thread.daemon = experiment_manager_thread.daemon = (
        task_launcher_thread.daemon
    ) = device_manager_thread.daemon = resource_manager_thread.daemon = True

    dashboard_thread.start()
    device_manager_thread.start()
    experiment_manager_thread.start()
    task_launcher_thread.start()
    resource_manager_thread.start()

    while True:
        time.sleep(1.5)
        if not experiment_manager_thread.is_alive():
            sys.exit(1001)

        if not task_launcher_thread.is_alive():
            sys.exit(1002)

        if not dashboard_thread.is_alive():
            sys.exit(1003)

        if not device_manager_thread.is_alive():
            sys.exit(1004)
