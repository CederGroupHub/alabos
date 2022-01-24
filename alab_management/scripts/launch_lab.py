"""
The script to launch task_view and executor, which are the core of the system.
"""
import multiprocessing
import sys
import time
from multiprocessing import Process

from gevent.pywsgi import WSGIServer

try:
    multiprocessing.set_start_method('spawn')
except RuntimeError:
    pass


def launch_dashboard(host: str, port: int, debug: bool = False):
    from ..dashboard import create_app

    app = create_app()
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


def launch_task():
    from ..task_launcher import TaskLauncher
    from ..utils.module_ops import load_definition

    load_definition()
    task_launcher = TaskLauncher()
    task_launcher.run()


def launch_lab(host, port, debug):
    dashboard_process = Process(target=launch_dashboard, args=(host, port, debug))
    experiment_manager_process = Process(target=launch_experiment_manager)
    task_launcher_process = Process(target=launch_task)

    dashboard_process.daemon = \
        experiment_manager_process.daemon = \
        task_launcher_process.daemon = False

    dashboard_process.start()
    experiment_manager_process.start()
    task_launcher_process.start()

    while True:
        time.sleep(1)
        if not experiment_manager_process.is_alive():
            task_launcher_process.terminate()
            dashboard_process.terminate()
            task_launcher_process.join()
            dashboard_process.join()
            sys.exit(1001)

        if not task_launcher_process.is_alive():
            experiment_manager_process.terminate()
            dashboard_process.terminate()
            experiment_manager_process.join()
            dashboard_process.join()
            sys.exit(1002)

        if not dashboard_process.is_alive():
            task_launcher_process.terminate()
            experiment_manager_process.terminate()
            task_launcher_process.join()
            experiment_manager_process.join()
            sys.exit(1003)
