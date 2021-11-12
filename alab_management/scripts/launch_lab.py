"""
The script to launch task_view and executor, which are the core of the system.
"""
import time
from multiprocessing import Process

import click

from .. import ExperimentManager, Executor, __version__
from ..dashboard import create_app
from ..utils.module_ops import load_definition
from gevent.pywsgi import WSGIServer


def launch_dashboard(host, port):
    app = create_app()
    server = WSGIServer((host, port), app, log=None, error_log=None)
    print(f"Starting dashboard on http://{host}:{port}")
    server.serve_forever()


def launch_experiment_manager():
    load_definition()
    experiment_manager = ExperimentManager()
    experiment_manager.run()


def launch_executor():
    load_definition()
    executor = Executor()
    executor.run()


@click.command()
@click.option("--host", default="127.0.0.1", )
@click.option("-p", "--port", default="8895", type=int)
def launch_lab(host, port):
    print(rf"""
       _    _       _         ___  ____  
      / \  | | __ _| |__     / _ \/ ___| 
     / _ \ | |/ _` | '_ \   | | | \___ \ 
    / ___ \| | (_| | |_) |  | |_| |___) |
   /_/   \_\_|\__,_|_.__/    \___/|____/      
 
----  Alab OS v{__version__} -- Alab Project Team  ----
""")
    dashboard_process = Process(target=launch_dashboard, args=(host, port))
    experiment_manager_process = Process(target=launch_experiment_manager)
    executor_process = Process(target=launch_executor)

    dashboard_process.daemon = False
    experiment_manager_process.daemon = False
    executor_process.daemon = False

    dashboard_process.start()
    experiment_manager_process.start()
    executor_process.start()

    while True:
        time.sleep(1)
        if not experiment_manager_process.is_alive():
            executor_process.kill()
            dashboard_process.kill()
            exit(1001)

        if not executor_process.is_alive():
            experiment_manager_process.kill()
            dashboard_process.kill()
            exit(1002)

        if not dashboard_process.is_alive():
            executor_process.kill()
            experiment_manager_process.kill()
            exit(1003)
