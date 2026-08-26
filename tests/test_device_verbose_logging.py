import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from alab_management.utils.device_verbose_logging import (
    MOBILE_ROBOT_DEVICE_NAME,
    get_verbose_devices,
    is_verbose_device,
    log_verbose_device,
    prepare_verbose_log_files,
    should_trace_device,
)


class TestDeviceVerboseLogging(TestCase):
    def test_verbose_device_file_logging(self) -> None:
        previous_devices = os.environ.get("ALABOS_VERBOSE_DEVICES")
        previous_dir = os.environ.get("ALABOS_VERBOSE_LOG_DIR")
        with TemporaryDirectory() as tmp_dir:
            os.environ["ALABOS_VERBOSE_DEVICES"] = "MOBILE_arm_ALFRED"
            os.environ["ALABOS_VERBOSE_LOG_DIR"] = tmp_dir
            try:
                self.assertTrue(is_verbose_device("MOBILE_arm_ALFRED"))
                self.assertFalse(is_verbose_device("DASH_capper"))
                log_verbose_device("MOBILE_arm_ALFRED", "hello %s", "world")
                log_path = Path(tmp_dir) / "MOBILE_arm_ALFRED.log"
                self.assertTrue(log_path.exists())
                self.assertIn("hello world", log_path.read_text(encoding="utf-8"))
                self.assertTrue(should_trace_device("MOBILE_arm_ALFRED"))
                self.assertFalse(should_trace_device("DASH_capper"))
            finally:
                if previous_devices is None:
                    os.environ.pop("ALABOS_VERBOSE_DEVICES", None)
                else:
                    os.environ["ALABOS_VERBOSE_DEVICES"] = previous_devices
                if previous_dir is None:
                    os.environ.pop("ALABOS_VERBOSE_LOG_DIR", None)
                else:
                    os.environ["ALABOS_VERBOSE_LOG_DIR"] = previous_dir

    def test_prepare_verbose_log_files(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            log_dir = Path(tmp_dir)
            prepare_verbose_log_files(
                [MOBILE_ROBOT_DEVICE_NAME, "DASH_capper"],
                log_dir,
            )
            self.assertTrue((log_dir / "MOBILE_arm_ALFRED.log").exists())
            self.assertTrue((log_dir / "DASH_capper.log").exists())

    def test_get_verbose_devices(self) -> None:
        previous = os.environ.get("ALABOS_VERBOSE_DEVICES")
        os.environ["ALABOS_VERBOSE_DEVICES"] = "A, B ,C"
        try:
            self.assertEqual(get_verbose_devices(), {"A", "B", "C"})
        finally:
            if previous is None:
                os.environ.pop("ALABOS_VERBOSE_DEVICES", None)
            else:
                os.environ["ALABOS_VERBOSE_DEVICES"] = previous
