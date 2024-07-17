"""This module contains the PowderDosing task."""

from __future__ import annotations

import copy
import time
from typing import TYPE_CHECKING, Literal, TypedDict
from unittest.mock import Mock

from alab_control.labman import InputFile, LabmanView, QuadrantStatus
from alab_control.labman.api.api import LabmanAPI
from alab_example.devices.robot_arm_furnaces import RobotArmFurnaces
from pydantic import BaseModel, Extra, Field, ValidationError

from alab_management import BaseTask
from alab_management.device_view.device import mock
from alab_management.task_view.task_enums import TaskPriority

if TYPE_CHECKING:
    from alab_example.devices.labman_quadrant import LabmanQuadrant
    from bson import ObjectId


class PowderItem(TypedDict):
    """Schema for the PowderItem for the PowderDosingSampleResult schema."""

    PowderName: str | None = Field(
        default=None,
        description="The name of the powder.",
    )
    TargetMass: float | None = Field(
        default=None, description="The target mass of the powder.", ge=0
    )
    Doses: list[dict] | None = Field(
        default=None,
        description="The doses of the powder.",
    )


class PowderDosingSampleResult(BaseModel, extra=Extra.forbid):
    """Schema for the PowderDosing task result for a sample."""

    ActualHeatDuration: int | None = Field(
        default=None, description="The actual heat duration in seconds.", ge=0
    )

    ActualTransferMass: float | None = Field(
        default=None,
        description="The actual mass of slurry transferred in grams.",
        ge=0,
    )

    CruciblePosition: int | None = Field(
        default=None, description="The crucible position in the subrack.", ge=1, le=4
    )

    CrucibleSubRack: Literal["SubRackA", "SubRackB", "SubRackC", "SubRackD"] | None = (
        Field(
            default=None,
            description="The crucible subrack.",
        )
    )

    DACDuration: int | None = Field(
        default=None, description="The duration of the mixing in seconds.", ge=0
    )

    DACSpeed: int | None = Field(
        default=None, description="The speed of the DAC in RPM.", ge=0
    )

    EndReason: str | None = Field(
        default=None,
        description="The reason the sample workflow ended.",
    )

    EthanolDispenseVolume: int | None = Field(
        default=None,
        description="The volume of ethanol dispensed in microliters.",
        ge=0,
    )

    MixingPotPosition: int | None = Field(
        default=None, description="The mixing pot position.", ge=1, le=16
    )

    Powders: list[PowderItem] | None = Field(
        default=None,
        description="The powders used in the workflow.",
    )

    TargetTransferVolume: int | None = Field(
        default=None, description="The target transfer volume in microliters.", ge=0
    )

    TransferTime: str | None = Field(
        default=None,
        description="The date and time of the transfer.",
    )


class WorkflowResults(BaseModel, extra=Extra.forbid):
    """Schema for the results from the Labman API query."""

    Rows: list[PowderDosingSampleResult] | None = Field(
        default=None,
        description="The results for each sample.",
    )

    WorkflowName: str | None = Field(
        default=None,
        description="The name of the workflow.",
    )


class RawResults(BaseModel, extra=Extra.forbid):
    """Schema for the raw results from the Labman API query."""

    IndexingRackQuadrant: int | None = Field(
        default=None, description="The indexing rack quadrant."
    )

    Results: WorkflowResults | None = Field(
        default=None, description="The results from the workflow."
    )


class PowderDosingResult(BaseModel, extra=Extra.forbid):
    """Schema for the PowderDosing task result."""

    raw_results: RawResults | None = Field(
        default=None,
        description="The raw results from the Labman API query.",
    )

    results_per_sample: dict[str, PowderDosingSampleResult] | None = Field(
        default=None,
        description="The results for each sample.",
    )

    mixingpot_to_sample: dict[int, list[str]] | None = Field(
        default=None,
        description="The list of samples derived from each mixing pot.",
    )

    time_elapsed_seconds: float | None = Field(
        default=None,
        description="The time elapsed in seconds for the whole task.",
    )


