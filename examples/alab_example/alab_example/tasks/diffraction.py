"""This module is responsible for performing XRD diffraction tasks."""

from __future__ import annotations

import time
from threading import Thread
from traceback import format_exc
from typing import TYPE_CHECKING

from alab_example.devices.cap_dispenser import CapDispenser
from alab_example.devices.capping_gripper import CappingGripper
from alab_example.devices.diffractometer import Diffractometer
from alab_example.devices.robot_arm_characterization import RobotArmCharacterization
from pydantic import BaseModel, Field, ValidationError

from alab_management import BaseTask
from alab_management.task_view.task_enums import TaskPriority

if TYPE_CHECKING:
    from alab_example.devices.scale import Scale
    from alab_example.devices.xrd_dispenser_rack import XRDDispenserRack

from .moving import Moving


class DiffractionResult(BaseModel, extra="forbid"):
    """The result of a Diffraction task."""

    mass_per_dispensing_attempt_mg: list[float] | None = Field(
        default=None,
        description="The total mass (mg) of powder dispensed onto the XRD holder per attempt.",
    )
    total_mass_dispensed_mg: float | None = Field(
        default=None,
        description="The total mass (mg) of powder dispensed onto the XRD holder.",
    )
    met_target_mass: bool | None = Field(
        default=None,
        description="True if the mass of powder on the XRD holder is >= the target mass, False otherwise.",
    )
    xrd_holder_index: int | None = Field(
        default=None,
        description="The index of the XRD holder that was used (1-16 on the XRDDispenseRack)",
    )
    sampleid_in_aeris: str | None = Field(
        default=None, description="The sample ID in the Aeris software."
    )
    twotheta: list[float] | None = Field(
        default=None, description="The two-theta values of the XRD scan."
    )
    counts: list[float] | None = Field(
        default=None, description="The counts of the XRD scan."
    )


