import socket
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from multiprocessing import Process
from threading import Thread

import servicemanager
import win32event
import win32service
import win32serviceutil

from alab_management.scripts.launch_lab import launch_lab
from alab_management.scripts.launch_worker import launch_worker
from alab_management.user_input import UserInputView

alabos_host = "127.0.0.1"
alabos_port = 8895
alabos_debug = False
user_input_view = UserInputView()


def process_launch_worker():
    """
    Launches the worker process.
    This is a workaround to redirect the output of the worker process to a file.
    """
    with (
        open("D:\\alabos_service.log", "a", encoding="utf-8") as sys.stdout,
        open("D:\\alabos_service.log", "a", encoding="utf-8") as sys.stderr,
    ):
        launch_worker([])


class alabosService(win32serviceutil.ServiceFramework):
    """
    To use this, make sure to add win32 and pywin32 site-packages folders to environment variables.
    Current behavior:
    1. No output is printed to the log file if the service is running properly other than the dramatiq infos.
    2. Once we stop the service, the logs will be filled.
    3. Once we stop the service, We need to end task some of the zombie python processes
    (originating from the "launch_worker" "grand"-children processes that cannot be terminated somehow).
    Some references said that we have to keep track of the "grand"-children processes.
    Then terminate them first before terminating the "launch_worker" process itself.
    """

    _svc_name_ = "alabosService"
    _svc_display_name_ = "AlabOS Service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        """Stops the service."""
        self.running = False
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        """Runs the service."""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        self.main()

    def main(self):
        """Main function of the service."""
        with (
            redirect_stdout(open("D:\\alabos_service.log", "a", encoding="utf-8")),
            redirect_stderr(open("D:\\alabos_service.log", "a", encoding="utf-8")),
        ):
            self.running = True
            self.warned = False
            self.alabos_thread = Thread(
                target=launch_lab, args=(alabos_host, alabos_port, alabos_debug)
            )
            self.alabos_thread.daemon = True
            self.alabos_thread.start()
            self.worker_process = Process(target=process_launch_worker)
            self.worker_process.daemon = False
            self.worker_process.start()
            while self.running:
                time.sleep(0.5)
                if not self.alabos_thread.is_alive() and not self.warned:
                    print("AlabOS thread is dead")
                    user_input_view._alarm.alert(
                        "Traceback (most recent call last): \nURGENT! AlabOS thread is dead!",
                        category="Error",
                    )
                    self.warned = True
                if not self.worker_process.is_alive() and not self.warned:
                    print("AlabOS worker thread is dead")
                    user_input_view._alarm.alert(
                        "Traceback (most recent call last): \nURGENT! AlabOS worker thread is dead!",
                        category="Error",
                    )
                    self.warned = True
                if (
                    not self.alabos_thread.is_alive()
                    and not self.worker_process.is_alive()
                ):
                    print("Both AlabOS and the worker thread are dead")
                    user_input_view._alarm.alert(
                        "Traceback (most recent call last): \nURGENT! Both AlabOS and the worker thread are dead!",
                        category="Error",
                    )
                    self.running = False


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(alabosService)
