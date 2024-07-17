"""This module contains the XRDCleaner class for cleaning XRD holders with a vacuum cleaner."""
from enum import Enum
from typing import ClassVar, Literal

import numpy as np
from alab_control.ender3 import Ender3
from alab_control.vacuum_controller.vacuum_controller import VacuumController
from alab_management.device_view import BaseDevice
from alab_management.sample_view import SamplePosition


class SlotState(Enum):
    """Enumeration of the states of a slot in the XRDCleaner."""
    UNKNOWN = "unknown"
    EMPTY = "empty"
    DIRTY = "dirty"
    CLEAN = "clean"


class XRDCleaner(BaseDevice):
    """A 3d printer modified to clean XRD holders with a vacuum cleaner."""
    description: ClassVar[str] = "A 3d printer modified to clean XRD holders with a vacuum cleaner."
    LEFT_COORDINATES = [
        45,
        120,
        0,
    ]  # coordinate where vacuum is centered directly above the left xrd holder
    RIGHT_COORDINATES = [
        117,
        120,
        0,
    ]  # coordinate where vacuum is centered directly above the right xrd holder
    SHOW_COORDINATES = [
        79.5,
        235.0,
        20,
    ]  # coordinate where tray is fully extended towards the robot arm
    HIDE_COORDINATES = [
        79.5,
        0,
        20,
    ]  # coordinate where tray is fully retracted away from the robot arm
    ZHOP_HEIGHT = 15  # the height (in mm) to raise the z-axis between lateral movements. This is to avoid collisions.

    def __init__(self, robot_port: str, relay_address: str, relay_port: int, *args, **kwargs):
        """Initialize the XRDCleaner object."""
        super().__init__(*args, **kwargs)
        self.robot_port = robot_port
        self.relay_address = relay_address
        self.relay_port = relay_port

        self.robot = None
        self.relay = None

        self.slot_state = self.dict_in_database(
            name="slot_state",
            default_value={
                "left": SlotState.EMPTY.value,
                "right": SlotState.EMPTY.value,
            },
        )

    def connect(self):
        """Connect to the XRDCleaner."""
        self.robot = Ender3(port=self.robot_port)
        if not self.robot.has_been_homed:
            self.robot.gohome()
        self.relay = VacuumController(ip_address=self.relay_address, port=self.relay_port)
        self._confirm_connection()
        self.robot.ZHOP_HEIGHT = self.ZHOP_HEIGHT

    def disconnect(self):
        """Disconnect from the XRDCleaner."""
        try:
            self.robot.disconnect()
        except Exception:
            pass  # maybe we weren't connected to begin with
        self.robot = None
        self.relay = None

    def is_running(self):
        """Check if the XRDCleaner is running."""
        return False  # TODO

    def _handle_unknown_slot_state(self, side: Literal["left", "right"]):
        response = self.request_maintenance(
            prompt=f"XRDCleaner: Unknown state for the {side} slot. Please submit the proper state here before "
            "continuing...",
            options=["Empty", "Clean", "Dirty"],
        )
        self.slot_state[side] = SlotState(response.lower()).value

    def _confirm_slot_states(self):
        if SlotState(self.slot_state["left"]) == SlotState.UNKNOWN:
            self._handle_unknown_slot_state("left")
        if SlotState(self.slot_state["right"]) == SlotState.UNKNOWN:
            self._handle_unknown_slot_state("right")

    def _confirm_connection(self):
        if self.robot is None:
            raise Exception("Device is not connected!")
        # self._confirm_slot_states()
        # TODO

        # while not self.driver.is_under_remote_control:
        #     self._device_view.pause_device(self.name)
        #     self.set_message("The Aeris is not under remote control. Please set to remote control and try again.")
        #     response = self.request_maintenance(prompt="Please set the Aeris XRD to remote control, then press OK to
        #            continue.", options = ["OK"])
        #     if self.driver.is_under_remote_control:
        #         self._device_view.unpause_device(self.name)
        #         self.set_message("Successfully connected to the Aeris in remote control mode!")

    @property
    def sample_positions(self):
        """Return the sample positions of the XRDCleaner."""
        return [
            SamplePosition(
                "slot/left",
                description="Position to clean XRD sample holders.",
            ),
            SamplePosition(
                "slot/right",
                description="Position to clean XRD sample holders.",
            ),
        ]

    def emergent_stop(self):
        """Stop the XRDCleaner."""
        return
        # self.driver.stop()

    ### movement methods
    def move_to_left(self):
        """Move the vacuum directly over the center coordinate of the left xrd holder slot."""
        self.robot.moveto(*self.LEFT_COORDINATES, zhop=True)

    def move_to_right(self):
        """Move the vacuum directly over the center coordinate of the right xrd holder slot."""
        self.robot.moveto(*self.RIGHT_COORDINATES, zhop=True)

    def show(self):
        """Move the tray to the furthest forward position. Use this when the robot arm needs to pick/place from the
        tray.
        """
        self.robot.moveto(*self.SHOW_COORDINATES, zhop=True)

    def hide(self):
        """Move the tray to the furthest back position. Use this to get the tray out of the way."""
        self.robot.moveto(*self.HIDE_COORDINATES, zhop=True)

    ### cleaning methods
    def _clean_grid(self, center_coordinates: list[float]):
        # build the grid to scan the sample
        width = 25  # mm
        steps = 15  # number of steps to break x/y grid into
        grid_coordinates = []
        zigzag = "zig"
        for dy in np.linspace(width / 2, -width / 2, steps):
            c_right = [
                center_coordinates[0] + width / 2,
                center_coordinates[1] + dy,
                center_coordinates[2],
            ]
            c_left = [
                center_coordinates[0] - width / 2,
                center_coordinates[1] + dy,
                center_coordinates[2],
            ]
            if zigzag == "zag":
                grid_coordinates.append(c_right)
                grid_coordinates.append(c_left)
                zigzag = "zig"
            elif zigzag == "zig":
                grid_coordinates.append(c_left)
                grid_coordinates.append(c_right)
                zigzag = "zag"

        self.robot.moveto(*grid_coordinates[0], zhop=True)  # go to initial corner of grid
        current_speed = self.robot.speed
        self.robot.speed = 0.3  # 20% speed
        self.relay.on()  # turn on vacuum
        self.robot.moveto_sequence(grid_coordinates[1:])  # move to each point in the grid
        self.relay.off()  # turn off vacuum
        self.robot.speed = current_speed
        self.robot.moveto(*self.HIDE_COORDINATES, zhop=True)  # go to clear position

    def clean_left(self):
        """Clean the left xrd holder."""
        self._clean_grid(self.LEFT_COORDINATES)

    def clean_right(self):
        """Clean the right xrd holder."""
        self._clean_grid(self.RIGHT_COORDINATES)

    ### state management methods NOT IN USE YET
    def _load(self, side: Literal["left", "right"]):
        # if self.slot_state[side] != SlotState.EMPTY:
        #     raise Exception(f"Cannot load into the {side} slot: it is not empty!")
        self.slot_state[side] = SlotState.DIRTY

    def load_left(self):
        """Indicate that a dirty xrd holder has been placed on the left slot."""
        self._load("left")

    def load_right(self):
        """Indicate that a dirty xrd holder has been placed on the right slot."""
        self._load("right")

    def _unload(self, side: Literal["left", "right"]):
        # if self.slot_state[side] == SlotState.EMPTY:
        #     raise Exception(f"Cannot unload from the {side} slot: it is already empty!")
        self.slot_state[side] = SlotState.EMPTY

    def unload_left(self):
        """Indicate that an xrd holder (clean or dirty) has been removed from the left slot."""
        self._unload("left")

    def unload_right(self):
        """Indicate that an xrd holder (clean or dirty) has been removed from the right slot."""
        self._unload("right")