class Diffraction(BaseTask):
    """takes an XRD scan."""

    def __init__(
        self,
        schema: str = "10-100_8-minutes",
        min_powder_mass: float = 100,
        *args,
        **kwargs,
    ):
        """Takes an XRD scan on the Aeris.

        Args:
            schema (str, optional): Name of the scanning schema. This should correspond to a preset schema on the Aeris.
                Defaults to "10-100_8-minutes".
            min_powder_mass (float, optional): minimum mass (mg) of powder to load onto the XRD holder. The scan will
                proceed whether or not this mass is met -- just sets a flag for us to check. Defaults to 100.
            args: Additional arguments.
            kwargs: Additional keyword arguments.
        """
        super().__init__(priority=TaskPriority.HIGH, *args, **kwargs)  # noqa
        self.scan_schema = schema
        self.min_powder_mass: float = min_powder_mass
        self.sample = self.samples[0]

    def validate(self):
        """Validate the Diffraction task."""
        if len(self.samples) != 1:
            raise ValueError("Number of samples must be 1")
        return True

    def run(self):
        """Run the Diffraction task."""
        preparation_results = self.run_subtask(
            PrepareSampleforXRD,
            sample=self.sample,
            min_powder_mass=self.min_powder_mass,
        )

        slot_idx = preparation_results["xrd_holder_index"]

        # run an XRD scan
        self.set_message("Waiting for the XRD to become available")
        with self.lab_view.request_resources(
            {Diffractometer: {}}  # why need robot arm
        ) as (
            devices,
            _,
        ):
            diffractometer: Diffractometer = devices[Diffractometer]
            self.set_message(
                "XRD is available, now waiting for robot arm to become available."
            )
            with self.lab_view.request_resources(
                {RobotArmCharacterization: {}}, priority=40
            ) as (inner_devices, _):
                arm: RobotArmCharacterization = inner_devices[RobotArmCharacterization]

                self.set_message("Moving the XRD sample holder onto the XRD")
                arm.run_programs(
                    [
                        f"pick_xrd_holder_rack_{slot_idx}.auto.urp",
                        "place_xrd_holder_machine.urp",
                    ]
                )

            self.set_message(f'Scanning XRD with schema "{self.scan_schema}".')

            for i in range(3):
                try:
                    scan_results = diffractometer.run_scan(
                        sample_name=self.sample, schema=self.scan_schema
                    )
                except Exception:
                    if i == 2:
                        raise
                    response = self.lab_view.request_user_input(
                        prompt=f"Fail to submit the scan. The error info is {format_exc()}",
                        options=["Retry", "Abort"],
                    )
                    if response == "Abort":
                        raise
                else:
                    break

            self.set_message(
                "Scan completed. Waiting to move sample off of the diffractometer..."
            )

            with self.lab_view.request_resources(
                {RobotArmCharacterization: {}, "dispenser_xrd": {}}, priority=50
            ) as (
                inner_devices,
                _,
            ):
                arm: RobotArmCharacterization = inner_devices[RobotArmCharacterization]
                xrd_dispenser: XRDDispenserRack = inner_devices["dispenser_xrd"]
                self.set_message("Moving the sample back to the XRD holder rack...")
                try:
                    arm.run_programs(
                        [
                            "pick_xrd_holder_machine.urp",
                            f"place_xrd_holder_rack_{slot_idx}.auto.urp",
                        ]
                    )
                except Exception:
                    response = self.lab_view.request_user_input(
                        prompt=f"Fail to pick up the XRD holder from the XRD machine.\n"
                        f"(1) Move the XRD holder on Aeris slot 1 manually to xrd holder rack slot {slot_idx}.\n"
                        f"(2) Set the robot arm to vertial_start position.\n"
                        f"The error info is {format_exc()}",
                        options=["OK", "Abort"],
                    )
                    if response == "Abort":
                        raise

                xrd_dispenser.mark_slot_dirty(
                    slot_idx,
                    str(self.sample),
                    str(self.lab_view.get_sample(self.sample).position),
                )  # mark the slot as dirty, give information of sample vial and its position

            total_mass_dispensed_mg = preparation_results.get(
                "total_mass_dispensed_mg", None
            )
            if total_mass_dispensed_mg is not None:
                self.set_message(
                    f"Complete. Measured {round(total_mass_dispensed_mg)} mg of powder."
                )
            else:
                self.set_message("Complete.")

        diffraction_results = {
            "mass_per_dispensing_attempt_mg": preparation_results.get(
                "mass_per_dispensing_attempt_mg", None
            ),
            "total_mass_dispensed_mg": total_mass_dispensed_mg,
            "met_target_mass": preparation_results.get("met_target_mass", None),
            "xrd_holder_index": slot_idx,
            "sampleid_in_aeris": scan_results["sampleid_in_aeris"],
            "twotheta": scan_results["twotheta"],
            "counts": scan_results["counts"],
        }
        try:
            DiffractionResult(**diffraction_results)
        except ValidationError as e:
            self.set_message(
                "Error: The results do not match the DiffractionResult schema. Please contact the developer."
            )
            raise e

        self.lab_view.update_sample_metadata(
            self.sample,
            {"diffraction_results": diffraction_results},
        )

        return diffraction_results