class PowderDosing(BaseTask):
    """Task to instruct the Labman to dose + mix powders into crucibles."""

    def __init__(
        self,
        inputfiles: dict[str | ObjectId, dict],
        *args,
        **kwargs,
    ):
        """Initialize the PowderDosing task.

        Args:
            inputfiles (dict[Union[str, ObjectId], dict]): Dictionary mapping samples to inputfiles in json format.
                Format: {sample_name: inputfile_json, sample_name2: inputfile_json2, ...}
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        priority = kwargs.pop("priority", TaskPriority.HIGH)
        super().__init__(priority=priority, *args, **kwargs)  # noqa
        self.inputfiles = inputfiles
        self.num_samples = len(self.samples)
        self.labman_view, self.labmanview_api = self.get_driver()

        if isinstance(self.labmanview_api, Mock):
            self.labmanview_api.get_results = lambda workflow_name: {
                "IndexingRackQuadrant": 1,
                "Results": {
                    "Rows": [
                        {
                            "ActualHeatDuration": 16,
                            "ActualTransferMass": 7.6514,
                            "CruciblePosition": (i % 4) + 1,
                            "CrucibleSubRack": f"SubRack{chr(65 + i // 4)}",
                            "DACDuration": 10,
                            "DACSpeed": 2000,
                            "EndReason": "Completed",
                            "EthanolDispenseVolume": 10000,
                            "MixingPotPosition": i + 1,
                            "Powders": [
                                {
                                    "PowderName": "Li2CO3",
                                    "TargetMass": 0.1,
                                    "Doses": [
                                        {
                                            "HeadPosition": 13,
                                            "Mass": 0.099165,
                                            "TimeStamp": "2023-02-03T20:38:50.0000000",
                                        }
                                    ],
                                }
                            ],
                            "TargetTransferVolume": 10000,
                            "TransferTime": "2023-02-03T20:45:44.0000000",
                        }
                        for i in range(self.num_samples)
                    ],
                    "WorkflowName": workflow_name,
                },
            }

    @mock(object_type=[LabmanView, LabmanAPI])
    def get_driver(self):
        """Get the Labman driver.

        Returns:
            tuple: A tuple containing the LabmanView instance and the LabmanAPI instance.
        """
        self.labman_view = LabmanView()
        return self.labman_view, self.labman_view.API

    def validate(self):
        """
        Validate the PowderDosing task.

        Raises:
            ValueError: If the number of samples is not between 1 and 16, or if the number of inputfiles does not match
            the number of samples, or if the inputfile JSON is invalid.
        """
        if not 1 <= len(self.samples) <= 16:
            raise ValueError("Number of samples must be between 1 and 16!")

        if len(self.inputfiles) != len(self.samples):
            raise ValueError(
                f"Number of inputfiles {len(self.inputfiles)} must match number of samples {self.num_samples}!"
            )
        for sample, inputfile in self.inputfiles.items():
            try:
                inp = InputFile.from_json(inputfile)
                if inp.replicates != 1:
                    raise ValueError(
                        "Replicates must be 1 for inputfiles within the PowderDosing task!"
                    )
            except Exception as e:
                raise ValueError(
                    f"Inputfile json for sample {sample} is invalid! Error: {e}"
                ) from e

        return True

    def _get_username(self) -> str:
        """Get the name of the user involved with this task. Looks for a sample metadata field ['user']. If not found,
        returns 'Not Specified'. If multiple samples with different users, returns the user with the most samples.
        """
        users = {}  # name: sample_count
        for sample_name in self.samples:
            sample_entry = self.lab_view.get_sample(sample_name)
            metadata = getattr(
                sample_entry, "metadata", {}
            )  # sample_entry is a dataclass, not dict! thats why getattr
            name = metadata.get("user", None)
            if name:
                users[name] = users.get(name, 0) + 1

        return "Not Specified" if len(users) == 0 else max(users, key=users.get)

    @mock(return_constant=(1, "labmanquadrant_1"))
    def get_available_quadrant(self) -> tuple[int, str]:
        """
        Returns the index of the first available quadrant, and the name of that quadrant device.

        (index, name)
        """
        # TODO race condition
        while True:
            for quadrant_index in [1, 2, 3, 4]:
                if (
                    self.labman_view.get_quadrant_status(quadrant_index)
                    == QuadrantStatus.EMPTY
                ):
                    quadrant_name = f"labmanquadrant_{quadrant_index}"
                    return quadrant_index, quadrant_name
            time.sleep(1)

    @mock(return_constant=None)
    def assert_quadrant_is_empty(self, quadrant_index: int):
        """Raises an error if the quadrant is not empty."""
        if self.labman_view.get_quadrant_status(quadrant_index) != QuadrantStatus.EMPTY:
            raise ValueError(f"Labman Quadrant {quadrant_index} is not empty!")

    def run(self):
        """Run the PowderDosing task."""
        self.set_message("Waiting for a Labman quadrant to become available.")

        while True:
            try:
                self.quadrant_index, quadrant_name = self.get_available_quadrant()
                self.set_message(
                    f"Labman quadrant {self.quadrant_index} is now available."
                )

                # reserve the entire quadrant regardless of how many samples are being dosed
                with self.lab_view.request_resources(
                    {
                        quadrant_name: {"jar": 16, "crucible": 16, "processing": 16},
                    },
                    timeout=15,
                ) as (
                    devices,
                    sample_positions,
                ):
                    self.assert_quadrant_is_empty(self.quadrant_index)
                    labmanquadrant: LabmanQuadrant = devices[quadrant_name]
                    self.set_message(
                        f"We now control Labman quadrant {self.quadrant_index}."
                    )

                    # reorganize crucibles if necessary
                    # self.reorganize_crucibles(labman=labmanquadrant) #TODO intraquadrant moves not implemented
                    # on ArmFurnaces yet

                    self.set_message("Submitting workflow to Labman...")
                    workflow_name, mixingpot_to_sample = labmanquadrant.submit_workflow(
                        name=str(self.task_id), inputfiles_as_json=self.inputfiles
                    )

                    # move samples to processing positions. These positions simply indicate that the samples exist
                    # somewhere within the Labman during the workflow. This is important for the LabmanQuadrant, which
                    # needs to know when it is empty (no samples in sample positions) to request cleanup.
                    for sample_id, position in zip(
                        self.samples,
                        sample_positions[quadrant_name]["processing"],
                        strict=True,
                    ):
                        self.lab_view.move_sample(sample=sample_id, position=position)

                    self.set_message(
                        f"Workflow is now running on the Labman Quadrant {self.quadrant_index}!"
                    )

                    t_start = time.time()
                    while labmanquadrant.get_status() != QuadrantStatus.COMPLETE:
                        time.sleep(5)
                        while labmanquadrant.has_error():
                            error_message = labmanquadrant.get_error_message()
                            self.lab_view.request_user_input(
                                prompt=f"Labman has encountered a process error: {error_message}.\n"
                                f"Please resolve the error and say OK to continue.",
                                options=["OK"],
                            )
                    workflow_duration = time.time() - t_start
                    self.set_message(
                        "Workflow is complete! Now retrieving results from the Labman..."
                    )

                    attempt = 0
                    while True:
                        # Labman API freezes at times due to a memory leak. This loop will keep the task alive until
                        # an operator can restart the Labman GUI (which serves the API), at which point the task
                        # will retrieve results and proceed. (Rishi 2023-03-16)
                        try:
                            results = self.labmanview_api.get_results(
                                workflow_name=workflow_name
                            )
                            break
                        except Exception as e:
                            attempt += 1
                            self.set_message(
                                f"Failed to get results from Labman. Error: {e} Retrying (attempt {attempt})..."
                            )
                            time.sleep(30)

                    results_per_sample = self.parse_results(
                        results=results, mixingpot_to_sample=mixingpot_to_sample
                    )
                    for sample_id, sample_result in results_per_sample.items():
                        position = (
                            f"{quadrant_name}/crucible/{sample_result['CrucibleSubRack']}/"
                            f"{sample_result['CruciblePosition']}"
                        )
                        self.lab_view.move_sample(sample=sample_id, position=position)
                        # Check if the sample_result obeys the PowderDosingSampleResult schema
                        try:
                            PowderDosingSampleResult(**sample_result)
                        except ValidationError as e:
                            self.set_message(
                                f"Error: The results for sample {sample_id} do not match the "
                                "PowderDosingSampleResult schema."
                            )
                            raise e
                        self.lab_view.update_sample_metadata(
                            sample_id, {"powderdosing_results": sample_result}
                        )
                    self.set_message("Workflow has been completed.")

                ## Note: changes to the format of the results (in particular, "results_per_sample") will affect
                ## the alab powder inventory.
                # Validate the results format
                task_results = {
                    "raw_results": results,
                    "results_per_sample": results_per_sample,
                    "mixingpot_to_sample": {
                        str(k): v for k, v in mixingpot_to_sample.items()
                    },
                    "time_elapsed_seconds": workflow_duration,
                }
                try:
                    PowderDosingResult(**task_results)
                except ValidationError as e:
                    self.set_message(
                        "Error: The results do not match the PowderDosingResult schema. Please contact the developer."
                    )
                    raise e
                return task_results
            except TimeoutError:
                self.set_message(
                    "Race condition encoutered. Waiting 2 minutes for a quadrant to become available."
                )
                time.sleep(120)

    def reorganize_crucibles(self, labman: LabmanQuadrant):
        """The Labman assumes that crucibles are filled in order from 1 to 16. This may not be the case, for example if
        a workflow using only 10 crucibles was previously run such that 6 crucible remain in the last 6 positions. This
        function will move the crucibles to the correct positions.

        Args:
            labman (Labman): labman device object.
        """
        current_positions = labman.driver.quadrants[
            self.quadrant_index
        ].available_crucibles
        current_positions = sorted(current_positions)  # this may be redundant

        num_crucibles_required = sum(
            inputfile["CrucibleReplicates"] for inputfile in self.workflow["InputFiles"]
        )
        desired_positions = list(range(num_crucibles_required))
        if len(desired_positions) > len(current_positions):
            raise ValueError(
                "There are not enough crucibles in the quadrant to run this workflow!"
            )  # TODO maybe user request?

        transfers = []  # list of tuples (from, to)
        for desired in desired_positions:
            if desired not in current_positions:
                # move the last crucible to the desired position
                transfers.append((current_positions.pop(-1), desired))
        if len(transfers) == 0:
            return  # nothing to do here

        # TODO move crucibles

        self.set_message(
            "We need to reorganize the crucibles for the Labman workflow. Waiting for the robot arm \n"
            "to become available..."
        )
        with self.lab_view.request_resources({RobotArmFurnaces: {}}) as (
            devices,
            sample_positions,
        ):
            arm: RobotArmFurnaces = devices[RobotArmFurnaces]
            self.set_message(
                "We have the robot arm, now taking control of the Labman quadrant"
            )
            labman.take_quadrant(self.quadrant_index)

            self.set_message("Reorganizing crucibles for the Labman workflow...")
            for source, destination in transfers:
                arm.move_within_labman(source, destination)  # TODO

            self.set_message(
                "Done reorganizing crucibles for the Labman workflow. Releasing the quadrant control back to Labman..."
            )
            labman.release_quadrant()

    def parse_results(
        self, results: dict, mixingpot_to_sample: dict[int, list[str]]
    ) -> dict:
        """Unpacks the results, sorts them by sample_name. This is useful to break replicates into individual samples.

        Args:
            results (dict): raw results from Labman API query
            mixingpot_to_sample (Dict[int, List[str]]): List of samples derived from each mixing pot
                {mixingpot_position: [sample_name1, sample_name2, ...]}

        Returns
        -------
            dict: {sample_name: results dictionary for this crucible}

        """
        results_per_sample: dict[str, dict] = (
            {}
        )  # {sample_name: results dictionary for this crucible}
        deepcopy_mixingpot_to_sample = copy.deepcopy(mixingpot_to_sample)
        for row in results["Results"]["Rows"]:
            pot_position = row["MixingPotPosition"]
            try:
                this_samplename = deepcopy_mixingpot_to_sample[pot_position].pop()
            except (KeyError, IndexError):
                new_mixingpot_to_sample = None
                while new_mixingpot_to_sample is None:
                    response, new_mixingpot_to_sample = (
                        self.lab_view.request_user_input_with_note(
                            prompt=f"mixingpot_to_sample has no sample for pot_position {pot_position}. \n"
                            f"{mixingpot_to_sample} \n"
                            f"Please resolve the error by pasting the new mixingpot_to_sample"
                            f"into the note the list. \n"
                            f"Click OK to continue.",
                            options=["OK", "Cancel"],
                        )
                    )
                if response == "Cancel":
                    raise ValueError("User cancelled the task.")
                # check the new_mixingpot_to_sample
                try:
                    mixingpot_to_sample = eval(new_mixingpot_to_sample)
                    assert isinstance(mixingpot_to_sample, dict)
                except Exception as e:
                    raise ValueError(
                        f"Error: {e}. The inserted mixingpot_to_sample is not a valid dictionary."
                    ) from e

            results_per_sample[this_samplename] = row

        ## Note: changes to the format of results_per_sample will affect the ALab One powder inventory.
        return results_per_sample
