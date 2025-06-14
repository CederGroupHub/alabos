"""The script to launch task_view and executor, which are the core of the system."""

import contextlib
import multiprocessing
import sys
import time
from threading import Thread

from gevent.pywsgi import WSGIServer  # type: ignore

from alab_management.utils.module_ops import calculate_package_hash

with contextlib.suppress(RuntimeError):
    multiprocessing.set_start_method("spawn")


experiment_manager = None
task_manager = None
device_manager = None
resource_manager = None
package_fingerprint = None


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

    global experiment_manager

    load_definition()
    experiment_manager = ExperimentManager()
    experiment_manager.run()
    print(experiment_manager)


def launch_task_manager():
    """Launch the task manager."""
    from alab_management.task_manager.task_manager import TaskManager
    from alab_management.utils.module_ops import load_definition

    global task_manager

    load_definition()
    task_manager = TaskManager()
    # Clean up any leftover tasks from previous runs. This blocks new workers until cleanup is done!

    task_manager.run()


def launch_device_manager():
    """Launch the device manager."""
    from alab_management.device_manager import DeviceManager
    from alab_management.utils.module_ops import load_definition

    global device_manager

    load_definition()
    device_manager = DeviceManager()
    device_manager.run()


def launch_resource_manager():
    """Launch the resource manager."""
    from alab_management.resource_manager.resource_manager import ResourceManager
    from alab_management.utils.module_ops import load_definition

    global resource_manager

    load_definition()
    resource_manager = ResourceManager()
    resource_manager.run()


def system_refresh():
    """Refresh the system if the package fingerprint has changed and auto_refresh is configured."""
    from alab_management.config import AlabOSConfig

    config = AlabOSConfig()
    if not config["general"].get("auto_refresh", False):
        return

    if (
        experiment_manager is None
        or device_manager is None
        or resource_manager is None
        or task_manager is None
    ):
        print("System is not fully initialized. Please wait for a while for refresh.")
        return
    global package_fingerprint

    current_package_fingerprint = calculate_package_hash()

    if current_package_fingerprint != package_fingerprint:
        package_fingerprint = current_package_fingerprint
        print(
            "Package fingerprint has changed, reloading definitions and refreshing system."
        )
        with (
            task_manager.pause_new_task_launching(),
            resource_manager.pause_resource_assigning(),
            device_manager.pause_all_devices(),
        ):
            while task_manager.check_number_of_running_tasks():
                time.sleep(10)
            time.sleep(10)  # give some time for tasks to finish
            task_manager.refresh_tasks()
            device_manager.refresh_devices()
            time.sleep(10)


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

    global package_fingerprint

    package_fingerprint = calculate_package_hash()

    counter = 0
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

        if not resource_manager_thread.is_alive():
            sys.exit(1005)

        counter += 1
        if counter % 10 == 0:  # check every minute
            system_refresh()
            counter = 0
