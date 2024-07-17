"""This module contains the code for recovering powder."""

import time
from threading import Thread
from traceback import format_exc
from typing import TYPE_CHECKING

from alab_example.devices.ball_dispenser import EmptyError
from alab_example.devices.robot_arm_characterization import RobotArmCharacterization
from alab_example.devices.robot_arm_furnaces import RobotArmFurnaces
from pydantic import BaseModel, Extra, Field, ValidationError

from alab_management import BaseTask

from .moving import Moving

if TYPE_CHECKING:
    from alab_example.devices.ball_dispenser import BallDispenser
    from alab_example.devices.cap_dispenser import CapDispenser
    from alab_example.devices.capping_gripper import CappingGripper
    from alab_example.devices.scale import Scale
    from alab_example.devices.shaker import Shaker
    from alab_example.devices.vial_dispenser_rack import VialDispenserRack


class RecoverPowderResult(BaseModel, extra=Extra.forbid):
    """A dataclass to represent the result of a RecoverPowder task."""

    initial_crucible_weight: float = Field(
        default=None,
        description="The initial weight of the crucible before powder recovery.",
    )

    weight_collected: float = Field(
        default=None,
        description="The weight of powder collected during the recovery process.",
    )


class RecoverPowder(BaseTask):
    """A task to recover powder from a crucible. This task is designed to be run in series, one sample at a time."""

    def __init__(self, *args, **kwargs):
        """Initialize the RecoverPowder task.

        Args:
            manual_recovery (bool, optional): Flag indicating manual recovery. Defaults to False.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.sample = self.samples[0]

    def validate(self):
        """Validate the RecoverPowder task."""
        return True

    def run(self):
        """A task implementation to RecoverPowder in series -- only one sample at a time!
        Assumes the crucible starts in the tranfer_rack. Ends by disposing of the crucible, and moving the capped vial
        to the filled_vial_rack.
        """
        if (
            self.lab_view.get_sample(self.sample).position
            != "powdertransfer_crucible_position"
        ):
            with self.lab_view.request_resources(
                {"transfer_rack": {"slot": 1}, RobotArmFurnaces: {}}
            ) as (
                _,
                sample_positions,
            ):
                transfer_rack_position = sample_positions["transfer_rack"]["slot"][0]

                self.set_message("Moving the crucible to transfer rack.")
                self.run_subtask(
                    Moving,
                    sample=self.sample,
                    destination=transfer_rack_position,
                )

            self.set_message("Moving the crucible to powdertransfer position.")
            self.run_subtask(
                Moving,
                sample=self.sample,
                destination="powdertransfer_crucible_position",
            )

        self.set_message(
            "Waiting for all the powder recovery devices to be available..."
        )
        with self.lab_view.request_resources(
            {
                "dispenser_balls": {"slot": 1},
                "dispenser_caps": {},
                "shaker": {"slot": 1},
                "scale": {"slot": 1},
                None: {
                    "powdertransfer_crucible_position": 1,
                    "powdertransfer_vial_position": 1,
                    "cap_position": 2,
                    "filled_vial_rack": 1,
                },
                "cappinggripper": {"slot": 1},
                "fresh_vial_rack": {},
            }
        ) as (devices, sample_positions):
            # Note: we reserve all devices and samplepositions required for the duration of this task.
            # This blocks nearly any parallelization on the characterization side. Resources are also
            # requested within the individual methods as futureproofing in case we want to parallelize
            # the individual steps. For now, requesting resources that are already allocated to the task is
            # essentially a no-op.
            powdertransfer_crucible_position = sample_positions[None][
                "powdertransfer_crucible_position"
            ][0]

            for i in range(3):
                self.set_message("Taking the initial crucible mass.")
                initial_crucible_weight = self.weigh_the_crucible()
                if initial_crucible_weight != -9e-5:
                    break
                if i == 2:
                    raise TimeoutError("Timeout error keep happening, abort.")
                self.set_message("Initial weighing timeout, retrying.")
                response = self.lab_view.request_user_input(
                    prompt="The balance takes too long time to stabilize.\n"
                    "(1) Put the robot arm to vertical_start position.\n"
                    f"(2) Put crucible to {powdertransfer_crucible_position}",
                    options=["Continue", "Abort"],
                )
                if response == "Abort":
                    raise TimeoutError("Manually abort by user.")

            if initial_crucible_weight > 1000:
                self.set_message(
                    f"Initial crucible mass: {initial_crucible_weight / 1000:.3f} g."
                )
            else:
                self.set_message(
                    f"Initial crucible mass: {initial_crucible_weight} mg."
                )

            self.set_up_shaking()

            self.set_message("Starting to shake the crucible for two minutes.")
            shaker = devices["shaker"]
            shaking_thread = Thread(target=lambda: shaker.shake(duration_seconds=120))
            shaking_thread.start()

            self.set_message("Getting a fresh vial and logging the barcode.")
            self.get_fresh_vial_and_remove_the_cap()

            shaking_thread.join(timeout=60)  # wait for shaking to finish

            self.after_shaking()

            self.transfer_powder_from_crucible_to_vial()  # Note the vial is uncapped at this point

            for i in range(3):
                self.set_message("Taking the final crucible mass.")
                final_crucible_weight = self.weigh_the_crucible(dispose_after=True)
                if final_crucible_weight != -9e-5:
                    break
                if i == 2:
                    raise TimeoutError("Timeout error keep happening, abort.")
                self.set_message("Final weighing timeout, retrying.")
                response = self.lab_view.request_user_input(
                    prompt="The balance takes too long time to stabilize.\n"
                    "(1) Put the robot arm to vertical_start position.\n"
                    f"(2) Put crucible to {powdertransfer_crucible_position}",
                    options=["Continue", "Abort"],
                )
                if response == "Abort":
                    raise TimeoutError("Abort by user.")

            self.put_cap_back_on_vial()

            weight_collected = initial_crucible_weight - final_crucible_weight
            self.set_message(f"{weight_collected:.1f} mg of powder was collected.")

            sample_result = {
                "weight_collected": weight_collected,
                "initial_crucible_weight": initial_crucible_weight,
            }

            try:
                RecoverPowderResult(**sample_result)
            except ValidationError as e:
                self.set_message(
                    "Error: The results do not match the RecoverPowderResult schema. Please contact the developer."
                )
                raise e

            self.lab_view.update_sample_metadata(
                self.sample, {"recoverpowder_results": sample_result}
            )

            return sample_result

    def weigh_the_crucible(self, dispose_after: bool = False):
        """Weighs the crucible+contents and returns the weight in milligrams.
        Assumes the crucible is in slot "cru_B". Returns the crucible here at the end.

        If dispose_after is True, the crucible is disposed of after weighing.
        """
        with self.lab_view.request_resources(
            {
                RobotArmCharacterization: {},
                "scale": {"slot": 1},
                None: {"powdertransfer_crucible_position": 1},
            }
        ) as (
            devices,
            positions,
        ):
            arm: RobotArmCharacterization = devices[RobotArmCharacterization]
            scale: Scale = devices["scale"]

            arm.run_programs(
                [
                    "vertical_to_horizonal.urp",
                    "pick_cru_B.urp",
                    "before_weighing.urp",
                ]
            )
            # if disposing, the sample (powder) has already been removed from the crucible.
            # otherwise, we will record the sample movement to the database.
            if not dispose_after:
                self.lab_view.move_sample(
                    sample=self.sample,
                    position=positions["scale"]["slot"][0],
                )
            time.sleep(5)  # allow scale to stabilize
            try:
                mass_in_mg = scale.get_mass_in_mg()
            except TimeoutError:
                return -9e-5
            if dispose_after:
                try:
                    arm.run_programs(
                        [
                            "after_weighing.urp",
                            "place_cru_B.urp",  # horizontal
                            "horizonal_to_vertical.urp",
                            "pick_transfer_rack_B.auto.urp",  # vertical
                            "dispose.urp",
                        ]
                    )
                except Exception:
                    response = self.lab_view.request_user_input(
                        prompt=f"Fail to dispose.\n"
                        f"(1) dispose manually from the balance/"
                        f"crucible_transfer_position/robot_char_gripper;\n"
                        f"(2) put the robot arm back to vertical_start position.\n"
                        f"The error message is: {format_exc()}",
                        options=["Continue", "Cancel"],
                    )
                    if response == "Cancel":
                        raise
            else:
                try:
                    arm.run_programs(
                        [
                            "after_weighing.urp",
                            "place_cru_B.urp",
                            "horizonal_to_vertical.urp",
                        ]
                    )
                except Exception:
                    response = self.lab_view.request_user_input(
                        prompt=f"Fail to place the crucible back.\n"
                        f"(1) put the robot arm back to vertical_start position.\n"
                        f"(2) put the crucible back to "
                        f"{positions[None]['powdertransfer_crucible_position'][0]}.\n"
                        f"The error message is: {format_exc()}",
                        options=["Continue", "Cancel"],
                    )
                    if response == "Cancel":
                        raise

                self.lab_view.move_sample(
                    sample=self.sample,
                    position=positions[None]["powdertransfer_crucible_position"][0],
                )

        return mass_in_mg

    def set_up_shaking(self):
        """Takes a crucible from position B, adds a milling ball + lid, places it in the shaker position."""
        threads = []
        with self.lab_view.request_resources(
            {
                RobotArmCharacterization: {},
                "dispenser_balls": {"slot": 1},
                "dispenser_caps": {},
                "shaker": {"slot": 1},
                None: {"powdertransfer_crucible_position": 1},
            }
        ) as (devices, positions):
            print("Method RobotArmCharacterization:", RobotArmCharacterization)
            arm: RobotArmCharacterization = devices[RobotArmCharacterization]
            shaker: Shaker = devices["shaker"]
            capdispenser: CapDispenser = devices["dispenser_caps"]
            balldispenser: BallDispenser = devices["dispenser_balls"]

            self.set_message(
                "Preparing the crucible for grinding in the vertical shaker. Adding a milling ball to the crucible."
            )
            for _ in range(5):
                try:
                    arm.run_programs(
                        [
                            "vertical_to_horizonal.urp",
                            # add balls to crucible
                            "pick_cru_B.urp",  # TODO what is B here
                            "before_ball_dispensing.urp",  # what is this
                        ]
                    )
                    self.lab_view.move_sample(
                        sample=self.sample,
                        position=positions["dispenser_balls"]["slot"][0],
                    )
                    balldispenser.dispense_one()
                except EmptyError:
                    arm.run_programs(
                        [
                            "after_ball_dispensing.urp",
                            "place_cru_B.urp",  # TODO what is B here
                            # add cap to crucible
                            "horizonal_to_vertical.urp",
                        ]
                    )
                    self.lab_view.move_sample(
                        sample=self.sample,
                        position=positions[None]["powdertransfer_crucible_position"][0],
                    )
                    balldispenser.request_refill()
                else:
                    break
            self.set_message("Milling ball added!")

            opencapthread = Thread(target=lambda: capdispenser.open_normal_cap())
            opencapthread.start()

            self.set_message("Putting a lid onto the crucible prior to shaking.")
            arm.run_programs(
                [
                    "after_ball_dispensing.urp",
                    "place_cru_B.urp",  # TODO what is B here
                    # add cap to crucible
                    "horizonal_to_vertical.urp",
                ]
            )
            self.lab_view.move_sample(
                sample=self.sample,
                position=positions[None]["powdertransfer_crucible_position"][0],
            )

            opencapthread.join()  # wait for cap to open

            for i in range(3):
                try:
                    arm.run_programs(
                        [
                            "pick_cap_dispenser_A.urp",
                        ]
                    )
                except Exception:
                    if i == 0:
                        try:
                            # try moving robot back to vertical start, close cap dispenser, push the caps down using
                            # robot arm and retry
                            arm.clear_popup()
                            time.sleep(3)
                            arm.run_programs(["recover_cap_dispenser_A_1.urp"])
                            capdispenser.close_normal_cap()
                            arm.run_programs(["recover_cap_dispenser_A_2.urp"])
                            capdispenser.open_normal_cap()
                        except Exception:
                            response = self.lab_view.request_user_input(
                                prompt="Failed to get a normal cap and automatic recovery failed.\n"
                                f"(1) Put a normal cap to the cap dispenser A\n"
                                f"(2) Set the robot arm back to vertical start\n"
                                f"The error information is {format_exc()}",
                                options=["Retry", "Abort"],
                            )
                            if response == "Abort":
                                raise
                    if i == 1:
                        response = self.lab_view.request_user_input(
                            prompt="Failed to get a normal cap and automatic recovery did not help.\n"
                            f"(1) Put a normal cap to the cap dispenser A\n"
                            f"(2) Set the robot arm back to vertical start\n"
                            f"The error information is {format_exc()}",
                            options=["Retry", "Abort"],
                        )
                        if response == "Abort":
                            raise
                    if i == 2:
                        raise
                else:
                    break

            arm.run_programs(["place_cap_cru_B.urp"])

            thread = Thread(target=lambda: capdispenser.close_normal_cap())
            thread.start()
            threads.append(thread)

            shaker.release()

            self.set_message("Moving the crucible to the shaker.")
            for i in range(3):
                try:
                    arm.run_programs(
                        [
                            "vertical_to_horizonal.urp",
                            # send to shaker
                            "pick_cru_B.urp",
                        ]
                    )
                    try:
                        arm.run_programs(
                            [
                                "before_shaking_cru.urp",
                            ]
                        )
                    except Exception:
                        arm.clear_popup()
                        time.sleep(3)
                        arm.run_programs(
                            [
                                "shaker_loading_error_recovery_1.urp",
                            ]
                        )
                        shaker.shake(duration_seconds=10, grab=False)
                        shaker.release()
                        arm.run_programs(
                            [
                                "shaker_loading_error_recovery_2.urp",
                            ]
                        )
                    arm.run_programs(
                        [
                            "horizonal_to_vertical.urp",
                        ]
                    )
                except Exception:
                    if i == 2:
                        raise
                    response = self.lab_view.request_user_input(
                        prompt="Failed to load crucible to the shaker and failed to automatically recover.\n"
                        f"(1) Put the crucible on powdertransfer_crucible_position\n"
                        f"(2) Set the robot arm back to vertical start\n"
                        f"The error information is {format_exc()}",
                        options=["Retry", "Abort"],
                    )
                    if response == "Abort":
                        raise
                else:
                    break

            self.lab_view.move_sample(
                sample=self.sample,
                position=positions["shaker"]["slot"][0],
            )

        for thread in threads:
            thread: Thread
            thread.join()

    def get_fresh_vial_and_remove_the_cap(self):
        """
        Retrieves a fresh vial and removes its cap.
        The cap is placed in slot B, and the vial is
        left in the dumping position.
        """
        with self.lab_view.request_resources(
            {
                RobotArmCharacterization: {},
                "cappinggripper": {"slot": 1},
                "fresh_vial_rack": {},
                None: {"powdertransfer_vial_position": 1},
            }
        ) as (
            devices,
            positions,
        ):
            arm: RobotArmCharacterization = devices[RobotArmCharacterization]
            freshvialrack: VialDispenserRack = devices["fresh_vial_rack"]
            cappinggripper: CappingGripper = devices["cappinggripper"]

            self.set_message("Getting a fresh vial.")
            rack, index = freshvialrack.get_vial()
            cappinggripper.open()  # sanity check, should already be open
            for i in range(3):
                try:
                    arm.run_programs(
                        [
                            f"pick_vial_rack_{rack}_{index}.auto.urp",
                            "place_dumping_station.auto.urp",
                        ]
                    )
                except Exception:
                    if i == 2:
                        raise
                    response = self.lab_view.request_user_input(
                        prompt="Failed to get a clean vial.\n"
                        f"(1) Put a clean vial to the rack {rack} slot {index}\n"
                        f"(2) Set the robot arm back to vertical start\n"
                        f"The error information is {format_exc()}",
                        options=["Retry", "Abort"],
                    )
                    if response == "Abort":
                        raise
                else:
                    break

            freshvialrack.consume_vial(rack, index)

            cappinggripper.open()
            arm.run_programs(
                ["move_vial_dumping_capper.urp"]
            )  # move fresh vial to capper

            self.set_message("Removing the original cap from the fresh vial.")
            cappinggripper.close()
            try:
                arm.run_programs(
                    [
                        "decapping.urp",
                        "place_cap_B.urp",
                    ]
                )
            except Exception:
                response = self.lab_view.request_user_input(
                    prompt=f"Decapping failed.\n"
                    f"(1) Decap it manually and put the cap on slot B;\n"
                    f"(2) Set the robot arm to vertical_start position.\n"
                    f"The error information is {format_exc()}",
                    options=["Continue", "Abort"],
                )
                if response == "Abort":
                    raise
            cappinggripper.open()

            self.set_message("Moving the decapped vial to the dumping position.")
            try:
                arm.run_programs(
                    [
                        "move_vial_capper_dumping.urp",
                        # send vial to tapping station
                        "vertical_to_horizonal.urp",
                        "pick_vial_dumping_station.urp",
                        "place_vial_tapping_station.urp",
                        "horizonal_to_vertical.urp",
                    ]
                )
            except Exception:
                response = self.lab_view.request_user_input(
                    prompt=f"Failed to move vial from capper to tapping station.\n"
                    f"(1) Put the vial in capper/powdertransfer_vial_position to tapping position;\n"
                    f"(2) Set the robot arm to vertical_start position.\n"
                    f"The error information is {format_exc()}",
                    options=["Continue", "Abort"],
                )
                if response == "Abort":
                    raise

    def after_shaking(self):
        """
        Assumes the crucible has finished shaking, but is still on the shaker.
        Moves the crucible back to the powdertransfer position and disposes of the cap.
        """
        self.set_message("Cleaning up after shaking the crucible.")
        with self.lab_view.request_resources(
            {
                RobotArmCharacterization: {},
                None: {
                    "powdertransfer_crucible_position": 1,
                },
            }
        ) as (
            devices,
            positions,
        ):
            arm: RobotArmCharacterization = devices[RobotArmCharacterization]

            try:
                arm.run_programs(
                    [
                        "vertical_to_horizonal.urp",
                        "after_shaking_cru.urp",
                        "place_cru_B.urp",
                        "horizonal_to_vertical.urp",
                    ]
                )
            except Exception:
                response = self.lab_view.request_user_input(
                    prompt=f"Failed to unload the crucible from the shaker.\n"
                    f"(1) Move the crucible manually to powdertransfer_crucible_position;\n"
                    f"(2) Set the robot arm to vertical_start position.\n"
                    f"The error information is {format_exc()}",
                    options=["Continue", "Abort"],
                )
                if response == "Abort":
                    raise

            self.lab_view.move_sample(
                sample=self.sample,
                position=positions[None]["powdertransfer_crucible_position"][0],
            )
            try:
                arm.run_programs(
                    [
                        # remove cap from crucible
                        "pick_cap_cru_B.urp",
                        "dispose.urp",
                    ]
                )
            except Exception:
                response = self.lab_view.request_user_input(
                    prompt=f"Failed to dispose the cap on the crucible.\n"
                    f"(1) Move the cap on the crucible to the trash bin;\n"
                    f"(2) Set the robot arm to vertical_start position.\n"
                    f"The error information is {format_exc()}",
                    options=["Continue", "Abort"],
                )
                if response == "Abort":
                    raise

    def transfer_powder_from_crucible_to_vial(self):
        """
        After shaking, transfers the contents of the crucible to the fresh vial.
        Assumes the crucible is in position B and the vial is in the dumping position.
        Dumps into the vial, then moves both crucible and vial over to the shaker to
        tap the remaining contents into the vial. Disposes of the crucible cap, returns
        the vial to the dumping position, and returns the crucible to position B.
        """
        with self.lab_view.request_resources(
            {
                RobotArmCharacterization: {},
                "shaker": {"slot": 1},
                None: {
                    "powdertransfer_vial_position": 1,
                    "vial_tapping_position": 1,
                },
            }
        ) as (
            devices,
            positions,
        ):
            arm: RobotArmCharacterization = devices[RobotArmCharacterization]
            shaker: Shaker = devices["shaker"]
            powdertransfer_vial_position = positions[None][
                "powdertransfer_vial_position"
            ][0]
            vial_tapping_position = positions[None]["vial_tapping_position"][0]

            self.set_message(
                "Setting up to dump + tap the crucible into the vial to collect remaining powder."
            )
            for i in range(3):
                try:
                    arm.run_programs(
                        [
                            # send crucible to shaker
                            "vertical_to_horizonal.urp",
                            "pick_cru_B.urp",
                            "before_tapping.urp",
                        ]
                    )
                except Exception:
                    if i == 2:
                        raise

                    response = self.lab_view.request_user_input(
                        prompt=f"Fail to pick the crucible for tapping:\n"
                        f"(1) Put the crucible back to powdertransfer_crucible_position;\n"
                        f"(2) Set the robot arm to vertial_start position.\n"
                        f"The error information is {format_exc()}",
                        options=["Retry", "Abort"],
                    )
                    if response == "Abort":
                        raise
                else:
                    break

            self.set_message(
                "Tapping the crucible contents into the vial for 15 seconds."
            )
            self.lab_view.move_sample(
                sample=self.sample,
                position=vial_tapping_position,
            )  # sample has been transferred into the vial

            shaker.shake(duration_seconds=15, grab=False)

            self.set_message("Cleaning up after tapping.")
            try:
                arm.run_programs(
                    [
                        "after_tapping.urp",
                        "place_cru_B.urp",
                        # take the vial back to dumping station
                        "pick_vial_tapping_station.urp",
                        "place_vial_dumping_station.urp",
                        "horizonal_to_vertical.urp",
                    ]
                )
            except Exception:
                response = self.lab_view.request_user_input(
                    prompt=(
                        "Fail to put the crucible back to powdertransfer_crucible_position.\n"
                        "(1) Put the crucible on tapping_position/robot_arm_gripper manually back to "
                        "powdertransfer_crucible_position;\n"
                        "(2) Put the vial on the recalibration position.\n"
                        "(3) Set the robot arm to vertical_start position.\n"
                        f"The error information is {format_exc()}"
                    ),
                    options=["Continue", "Abort"],
                )
                if response == "Abort":
                    raise

            self.lab_view.move_sample(
                sample=self.sample, position=powdertransfer_vial_position
            )  # the powder is now in the vial, and the vial is in the powdertransfer position

    def put_cap_back_on_vial(self):
        """
        Assumes the vial is in the dumping position. Puts the cap back
        on the vial, then moves the vial to the vial_rack.
        """
        with self.lab_view.request_resources(
            {
                RobotArmCharacterization: {},
                "cappinggripper": {"slot": 1},
                None: {"filled_vial_rack": 1},
            }
        ) as (
            devices,
            positions,
        ):
            arm: RobotArmCharacterization = devices[RobotArmCharacterization]
            cappinggripper: CappingGripper = devices["cappinggripper"]

            cappinggripper_position = positions["cappinggripper"]["slot"][0]
            filled_vial_rack_position = positions[None]["filled_vial_rack"][0]

            self.set_message("Putting the cap back on the vial.")
            cappinggripper.open()  # sanity check, should be open already

            arm.run_programs(
                [
                    "move_vial_dumping_capper.urp",
                ]
            )

            self.lab_view.move_sample(
                sample=self.sample,
                position=cappinggripper_position,
            )

            closethread = Thread(target=lambda: cappinggripper.close())
            closethread.start()

            try:
                arm.run_programs(
                    [
                        "pick_cap_B.urp",
                    ]
                )
                closethread.join()
                arm.run_program("capping.urp")
            except Exception:
                response = self.lab_view.request_user_input(
                    prompt="The capping program failed.\n"
                    "(1) Cap the cap manually to the vial\n"
                    "(2) Set remote arm to the vertical_start position.\n"
                    f"The error information is {format_exc()}",
                    options=["Continue", "Abort"],
                )
                if response == "Abort":
                    raise
            cappinggripper.open()

            self.set_message(
                "Storing the capped vial containing powder on the filled vial rack."
            )

            self.run_subtask(
                Moving,
                sample=self.sample,
                destination=filled_vial_rack_position,
            )
