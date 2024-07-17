"""This module contains the Ending task for the ALab One project."""

from __future__ import annotations

import os
import re
from importlib import util
from pathlib import Path
from traceback import format_exc, print_exc

import cv2
import zxingcpp
from alab_example.devices.robot_arm_characterization import RobotArmCharacterization
from alab_example.devices.vial_labeler import VialLabeler
from alab_example.tasks.moving import Moving
from pydantic import BaseModel, Extra, Field, ValidationError

from alab_management import BaseTask
from alab_management.config import AlabOSConfig
from alab_management.device_view.device import mock

IS_SIM_MODE = AlabOSConfig().is_sim_mode()
REMOTE_PHOTO_FOLDER = "/programs/output"


@mock(return_constant=Path(__file__).parent / "QR_codes")
def QR_CODE_FOLDER():
    """Return the path to the folder where the QR codes are stored."""
    return Path("D:\\QR_codes")


class EndingResult(BaseModel, extra=Extra.forbid):
    """Ending task result."""

    decoded_sample_id: str | None = Field(
        default=None,
        description="Decoded sample ID from the QR code.",
    )

    successful_labeling: bool | None = Field(
        default=None,
        description="Whether the labeling of the filled vial was successful.",
    )


class Ending(BaseTask):
    """This class is a task called at the conclusion of an A-Lab workflow and features the labeling and storage of a
    filled vial sample.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the Ending task."""
        super().__init__(*args, **kwargs)
        self.decoded_sample_id = None
        self.sample = self.samples[0]
        self.filled_vial_position = None

    def validate(self):
        """Validate the Ending task."""
        if len(self.samples) != 1:
            raise ValueError(
                f"Ending task can only be used with one sample, but {len(self.samples)} were given."
            )
        return True

    def run(self):
        """Run the Ending task."""
        self.filled_vial_position = self.lab_view.get_sample(
            sample=self.sample
        ).position
        if self.filled_vial_position is None:
            # If the filled vial position is none, the sample is not in the lab
            self.set_message(
                f"Sample {self.sample} is not in the system. This might be due to manual powder recovery and "
                "XRD preparation."
            )
            return None
        self.move_vial_to_station()

        successful_labeling = self.print_vial_label()

        if successful_labeling:
            self.store_vial()
        else:
            self.return_to_filled_vial_rack()

        ending_results = {
            "decoded_sample_id": self.decoded_sample_id,
            "successful_labeling": successful_labeling,
        }
        try:
            EndingResult(**ending_results)
        except ValidationError as e:
            self.set_message(
                "Error: The results do not match the EndingResult schema. Please contact the developer."
            )
            raise e

        self.lab_view.update_sample_metadata(
            self.sample, {"ending_results": ending_results}
        )

        return ending_results

    def move_vial_to_station(self):
        """Move filled vial from filled vial rack to powdertransfer_vial_position to prepare for cap labeling."""
        self.set_message(
            "Waiting for filled_vial_rack & powdertransfer_vial_position to be available..."
        )
        with self.lab_view.request_resources(
            {
                RobotArmCharacterization: {},
                None: {"filled_vial_rack": 1, "powdertransfer_vial_position": 1},
            }
        ) as (
            _,
            positions,
        ):
            powdertransfer_vial_position = positions[None][
                "powdertransfer_vial_position"
            ][0]

            self.set_message(
                f"Moving filled vial from position {self.filled_vial_position} ..."
            )
            try:
                self.run_subtask(
                    Moving, sample=self.sample, destination=powdertransfer_vial_position
                )
                self.set_message("Moved filled vial to prepare for labeling.")
            except Exception:
                response = self.lab_view.request_user_input(
                    prompt=f"Failed to move filled vial from {self.filled_vial_position} to "
                    f"{powdertransfer_vial_position}.\n"
                    f"(1) Move filled vial from position {self.filled_vial_position} to "
                    f"{powdertransfer_vial_position}.\n"
                    "(2) Set the robot arm back to vertical start.\n"
                    f"The error information is {format_exc()}",
                    options=["Continue", "Abort"],
                )
                if response == "Abort":
                    raise

    def print_vial_label(self):
        """Print the label onto the filled vial cap."""
        self.set_message("Waiting to print vial label...")
        with self.lab_view.request_resources(
            {
                RobotArmCharacterization: {},
                VialLabeler: {"slot": 1},
                None: {"powdertransfer_vial_position": 1},
            }
        ) as (
            devices,
            positions,
        ):
            arm: RobotArmCharacterization = devices[RobotArmCharacterization]
            vial_labeler: VialLabeler = devices[VialLabeler]

            vial_labeler_slot_position = positions[VialLabeler]["slot"][0]
            powdertransfer_vial_position = positions[None][
                "powdertransfer_vial_position"
            ][0]

            self.set_message(
                "Picking up the filled vial and placing in front of printer..."
            )
            self.run_subtask(
                Moving, sample=self.sample, destination=vial_labeler_slot_position
            )
            self.set_message("Placed vial in front of labeler. Printing label...")

            for i in range(3):
                try:
                    vial_labeler.print_sample_label(
                        self.lab_view.get_sample(sample=self.sample)
                    )
                except Exception:
                    if i == 2:
                        raise
                    # Move the vial back to the powdertransfer vial position
                    self.run_subtask(
                        Moving,
                        sample=self.sample,
                        destination=powdertransfer_vial_position,
                    )
                    response = self.lab_view.request_user_input(
                        prompt=f"Failed to perform vial label printing.\n"
                        f"(1) Check the inkjet printer is functioning.\n"
                        f"(2) Place the vial back on powdertransfer vial position (dumping station).\n"
                        f"(3) Ensure there is a fresh/unmarked cap on the vial.\n"
                        f"(4) Set the robot arm to vertical_start position.\n"
                        f"The error information is: \n\n {format_exc()}",
                        options=["Retry", "Abort"],
                    )
                    if response == "Abort":
                        raise
                    # Move the vial back to the labeler slot
                    self.run_subtask(
                        Moving,
                        sample=self.sample,
                        destination=vial_labeler_slot_position,
                    )
                else:
                    break

            self.run_subtask(
                Moving, sample=self.sample, destination=powdertransfer_vial_position
            )
            self.set_message("Taking photo of QR code...")
            arm.run_program("take_photo.urp")
            self.set_message(
                "Placed labeled vial back to powdertransfer vial position (dumping station)."
            )

            successful_labeling = False
            # Read the QR code from the photo using the (URCap) robot arm program directly
            installation_variables = arm.read_file("/programs/default.variables")
            sample_id_from_photo = re.search(
                r'(?<=current_code=").*(?=")', installation_variables
            ).group()
            if (
                IS_SIM_MODE
            ):  # assume QR code is always read correctly in simulation mode
                sample_id_from_photo = str(
                    self.lab_view.get_sample(sample=self.sample).sample_id
                )
            try:
                # Download and remove the photo from the robot arm memory
                arm.download_folder(
                    remote_folder_path=REMOTE_PHOTO_FOLDER,
                    local_folder_path=QR_CODE_FOLDER().as_posix(),
                    remove_remote_files=True,
                )
                files = os.listdir(QR_CODE_FOLDER().as_posix())
                # Filter out only .jpg files and sort them by modification time
                jpg_files = [
                    file
                    for file in files
                    if (
                        file.lower().endswith(".jpg")
                        and not file.lower().startswith("old")
                    )
                ]
                jpg_files.sort(
                    key=lambda x: os.path.getmtime(
                        os.path.join(QR_CODE_FOLDER().as_posix(), x)
                    )
                )
                # Get the latest dated .jpg file
                latest_file = jpg_files[-1] if jpg_files else None
                # rename the file to be the sample ID
                new_file_name = f"old_{self.lab_view.get_sample(sample=self.sample).sample_id!s}.jpg"
                if latest_file is not None:
                    os.rename(
                        os.path.join(QR_CODE_FOLDER().as_posix(), latest_file),
                        os.path.join(QR_CODE_FOLDER().as_posix(), new_file_name),
                    )
                    latest_file = new_file_name
                else:
                    raise ValueError(
                        "Failed to download QR code photo from robot arm. No new file is present or all the files "
                        "are only old ones."
                    )
            except Exception as e:
                print_exc()
                self.set_message(
                    f"Failed to download QR code photo from robot arm: {e}. Either no new file is present "
                    "or all the files are only old ones."
                )
                latest_file = ""

            if sample_id_from_photo == "" and latest_file != "":
                self.set_message(
                    "Failed to read QR code from photo using the robot arm decoder. Trying zxing."
                )
                try:
                    # Construct the full file path
                    file_path = os.path.join(QR_CODE_FOLDER().as_posix(), latest_file)

                    # Decode the QR code from the image using zxing
                    result = self.decode_image(file_path)

                    if result is not None:
                        # Assume only one QR code is present in the image
                        sample_id_from_photo = result.text
                        self.set_message(f"QR Code Data: {sample_id_from_photo}")
                    else:
                        raise ValueError("No QR code found in the image!")
                except Exception as e:
                    print_exc()
                    self.set_message(f"Failed to read QR code from photo: {e}")
            else:
                self.set_message(
                    f"Detected sample ID from photo: {sample_id_from_photo}"
                )

            self.decoded_sample_id = sample_id_from_photo

            if sample_id_from_photo == str(
                self.lab_view.get_sample(sample=self.sample).sample_id
            ):
                successful_labeling = True
            else:
                if sample_id_from_photo == "":
                    self.set_message(
                        f"Warning! No QR code detected for sample {self.sample}."
                    )
                else:
                    self.set_message(
                        f"Warning: sample ID from photo ({sample_id_from_photo}) does not match "
                        f"the expected sample ID ({self.lab_view.get_sample(sample=self.sample).sample_id})."
                    )

            return successful_labeling

    def store_vial(self):
        """
        Store the filled vial in the storage bin. The algorithm will determine which bin
        to place the sample into; this is based on the project ID of the sample (e.g.,
        PG_1364 --> PG is the project ID).
        """

        def get_project_tags_in_bin(bin_name):
            bin_samples = [
                str(d["name"])
                for d in self.lab_view._sample_view._sample_collection.find(  # pylint: disable=protected-access
                    {"position": {"$regex": f"filled_vial_storage_bin_{bin_name}"}}
                )
            ]
            return {sample.split("_")[0] for sample in bin_samples}

        sample_name = str(self.lab_view.get_sample(sample=self.sample).name)

        designated_bin = None
        if (
            len(sample_name.split("_")) == 1
        ):  # if the sample name is not in the format of projecttag_samplenum
            designated_bin = "C"  # default to bin C always
        else:
            bin_a_project_tags = get_project_tags_in_bin("A")
            bin_b_project_tags = get_project_tags_in_bin("B")
            bin_c_project_tags = get_project_tags_in_bin("C")

            project_tag = sample_name.split("_", maxsplit=1)[0]

            if project_tag in bin_a_project_tags:
                designated_bin = "A"
            elif project_tag in bin_b_project_tags:
                designated_bin = "B"
            elif project_tag in bin_c_project_tags:
                designated_bin = "C"

            if designated_bin is None:
                if len(bin_a_project_tags) == 0:
                    designated_bin = "A"
                elif len(bin_b_project_tags) == 0:
                    designated_bin = "B"
                else:
                    designated_bin = "C"

        with self.lab_view.request_resources(
            {
                RobotArmCharacterization: {},
                None: {
                    f"filled_vial_storage_bin_{designated_bin}": 1,
                    "powdertransfer_vial_position": 1,
                },
            }
        ) as (
            _,
            positions,
        ):
            filled_vial_storage_bin = positions[None][
                f"filled_vial_storage_bin_{designated_bin}"
            ][0]

            self.set_message(
                "Picking up the labeled filled vial and placing in storage bin..."
            )
            try:
                self.run_subtask(
                    Moving, sample=self.sample, destination=filled_vial_storage_bin
                )
            except Exception:
                response = self.lab_view.request_user_input(
                    prompt=f"Failed to move filled vial from labeling position into storage bin.\n"
                    f"(1) Move the filled vial to {filled_vial_storage_bin};\n"
                    f"(2) Set the robot arm to vertical_start position.\n"
                    f"The error information is {format_exc()}",
                    options=["Continue", "Abort"],
                )
                if response == "Abort":
                    raise

            self.set_message("Placed vial in storage bin.")

            # TODO: implement filled vial bin capacity checking

        self.set_message(
            f"Requesting user to remove sample {self.sample} out of the lab"
        )
        response = self.lab_view.request_user_input(
            prompt=f"Remove {self.sample} in {filled_vial_storage_bin} and place in long-term storage.",
            options=["Success", "Error"],
        )
        if response == "Error":
            raise Exception(
                f"User said they were unable to remove {self.sample} in {filled_vial_storage_bin}!"
            )

        self.lab_view.move_sample(
            sample=self.sample,
            position=None,
        )
        self.set_message(
            "Sample was removed from filled vial bin and cleared from A-Lab."
        )

    def return_to_filled_vial_rack(self):
        """Return the filled vial to the filled vial rack if an error in labeling occurs."""
        self.sample = self.samples[0]
        position = self.lab_view.get_sample(sample=self.sample).position

        if self.filled_vial_position is None:
            response = self.lab_view.request_user_input(
                prompt=f"Cannot determine which position to return filled vial to! Remove {self.sample} on {position}",
                options=["Success", "Error"],
            )
            if response == "Error":
                raise Exception(
                    f"User said they were unable to remove {self.sample} on {position}!"
                )
        else:
            with self.lab_view.request_resources(
                {
                    RobotArmCharacterization: {},
                    None: {"filled_vial_rack": 1, "powdertransfer_vial_position": 1},
                }
            ) as (
                devices,
                positions,
            ):
                filled_vial_position = positions[None]["filled_vial_rack"][0]
                self.run_subtask(
                    Moving, sample=self.sample, destination=filled_vial_position
                )

            position = self.lab_view.get_sample(sample=self.sample).position
            self.set_message(
                f"Requesting user to remove sample {self.sample} from {position}."
            )
            response = self.lab_view.request_user_input(
                prompt=f"Warning! Sample ID decoded from photo ({self.decoded_sample_id}) does not match.\n"
                f"Expected sample ID ({self.lab_view.get_sample(sample=self.sample).sample_id}).\n"
                f"Sample requires manual labeling. Remove {self.sample} on {position}.",
                options=["Success", "Error"],
            )
            if response == "Error":
                raise Exception(
                    f"User said they were unable to remove {self.sample} on {position}!"
                )

        self.lab_view.move_sample(
            sample=self.sample,
            position=None,
        )
        self.set_message("Sample was successfully removed.")

    def decode_image(self, file_path: str):
        """Decode the QR code from the image using the zxingcpp library."""
        # Create a QReader instance
        return zxingcpp.read_barcode(cv2.imread(file_path))
