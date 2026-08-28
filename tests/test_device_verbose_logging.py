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
    read_verbose_log_tail,
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
                log_verbose_device("DASH_capper", "also %s", "logged")
                log_path = Path(tmp_dir) / "MOBILE_arm_ALFRED.log"
                self.assertTrue(log_path.exists())
                self.assertIn("hello world", log_path.read_text(encoding="utf-8"))
                capper_log = Path(tmp_dir) / "DASH_capper.log"
                self.assertTrue(capper_log.exists())
                self.assertIn("also logged", capper_log.read_text(encoding="utf-8"))
                self.assertTrue(should_trace_device("MOBILE_arm_ALFRED"))
                self.assertTrue(should_trace_device("DASH_capper"))
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

    def test_read_verbose_log_tail_returns_the_last_lines(self) -> None:
        previous_devices = os.environ.get("ALABOS_VERBOSE_DEVICES")
        previous_dir = os.environ.get("ALABOS_VERBOSE_LOG_DIR")
        with TemporaryDirectory() as tmp_dir:
            os.environ["ALABOS_VERBOSE_DEVICES"] = "DASH_arm_JEEVES"
            os.environ["ALABOS_VERBOSE_LOG_DIR"] = tmp_dir
            try:
                log_path = Path(tmp_dir) / "DASH_arm_JEEVES.log"
                log_path.write_text(
                    "".join(f"line {index}\n" for index in range(30)),
                    encoding="utf-8",
                )
                payload = read_verbose_log_tail("DASH_arm_JEEVES", max_lines=5)
                self.assertTrue(payload["available"])
                self.assertEqual(payload["lines"], ["line 25", "line 26", "line 27", "line 28", "line 29"])
            finally:
                if previous_devices is None:
                    os.environ.pop("ALABOS_VERBOSE_DEVICES", None)
                else:
                    os.environ["ALABOS_VERBOSE_DEVICES"] = previous_devices
                if previous_dir is None:
                    os.environ.pop("ALABOS_VERBOSE_LOG_DIR", None)
                else:
                    os.environ["ALABOS_VERBOSE_LOG_DIR"] = previous_dir

    def test_read_verbose_log_tail_does_not_require_a_launcher_checkbox(self) -> None:
        previous_devices = os.environ.get("ALABOS_VERBOSE_DEVICES")
        previous_dir = os.environ.get("ALABOS_VERBOSE_LOG_DIR")
        with TemporaryDirectory() as tmp_dir:
            os.environ.pop("ALABOS_VERBOSE_DEVICES", None)
            os.environ["ALABOS_VERBOSE_LOG_DIR"] = tmp_dir
            try:
                log_path = Path(tmp_dir) / "DASH_capper.log"
                log_path.write_text("[12:00:00] hello\n", encoding="utf-8")
                payload = read_verbose_log_tail("DASH_capper")
                self.assertTrue(payload["available"])
                self.assertEqual(payload["lines"], ["[12:00:00] hello"])
            finally:
                if previous_devices is None:
                    os.environ.pop("ALABOS_VERBOSE_DEVICES", None)
                else:
                    os.environ["ALABOS_VERBOSE_DEVICES"] = previous_devices
                if previous_dir is None:
                    os.environ.pop("ALABOS_VERBOSE_LOG_DIR", None)
                else:
                    os.environ["ALABOS_VERBOSE_LOG_DIR"] = previous_dir

    def test_read_verbose_log_tail_says_when_the_file_is_missing(self) -> None:
        previous_dir = os.environ.get("ALABOS_VERBOSE_LOG_DIR")
        with TemporaryDirectory() as tmp_dir:
            os.environ["ALABOS_VERBOSE_LOG_DIR"] = tmp_dir
            try:
                payload = read_verbose_log_tail("DASH_arm_JEEVES")
                self.assertFalse(payload["available"])
                self.assertEqual(payload["reason"], "no_file")
            finally:
                if previous_dir is None:
                    os.environ.pop("ALABOS_VERBOSE_LOG_DIR", None)
                else:
                    os.environ["ALABOS_VERBOSE_LOG_DIR"] = previous_dir

    def test_read_verbose_log_tail_rejects_a_path_escape(self) -> None:
        with self.assertRaises(ValueError):
            read_verbose_log_tail("../secret")

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
