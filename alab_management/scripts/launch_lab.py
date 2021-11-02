"""
The script to launch task_view and executor, which are the core of the system.
"""

from multiprocessing import Process

from .. import TaskManager, Executor


def launch_task_manager():
    task_manager = TaskManager()
    task_manager.run()


def launch_executor():
    executor = Executor()
    executor.run()


def launch_lab():
    task_manager_process = Process(target=launch_task_manager)
    executor_process = Process(target=launch_executor)

    task_manager_process.daemon = False
    executor_process.daemon = False

    task_manager_process.start()
    executor_process.start()

    while True:
        if (not task_manager_process.is_alive()
                or not executor_process.is_alive()):
            exit(1)
