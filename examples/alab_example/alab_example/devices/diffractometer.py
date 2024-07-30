"""This module contains the Diffractometer class for acquiring X-Ray Diffraction patterns."""

from __future__ import annotations

import uuid
from typing import ClassVar

import numpy as np
from alab_control.diffractometer_aeris import Aeris as XRDDriver
from alab_management.device_view import BaseDevice
from alab_management.device_view.device import mock
from alab_management.sample_view import SamplePosition


class Diffractometer(BaseDevice):
    """A device for acquiring X-Ray Diffraction patterns."""

    description: ClassVar[str] = "Diffractometer to acquire X-Ray Diffraction patterns"
    SLOT_TO_USE = 1

    def __init__(self, address: str, results_dir: str, *args, **kwargs):
        """Initialize the Diffractometer object."""
        super().__init__(*args, **kwargs)
        self.address = address
        self.running = False
        self.schemas = {
            "fast_10min": dict(tt_min=10, tt_max=70, tt_step=0.1, rate=6),
            "slow_30min": dict(tt_min=10, tt_max=70, tt_step=0.1, rate=2),
        }
        self.results_dir = results_dir

    @mock(object_type=XRDDriver)
    def get_driver(self):
        """Return the driver for the Diffractometer."""
        self.driver = XRDDriver(ip=self.address, results_dir=self.results_dir)
        self._confirm_connection()
        return self.driver

    def connect(self):
        """Connect to the Diffractometer."""
        self.driver = self.get_driver()

    def disconnect(self):
        """Disconnect from the Diffractometer."""
        self.driver = None

    def _confirm_connection(self):
        if self.driver is None:
            raise Exception("Device is not connected!")
        try:
            while not self.driver.is_under_remote_control:
                self._device_view.pause_device(self.name)
                self.set_message(
                    "The Aeris is not under remote control. Please set to remote control and try again."
                )
                self.request_maintenance(
                    prompt="Please set the Aeris XRD to remote control, then press OK to continue.",
                    options=["OK"],
                )
                if self.driver.is_under_remote_control:
                    self._device_view.unpause_device(self.name)
                    self.set_message(
                        "Successfully connected to the Aeris in remote control mode!"
                    )
        except TimeoutError:
            self.set_message("Connection to Aeris has timed out.")
            response = self.request_maintenance(
                prompt="Please confirm you have turned on Aeris. Press OK to continue or Cancel to stop the OS. "
                "It will start in paused mode if you click OK.",
                options=["OK", "Cancel"],
            )
            self._device_view.pause_device(self.name)
            if response == "Cancel":
                raise

    @property
    def sample_positions(self):
        """Return the sample positions of the Diffractometer."""
        return [
            SamplePosition(
                "slot".format(),
                description="Arm that moves samples in and out of the diffractometer.",
            ),
        ]

    def emergent_stop(self):
        """Stop the Diffractometer."""
        return
        # self.driver.stop()

    @mock(
        return_constant={
            "twotheta": np.linspace(10, 100, 1000).tolist(),
            "counts": np.random.rand(1000).tolist(),
            "sampleid_in_aeris": "test_sampleid",
        }
    )
    def run_scan(self, sample_name: str, schema: str) -> dict[str, list[float] | str]:
        """Scans the sample in the diffractometer using a preset schema.

        Args:
            schema (str): name of a preset schema to use for the scan.
            sample_name (str): name of the sample to scan.

        Returns:
            Dict[str, List[float]]: dictionary with the keys "twotheta" and "counts" containing the xy data from the XRD
            scan. also includes the sampleid of the sample within the Aeris.
        """
        self._confirm_connection()
        self.set_message(f"Logging {sample_name} in the Aeris database")
        sampleid = f"{sample_name}_{uuid.uuid4()}"
        self.driver.add(sample_id=sampleid, loc=self.SLOT_TO_USE)
        try:
            self.set_message(f'Scanning with schema "{schema}"')
            # TODO default schema if not valid?
            twotheta, counts = self.driver.scan_and_return_results(
                sample_id=sampleid, program=schema
            )
            self.set_message(f"Scan of {sample_name} is complete.")
        except:
            self.set_message(f"Scan of {sample_name} has failed.")
            raise
        finally:
            self.driver.remove(sample_id=sampleid)

        return {
            "twotheta": twotheta.tolist(),
            "counts": counts.tolist(),
            "sampleid_in_aeris": sampleid,
        }

    @mock(return_constant=False)
    def is_running(self):
        """Return whether the Diffractometer is running."""
        return self.driver.xrd_is_busy
        # return self.driver.is_running()
