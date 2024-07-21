"""This module provides the LabmanQuadrant class for interacting with Labman powder dosing station."""

from __future__ import annotations

import threading
import time
from typing import ClassVar, Literal

from alab_control.labman import InputFile, LabmanError, QuadrantStatus, Workflow
from alab_control.labman import Labman as LabmanDriver

from alab_management.device_view import BaseDevice
from alab_management.device_view.dbattributes import value_in_database
from alab_management.device_view.device import mock
from alab_management.sample_view import SamplePosition


class LabmanQuadrant(BaseDevice):
    """One of four quadrants within Labman powder dosing station. This quadrant can host up to 16 samples. The
    Labman is an enclosed set of devices that weighs and mixes powders, then dispenses them into crucibles. This is done
    prior to sending samples to the furnaces.
    """

    description: ClassVar[
        str
    ] = """
    One of four quadrants within Labman powder dosing station. This quadrant can host up to 16 samples. The
    Labman is an enclosed set of devices that weighs and mixes powders, then dispenses them into crucibles. This is done
    prior to sending samples to the furnaces.
    """

    waiting_for_cleanup: bool = value_in_database(
        name="waiting_for_cleanup", default_value=False
    )

    def __init__(
        self,
        quadrant_index: Literal[1, 2, 3, 4],
        ip_address: str = "128.3.17.139",
        port: int = 8080,
        *args,
        **kwargs,
    ):
        """Initializes the Labman device. Note that we do not connect to the Labman until the `.connect()` method is
        called.

        Args:
            ip_address (str, optional): Labman's IP address. This is internal to the LBL intranet. Defaults to None, in
                which case the IP address is loaded from the config file.
            port (int, optional): Port over which Labman API is exposte. Defaults to None, in which case the port is
                loaded from the config file.
            quadrant_index (Literal[1, 2, 3, 4]): Index of the quadrant within the Labman. Must be one of [1, 2, 3, 4].
            args: Additional arguments.
            kwargs: Additional keyword arguments.
        """
        super().__init__(*args, **kwargs)

        self.ip_address = ip_address
        self.port = port
        if quadrant_index not in [1, 2, 3, 4]:
            raise ValueError(
                f"quadrant_index must be one of [1,2,3,4], not {quadrant_index}"
            )
        self.quadrant_index = quadrant_index
        self.__daemon_running = False

    @mock(object_type=LabmanDriver)
    def get_driver(self):
        """Return the driver for the Labman."""
        self.driver = LabmanDriver(url=self.ip_address, port=self.port)
        return self.driver

    def connect(self):
        """Connect to the Labman."""
        self.driver = self.get_driver()

    def disconnect(self):
        """Disconnect from the Labman."""
        del self.driver

    @mock(return_constant="mock is running")
    def take_control(self):
        """Take control of a Labman quadrant. The Labman cannot access any jars or crucibles on the quadrant until it is
        released using the `Labman.release_quadrant` method.
        """
        self.set_message("Waiting to take control of Labman quadrant...")
        retry_count = 0
        while True:
            while not self.driver.rack_under_robot_control:
                self.set_message(
                    "Waiting to take control of Labman quadrant. Another quadrant is currently being controlled by a "
                    "user/other task, waiting for them to release control..."
                )
                time.sleep(1)
            try:
                self.set_message("Requesting control of Labman quadrant")
                self.driver.take_quadrant(
                    index=self.quadrant_index
                )  # this blocks until Labman yields control to us
                break
            except LabmanError as e:
                # we might get a LabmanError is anothe quadrant immediately takes control. Race condition.
                # So we wait and try to get it once that quadrant releases control.
                retry_count += 1
                self.set_message(
                    f"Retry ({retry_count}) to take control of Labman quadrant. Got error: {e}. "
                )

        self.set_message("Currently in control of the Labman quadrant.")

    @mock(return_constant="mock is running")
    def release_control(self):
        """Release control of a Labman quadrant. The Labman can now access jars and crucibles on the quadrant."""
        self.set_message("Releasing control of Labman quadrant...")
        if not self.driver.rack_under_robot_control:
            self.driver.release_quadrant()
        self.set_message("")

    def submit_workflow(
        self, name: str, inputfiles_as_json: dict[str, dict]
    ) -> tuple[str, dict[int, list[str]]]:
        """Submits a workflow to the Labman quadrant.

        Args:
            inputfiles_as_json (Dict[str, dict]): Dictionary of {sample: inputfile_json} of inputfiles as json
            name (str): name of the workflow

        Returns:
            str: name of the workflow. This is used to retrieve results from the Labman quadrant.
            Dict[int, List[str]]: mapping from mixing pot index to samples which are generated from those mixingpots.
                {mixingpot_index: [sample1_name, sample2_name, ...]}
        """
        workflow = Workflow(name=name)
        available_mixingpots = list(range(1, 17))  # TODO available mixingpots

        for sample_name, inputfile_json in inputfiles_as_json.items():
            inputfile = InputFile.from_json(inputfile_json)
            workflow.add_input(inputfile, sample=sample_name)

        workflow_json, mixingpot_to_sample = workflow.to_json(
            quadrant_index=self.quadrant_index,
            available_positions=available_mixingpots,
            return_sample_tracking=True,
        )
        print(f"mixingpot_to_sample: {mixingpot_to_sample}")
        self.take_control()
        self.driver.submit_workflow_json(workflow_json)
        self.release_control()
        self.set_message(f"Working on workflow: {name}.")
        return workflow.name, mixingpot_to_sample

    @mock(return_constant=False)
    def has_error(self) -> bool:
        """Returns True if the Labman is displaying a process error. This error is not necessarily isolated to this
        quadrant, but is stopping the Labman from processing any workflows until it is resolved.

        Returns:
            bool: Whether the Labman is displaying a process error.
        """
        return self.driver.has_error

    @mock(return_constant=None)
    def get_error_message(self) -> str | None:
        """Returns the error message displayed on the Labman GUI, if any. If none, returns None."""
        return self.driver.error_message

    @property
    def sample_positions(self):
        """Return the sample positions of the LabmanQuadrant."""
        return [
            ### Quadrant 1
            SamplePosition(
                "jar",
                number=16,
                description="Slot that can accept a jar (mixing pot) on the Labman quadrant.",
            ),
            SamplePosition(
                "crucible/SubRackA",
                number=4,
                description="Slot that can accept a crucible on the Labman quadrant, SubRack A.",
            ),
            SamplePosition(
                "crucible/SubRackB",
                number=4,
                description="Slot that can accept a crucible on Labman quadrant, SubRack B.",
            ),
            SamplePosition(
                "crucible/SubRackC",
                number=4,
                description="Slot that can accept a crucible on Labman quadrant, SubRack C.",
            ),
            SamplePosition(
                "crucible/SubRackD",
                number=4,
                description="Slot that can accept a crucible on Labman quadrant, SubRack D.",
            ),
            SamplePosition(
                "processing",
                number=16,
                description="Undefined position within the Labman. Samples in these positions are currently being "
                "generated somewhere within the Labman. Once the workflow is complete and the sample is ready in a "
                "crucible, the sample will be moved to a crucible position within this Labman Quadrant.",
            ),
        ]

    def emergent_stop(self):
        """Stop the Labman."""

    @mock(return_constant=False)
    def is_running(self) -> bool:
        """Return whether the Labman is running."""
        return self.driver.robot_is_running()

    @mock(return_constant=QuadrantStatus.COMPLETE)
    def get_status(self) -> QuadrantStatus:
        """Returns the status of the Labman quadrant."""
        status = self.driver.get_quadrant_status(self.quadrant_index)
        if status == QuadrantStatus.UNKNOWN:
            self.set_message(
                "Could not determine the state of this quadrant, likely a Labman API timeout. Is the Labman GUI frozen?"
            )
        return status
