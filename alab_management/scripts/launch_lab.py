"""
The script to launch task_view and executor, which are the core of the system.
"""

import multiprocessing
import sys
import time
from threading import Thread

from gevent.pywsgi import WSGIServer

try:
    multiprocessing.set_start_method("spawn")
except RuntimeError:
    pass


def launch_dashboard(host: str, port: int, debug: bool = False):
    from ..dashboard import create_app

    if debug:
        print("Debug mode is on, the dashboard will be served with CORS enabled!")
    app = create_app(cors=debug)  # if debug enabled, allow cross-origin requests to API
    if debug:
        server = WSGIServer((host, port), app)  # print server's log on the console
    else:
        server = WSGIServer((host, port), app, log=None, error_log=None)
    server.serve_forever()


def launch_experiment_manager():
    from ..experiment_manager import ExperimentManager
    from ..utils.module_ops import load_definition

    load_definition()
    experiment_manager = ExperimentManager()
    experiment_manager.run()


def launch_task_manager():
    from ..task_manager import TaskManager
    from ..utils.module_ops import load_definition

    load_definition()
    task_launcher = TaskManager()
    task_launcher.run()


def launch_device_manager():
    from ..device_manager import DeviceManager
    from ..utils.module_ops import load_definition

    load_definition()
    device_manager = DeviceManager()
    device_manager.run()


def launch_lab(host, port, debug):
    from alab_management.device_view import DeviceView

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

    dashboard_thread.daemon = (
        experiment_manager_thread.daemon
    ) = task_launcher_thread.daemon = device_manager_thread.daemon = True

    dashboard_thread.start()
    experiment_manager_thread.start()
    task_launcher_thread.start()
    device_manager_thread.start()

    while True:
        time.sleep(1)
        if not experiment_manager_thread.is_alive():
            sys.exit(1001)

        if not task_launcher_thread.is_alive():
            sys.exit(1002)

        if not dashboard_thread.is_alive():
            sys.exit(1003)

        if not device_manager_thread.is_alive():
            sys.exit(1004)
