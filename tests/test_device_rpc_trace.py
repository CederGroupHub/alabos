import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from alab_management.device_manager import _summarize_rpc_call
from alab_management.utils.logger import (
    is_device_rpc_debug_enabled,
    is_mobile_robot_debug_enabled,
    is_robot_arm_mobile_debug_enabled,
)


class TestDeviceRpcTrace(TestCase):
    def test_summarize_rpc_call(self):
        self.assertEqual(
            _summarize_rpc_call("a", 123, foo="bar"),
            "'a', 123, foo='bar'",
        )
        long_value = "x" * 100
        summary = _summarize_rpc_call(long_value)
        self.assertIn("...", summary)

    def test_logging_debug_config_toggle(self):
        previous_config_path = os.environ.get("ALABOS_CONFIG_PATH")
        previous_rpc_env = os.environ.get("ALABOS_DEVICE_RPC_DEBUG")
        os.environ.pop("ALABOS_DEVICE_RPC_DEBUG", None)

        with TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.toml"
            config_path.write_text(
                "[general]\nname = 'TestLab'\n\n"
                "[logging]\n"
                "device_rpc_debug = true\n"
                "mobile_robot_debug = true\n"
                "robot_arm_mobile_debug = true\n",
                encoding="utf-8",
            )
            os.environ["ALABOS_CONFIG_PATH"] = str(config_path)
            try:
                self.assertTrue(is_device_rpc_debug_enabled())
                self.assertTrue(is_mobile_robot_debug_enabled())
                self.assertTrue(is_robot_arm_mobile_debug_enabled())
            finally:
                if previous_config_path is None:
                    os.environ.pop("ALABOS_CONFIG_PATH", None)
                else:
                    os.environ["ALABOS_CONFIG_PATH"] = previous_config_path
                if previous_rpc_env is None:
                    os.environ.pop("ALABOS_DEVICE_RPC_DEBUG", None)
                else:
                    os.environ["ALABOS_DEVICE_RPC_DEBUG"] = previous_rpc_env

    def test_logging_debug_env_toggles(self):
        previous = {
            "ALABOS_DEVICE_RPC_DEBUG": os.environ.get("ALABOS_DEVICE_RPC_DEBUG"),
            "ALABOS_MOBILE_ROBOT_DEBUG": os.environ.get("ALABOS_MOBILE_ROBOT_DEBUG"),
            "ALABOS_ROBOT_ARM_MOBILE_DEBUG": os.environ.get(
                "ALABOS_ROBOT_ARM_MOBILE_DEBUG"
            ),
        }
        try:
            os.environ["ALABOS_DEVICE_RPC_DEBUG"] = "1"
            self.assertTrue(is_device_rpc_debug_enabled())
            os.environ["ALABOS_MOBILE_ROBOT_DEBUG"] = "1"
            self.assertTrue(is_mobile_robot_debug_enabled())
            os.environ["ALABOS_ROBOT_ARM_MOBILE_DEBUG"] = "1"
            self.assertTrue(is_robot_arm_mobile_debug_enabled())
            os.environ["ALABOS_DEVICE_RPC_DEBUG"] = "0"
            self.assertFalse(is_device_rpc_debug_enabled())
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
