"""This module contains the ManualHeating class for performing manual heating tasks."""

from alab_example.devices.manual_furnace import ManualFurnace
from pydantic import BaseModel, Extra, Field, ValidationError

from alab_management import BaseTask
from alab_management.task_view.task_enums import TaskPriority


class ManualHeatingResult(BaseModel, extra=Extra.forbid):
    """ManualHeating task result."""

    heating_temperature: float = Field(
        default=None,
        description="Target temperature to which the samples were heated.",
    )
    heating_time: float = Field(
        default=None,
        description="Duration for which the samples were heated.",
    )


class ManualHeating(BaseTask):
    """This class represents the ManualHeating task."""

    def __init__(
        self,
        heating_time: float,
        heating_temperature: float,
        *args,
        **kwargs,
    ):
        """Initialize the ManualHeating task."""
        priority = kwargs.pop("priority", TaskPriority.HIGH)
        super().__init__(priority=priority, *args, **kwargs)  # noqa

        self.num_samples = len(self.samples)
        self.heating_time = heating_time
        self.heating_temperature = heating_temperature

    def validate(self):
        """Validate the ManualHeating task."""
        if not 0 < len(self.samples) <= 8:
            raise ValueError("Number of samples must be between 1 and 8")
        return True

    def run(self):
        """Run the ManualHeating task."""
        self.samples.sort(key=lambda x: self.lab_view.get_sample(x).position)
        with self.lab_view.request_resources({ManualFurnace: {"slot": 8}}) as (
            devices,
            sample_positions,
        ):
            sample_positions = sample_positions[ManualFurnace]["slot"]
            furnace_name = sample_positions[0].split("/")[0]
            sample_positions.sort(key=lambda x: x)

            response = self.lab_view.request_user_input(
                prompt=f"Please take the sample from the labman quadrant to the furnace {furnace_name}, "
                f"set up the heating profile "
                f"and click OK.\n"
                f"Moving the crucibles as follows:\n"
                + "\n".join(
                    f"{sample}: from `{self.lab_view.get_sample(sample).position}` to `{position}`;"
                    for sample, position in zip(self.samples, sample_positions)
                )
                + "\n\n"
                "The heating profile should be as follows:\n"
                f"`Temperature: {self.heating_temperature} °C`\n"
                f"`Time: {self.heating_time} min`\n"
                f"Ramp rate is 2 °C/min before 300 °C. and 15 °C/min after 300 °C.\n",
                options=["OK", "Cancel"],
            )

            if response == "Cancel":
                raise Exception("User cancelled the task.")

            for sample, position in zip(self.samples, sample_positions):
                self.lab_view.move_sample(sample, position)

            self.set_message(
                f"The user is heating the samples in furnace {furnace_name}."
            )

            self.lab_view.request_user_input(
                prompt=f"Click OK when the heating is done in furnace {furnace_name}.",
                options=["OK", "Cancel"],
            )

            if response == "Cancel":
                raise Exception("User cancelled the task.")

        heating_result = {
            "heating_temperature": self.heating_temperature,
            "heating_time": self.heating_time,
        }
        try:
            ManualHeatingResult(**heating_result)
        except ValidationError as e:
            self.set_message(
                "Error: The results do not match the ManualHeatingResult schema. Please contact the developer."
            )
            raise e

        for sample in self.samples:
            self.lab_view.update_sample_metadata(
                sample, {"heating_results": heating_result}
            )

        for sample in self.samples:
            with self.lab_view.request_resources({"transfer_rack": {"slot": 1}}) as (
                _,
                sample_positions,
            ):
                transfer_rack_position = sample_positions["transfer_rack"]["slot"][0]

                self.set_message("Moving the crucible to transfer rack.")
                position = self.lab_view.get_sample(sample).position

                response = self.lab_view.request_user_input(
                    prompt=f"Please move the sample {sample} from `{position}` to `{transfer_rack_position}`.",
                    options=["Done", "Cancel"],
                )
                if response == "Cancel":
                    raise Exception("User cancelled the task.")
                self.lab_view.move_sample(sample, transfer_rack_position)

        return heating_result