class PrepareSampleforXRD(BaseTask):
    """takes ground powder in a plastic vial -> pressed powder on an XRD sample holder. leaves vial in the dirty vial
    rack.
    """

    def __init__(self, sample: str, min_powder_mass: float, *args, **kwargs):
        """Prepare a sample for XRD."""
        super().__init__(priority=TaskPriority.HIGH, *args, **kwargs)  # noqa
        self.sample = sample
        self.min_powder_mass = min_powder_mass

    def validate(self):
        """Validate the PrepareSampleforXRD task."""
        return True

    def run(self) -> dict[str, list[float] | (float | bool)]:
        """
        Dispenses ground powder from a vial onto an XRD sample holder. Checks if the mass is
        sufficient. At the end, it will 1) return the XRD holder w/ powder to the XRD holder rack and
        2) recap + return the vial to the filled_vial_rack.

        Returns a dictionary with the following keys:
            "mass_per_dispense_attempt_mg" List[float]: The total mass (mg) of powder dispensed onto the
              XRD holder per attempt. The final value is the mass of the powder on the XRD holder.
            "total_mass_dispensed_mg": float: The total mass (mg) of powder dispensed onto the XRD holder.
            "met_target_mass" bool: True if the mass of powder on the XRD holder is >= the target mass, False otherwise.
            "xrd_holder_index" int: The index of the XRD holder that was used (1-16 on the XRDDispenseRack)

        """
        # move clean XRD holder and sample vial w/ powder to sample prep station.
        # pour + flatten powder onto XRD holder
        # get a fresh XRD sample holder, then move it to the pourstation
        # To prevent blocking, we only book dispenser_xrd to check available slot.
        # The loop to check happens here instead of the device because we dont want to book the device while its only
        # checking.
        slot_idx = None
        while slot_idx is None:
            with self.lab_view.request_resources(
                {"dispenser_xrd": {}},
            ) as (devices, sample_positions):
                dispenser_xrd: XRDDispenserRack = devices["dispenser_xrd"]
                self.set_message("Waiting for a fresh XRD sample holder")
                slot_idx = dispenser_xrd.get_available_slot()
                if slot_idx is None:
                    self.set_message(
                        "No fresh XRD sample holder available. Waiting for fresh one to be returned onto the rack."
                    )
            time.sleep(10)

        self.set_message(
            f"Booked XRD sample holder number {slot_idx!s} Waiting for all the other resources to become available."
        )

        with self.lab_view.request_resources(
            {
                CapDispenser: {},
                CappingGripper: {"slot": 1},
                "scale": {"slot": 1},
                "dispenser_xrd": {},
                None: {
                    "powdertransfer_vial_position": 1,
                    "powdertransfer_xrd_position": 1,
                    "cap_position": 2,
                    "filled_vial_rack": 1,
                },
            },
        ) as (devices, sample_positions):
            # devices
            dispenser_xrd: XRDDispenserRack = devices["dispenser_xrd"]
            capdispenser: CapDispenser = devices[CapDispenser]
            cappinggripper: CappingGripper = devices[CappingGripper]
            scale: Scale = devices["scale"]

            # sample positions
            powdertransfer_vial_position = sample_positions[None][
                "powdertransfer_vial_position"
            ][0]
            filled_vial_position = sample_positions[None]["filled_vial_rack"][0]

            self.set_message(f"Found a fresh XRD sample holder at slot {slot_idx}.")
            # moving the vial to the dumping station
            with self.lab_view.request_resources({RobotArmCharacterization: {}}) as (
                inner_devices,
                _,
            ):
                arm: RobotArmCharacterization = inner_devices[RobotArmCharacterization]
                self.set_message(
                    f"Moving XRD sample holder {slot_idx} to the powder transfer station."
                )

                for i in range(3):
                    try:
                        arm.set_message(
                            "Moving an XRD holder to the dispensing station..."
                        )
                        arm.run_programs(
                            [
                                f"pick_xrd_holder_rack_{slot_idx}.auto.urp",
                                "place_xrd_dispense_station.urp",
                            ]
                        )
                        arm.set_message(
                            "Moved an XRD holder to the dispensing station."
                        )
                    except Exception:
                        if i == 2:
                            raise
                        response = self.lab_view.request_user_input(
                            prompt="Failed to move XRD sample holder to powder transfer station.\n"
                            f"(1) Put the xrd holder back to Slot {slot_idx}\n"
                            f"(2) Set the robot arm back to vertical start\n"
                            f"The error information is {format_exc()}",
                            options=["Retry", "Abort"],
                        )
                        if response == "Abort":
                            raise
                    else:
                        break

                openthread = Thread(target=lambda: capdispenser.open_sieve_cap())
                openthread.start()
                self.set_message(
                    "Moving the sample vial to the powder transfer station..."
                )
                self.run_subtask(
                    Moving,
                    sample=self.sample,
                    destination=powdertransfer_vial_position,
                )

                self.set_message("Getting a sieve cap...")
                openthread.join()

                for i in range(3):
                    try:
                        arm.set_message(
                            "Picking up a sieve cap from the cap dispenser..."
                        )
                        arm.run_programs(
                            [
                                "pick_cap_dispenser_B.urp",
                            ]
                        )
                        arm.set_message("Picked up a sieve cap.")
                    except Exception:
                        if i == 0:
                            try:
                                # try moving robot back to vertical start, close cap dispenser, push the caps down
                                # using robot arm and retry
                                arm.clear_popup()
                                time.sleep(3)
                                arm.run_programs(["recover_cap_dispenser_B_1.urp"])
                                capdispenser.close_sieve_cap()
                                arm.run_programs(["recover_cap_dispenser_B_2.urp"])
                                capdispenser.open_sieve_cap()
                            except Exception:
                                response = self.lab_view.request_user_input(
                                    prompt="Failed to get a sieved cap and automatic recovery failed.\n"
                                    f"(1) Put a sieved cap to the cap dispenser B\n"
                                    f"(2) Set the robot arm back to vertical start\n"
                                    f"The error information is {format_exc()}",
                                    options=["Retry", "Abort"],
                                )
                                if response == "Abort":
                                    raise
                        if i == 1:
                            response = self.lab_view.request_user_input(
                                prompt="Failed to get a sieve cap.\n"
                                f"(1) Put the sieve cap to the cap dispenser B\n"
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

                closethread = Thread(target=lambda: capdispenser.close_sieve_cap())
                closethread.start()
                arm.set_message("Placing the sieve cap on the table...")
                arm.run_programs(
                    [
                        "place_cap_A.urp",
                    ]
                )
                arm.set_message("Placed the sieve cap on the table.")
                closethread.join()

                self.set_message("Changing vial cap to the sieve cap.")
                self.change_cap(
                    arm=arm, cappinggripper=cappinggripper, old_="B", new_="A"
                )  # put the sieve lid on. the original cap is sitting in the old position.

                openthread = Thread(target=lambda: capdispenser.open_acrylic_disk())
                openthread.start()
                mass_vs_attempts: list[float] = self.powder_dispensing_onto_xrd_holder(
                    arm=arm, scale=scale
                )
                got_enough_powder_mass: bool = (
                    mass_vs_attempts[-1] >= self.min_powder_mass
                )

                success_message = (
                    "Dispense was "
                    + ("successful" if got_enough_powder_mass else "unsuccessful")
                    + f": recovered {100*mass_vs_attempts[-1]/self.min_powder_mass}% of the target mass on the "
                    "XRD sample holder."
                )
                self.set_message(success_message + "Now flattening the powder.")

                # TODO do we always measure? Or only if we got enough powder?
                # flatten the sample

                openthread.join()
                for i in range(3):
                    try:
                        arm.set_message(
                            "Getting an acrylic disk to flatten powder on the XRD holder..."
                        )
                        arm.run_programs(
                            [
                                "pick_cap_dispenser_C.urp",
                            ]
                        )
                        arm.set_message("Got an acrylic disk.")
                    except Exception:
                        if i == 2:
                            raise
                        response = self.lab_view.request_user_input(
                            prompt="Failed to get an acrylic disk.\n"
                            f"(1) Put the acrylic disk to the cap dispenser C\n"
                            f"(2) Set the robot arm back to vertical start\n"
                            f"The error information is {format_exc()}",
                            options=["Retry", "Abort"],
                        )
                        if response == "Abort":
                            raise
                    else:
                        break

                closethread = Thread(target=lambda: capdispenser.close_acrylic_disk())
                closethread.start()
                arm.set_message(
                    "Using an acrylic disk to flatten powder on the XRD holder..."
                )
                arm.run_programs(
                    [
                        "xrd_sample_flattening.urp",
                    ]
                )
                arm.set_message("Flattened powder. Disposing of the acrylic disk...")
                try:
                    arm.run_programs(
                        [
                            "dispose.urp",
                        ]
                    )
                except Exception:
                    response = self.lab_view.request_user_input(
                        prompt="Fail to dispose the acrylic disk.\n"
                        f"(1) Dispose the acrylic disk manually\n"
                        f"(2) Set the robot arm back to vertical start\n"
                        f"The error information is {format_exc()}",
                        options=["OK", "Abort"],
                    )
                    if response == "Abort":
                        raise
                arm.set_message("Disposed the acrylic disk.")
                closethread.join()
                self.set_message(success_message)

                # move the prepared sample back to the rack position, vacate the xrd powder transfer position
                # TODO maybe not required -- can leave the sample in the powder transfer position
                try:
                    arm.set_message(
                        f"Moving the XRD holder to slot {slot_idx} of the XRD holder rack..."
                    )
                    arm.run_programs(
                        [
                            "pick_xrd_dispense_station.urp",
                            f"place_xrd_holder_rack_{slot_idx}.auto.urp",
                        ]
                    )
                    arm.set_message(
                        f"Placed the XRD holder in slot {slot_idx} of the XRD holder rack."
                    )
                    # return the vial to the filled vial rack
                except Exception:
                    response = self.lab_view.request_user_input(
                        prompt=f"Fail to move the xrd holder from xrd_dispense_position to the"
                        "xrd holder rack {slot_idx}\n"
                        f"(1) Put the xrd holder on robot_arm_gripper/xrd_dispense_position to"
                        "xrd holder rack {slot_idx};\n"
                        f"(2) Set the robot arm to vertial_start position.\n"
                        f"The error information is {format_exc()}",
                        options=["OK", "Abort"],
                    )

                self.set_message(
                    "Putting the vial of remaining powder back to the filled vial rack."
                )
                self.change_cap(
                    arm=arm, cappinggripper=cappinggripper, old_="dispose", new_="B"
                )
                self.run_subtask(
                    Moving,
                    sample=self.sample,
                    destination=filled_vial_position,
                )
                self.set_message("Done preparing the sample for XRD.")

        return {
            "mass_per_dispensing_attempt_mg": mass_vs_attempts,
            "total_mass_dispensed_mg": mass_vs_attempts[-1],
            "met_target_mass": got_enough_powder_mass,
            "xrd_holder_index": slot_idx,
        }

    def change_cap(
        self, arm: RobotArmCharacterization, cappinggripper: CappingGripper, old_, new_
    ):
        """Change the cap on the vial."""
        cappinggripper.open()  # sanity check
        arm.set_message("Moving vial to the capping station...")
        arm.run_program("move_vial_dumping_capper.urp")
        arm.set_message("Moved vial to the capping station.")
        cappinggripper.close()

        try:
            arm.set_message("Removing the current cap from the vial...")
            arm.run_programs(
                [
                    "decapping.urp",
                    f"place_cap_{old_}.urp" if old_ != "dispose" else "dispose.urp",
                ]
            )
            arm.set_message("Removed the current cap and placed it on the table.")
        except Exception:
            response = self.lab_view.request_user_input(
                prompt="Failed to decap the vial.\n"
                f"(1) Put the cap on the vial {'back to Slot ' + old_ if old_ != 'dispose' else 'to trash'}\n"
                f"(2) Set the robot arm back to vertical start\n"
                f"The error information is {format_exc()}",
                options=["Continue", "Abort"],
            )
            if response == "Abort":
                raise

        try:
            arm.set_message("Putting the new cap onto the vial...")
            arm.run_programs(
                [
                    f"pick_cap_{new_}.urp",
                    "capping.urp",
                ]
            )
            arm.set_message("Put the new cap onto the vial.")
        except Exception:
            response = self.lab_view.request_user_input(
                prompt="Failed to cap the vial.\n"
                f"(1) Put the cap on Slot {new_} to the vial\n"
                f"(2) Set the robot arm back to vertical start\n"
                f"The error information is {format_exc()}",
                options=["Continue", "Abort"],
            )
            if response == "Abort":
                raise

        cappinggripper.open()
        try:
            arm.set_message(
                "Moving the vial from the capper to the dumping position..."
            )
            arm.run_program("move_vial_capper_dumping.urp")
            arm.set_message("Moved the vial to the dumping position.")
        except Exception:
            response = self.lab_view.request_user_input(
                prompt=f"Fail to move the vial from the capper to the powdertransfer_crucible_position.\n"
                f"(1) Move the vial in capper/robot_arm_gripper to the powdertransfer_crucible_position manually;\n"
                f"(2) Set the robot arm to vertical_start position.\n"
                f"The error info is {format_exc()}",
                options=["OK", "Abort"],
            )
            if response == "Abort":
                raise

    def powder_dispensing_onto_xrd_holder(
        self, arm: RobotArmCharacterization, scale: Scale
    ) -> list[float]:
        """
        Dispenses powder onto the XRD sample holder. Makes up to a few attempts to get a target mass of powder.

        Note that reported masses are _loss from the vial_, not necessarily mass on the holders. This should be pretty
        much the same though.

        Returns
        -------
            List[float]: The total mass of powder dispensed onto the XRD sample holder after each attempt.
        """

        def _get_mass(rng=0):
            attempt = 0
            weight = scale.get_mass_in_mg()
            while (weight is None) and attempt < 3:  # try three times
                arm.run_program("after_weighing_vial.urp")
                arm.run_program("before_weighing_vial.urp")
                weight = scale.get_mass_in_mg()
                attempt += 1
            if weight is None:
                weight = -999999 if rng == 0 else 999999
            return weight

        self.set_message(
            f"Dispensing powder onto the XRD sample holder. Target mass is {self.min_powder_mass:.1f} mg."
        )
        arm.set_message("Moving a vial to the balance...")
        arm.run_programs(
            [
                "vertical_to_horizonal.urp",
                "pick_vial_dumping_station_reverse.urp",
                "before_weighing_vial.urp",
            ]
        )
        arm.set_message("Moved a vial to the balance.")
        time.sleep(5)  # let the balance settle
        initial_weight = current_weight = _get_mass()
        arm.set_message("Taking the vial off of the balance...")
        arm.run_program("after_weighing_vial.urp")
        arm.set_message("Moved the vial from the balance to the dumping position.")

        weights = [0]
        max_attempts = 3
        attempt = 0
        while True:
            # dispense powder
            attempt += 1

            # can shake a few extra times if we need a lot more powder to reach our target mass.
            we_need_a_lot_more_powder = weights[-1] < (self.min_powder_mass * 0.75)
            num_shakes = attempt if we_need_a_lot_more_powder else 1
            for _ in range(num_shakes):
                arm.set_message("Shaking powder from the vial onto the XRD holder...")
                arm.run_program("xrd_powder_dispensing.urp")

            arm.set_message("Moving the vial to the balance...")
            arm.run_program("before_weighing_vial.urp")
            arm.set_message("Moved the vial to the balance.")
            time.sleep(5)  # let the balance stabilize
            current_weight = _get_mass(rng=1)
            weights.append(initial_weight - current_weight)
            self.set_message(
                f"Powder dispense attempt {attempt}: {weights[-1]:.1f} / {self.min_powder_mass:.1f} mg dispensed."
            )
            arm.set_message("Taking the vial off of the balance...")
            arm.run_program("after_weighing_vial.urp")
            arm.set_message("Moved the vial from the balance to the dumping position.")

            if weights[-1] >= self.min_powder_mass:
                break  # we got enough powder
            if attempt == max_attempts:
                break  # we tried enough times
            if abs(weights[-1] - weights[-2]) < self.min_powder_mass * 0.05:
                # the weight is not changing much. Maybe out of powder, or sieve is clogged.
                break

        arm.set_message("Putting the vial back to the dumping station...")
        arm.run_program("place_vial_dumping_station_reverse.urp")
        arm.run_program("horizonal_to_vertical.urp")
        arm.set_message("Placed the vial back on the dumping station.")

        return weights
