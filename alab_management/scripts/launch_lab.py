"""
The script to launch task_view and executor, which are the core of the system.
"""
import multiprocessing
import sys
import time
from multiprocessing import Process

import click
from gevent.pywsgi import WSGIServer


def launch_dashboard(host: str, port: int, debug: bool = False):
    from ..dashboard import create_app

    app = create_app()
    if debug:
        server = WSGIServer((host, port), app)  # print server's log on the console
    else:
        server = WSGIServer((host, port), app, log=None, error_log=None)
    click.echo(f"Starting dashboard on http://{host}:{port}")
    server.serve_forever()


def launch_experiment_manager():
    from ..experiment_manager import ExperimentManager
    from ..utils.module_ops import load_definition

    load_definition()
    experiment_manager = ExperimentManager()
    experiment_manager.run()


def launch_executor():
    from ..executor import Executor
    from ..utils.module_ops import load_definition

    load_definition()
    executor = Executor()
    executor.run()


def launch_lab(host, port, debug):
    multiprocessing.set_start_method('spawn')

    dashboard_process = Process(target=launch_dashboard, args=(host, port, debug))
    experiment_manager_process = Process(target=launch_experiment_manager)
    executor_process = Process(target=launch_executor)

    dashboard_process.daemon = \
        experiment_manager_process.daemon = \
        executor_process.daemon = False

    dashboard_process.start()
    experiment_manager_process.start()
    executor_process.start()

    while True:
        time.sleep(1)
        if not experiment_manager_process.is_alive():
            executor_process.terminate()
            dashboard_process.terminate()
            sys.exit(1001)

        if not executor_process.is_alive():
            experiment_manager_process.terminate()
            dashboard_process.terminate()
            sys.exit(1002)

        if not dashboard_process.is_alive():
            executor_process.terminate()
            experiment_manager_process.terminate()
            sys.exit(1003)
