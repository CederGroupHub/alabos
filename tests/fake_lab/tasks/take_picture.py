import datetime

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator

from alab_management.task_view.task import BaseTask, LargeResult

from .. import RobotArm  # noqa


class TakePictureResult(BaseModel):
    """Take picture result."""

    sample_name: str | None = None
    sample_id: ObjectId | None = None
    picture: LargeResult
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("timestamp", mode="before")
    def validate_timestamp(cls, v):
        if isinstance(v, str):
            return datetime.datetime.fromisoformat(v)
        return v


class TakePicture(BaseTask):
    """Take picture task."""

    def __init__(self, samples: list[str | ObjectId], *args, **kwargs):
        """Take picture task.

        Args:
            samples (list[str|ObjectId]): List of sample names or sample IDs.
        """
        super().__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]

    @property
    def result_specification(self) -> type[BaseModel]:
        """Take picture task result specification."""
        return TakePictureResult

    def run(self):
        """Run the take picture task."""
        with self.lab_view.request_resources({RobotArm: {}}) as (
            inner_devices,
            sample_positions,
        ):
            robot_arm: RobotArm = inner_devices[RobotArm]
            robot_arm.run_program("take_picture.urp")
            sample_id = self.lab_view.get_sample(self.sample).sample_id
            picture_location = robot_arm.get_most_recent_picture_location()
            picture = LargeResult.from_local_file(local_path=picture_location)
            print(picture)
        # by doing this, checking is done during running.
        # this can lead to task being marked as failed if result does not meet the specification.
        return TakePictureResult(
            sample_id=sample_id, picture=picture, timestamp=datetime.datetime.now()
        )


class TakePictureWithoutSpecifiedResult(TakePicture):
    """Take picture without specified result task."""

    @property
    def result_specification(self):
        """Take picture without specified result task result specification."""
        return None

    def run(self):
        """Run the take picture without specified result task."""
        with self.lab_view.request_resources({RobotArm: {}}) as (
            devices,
            sample_positions,
        ):
            robot_arm: RobotArm = devices[RobotArm]
            robot_arm.run_program("take_picture.urp")
            sample_id = self.lab_view.get_sample(self.sample).sample_id
            picture_location = robot_arm.get_most_recent_picture_location()
            picture = LargeResult.from_local_file(local_path=picture_location)
        # by doing this, checking is done during running.
        # this can lead to task being marked as failed if result does not meet the specification.
        return {
            "sample_id": sample_id,
            "picture": picture,
            "timestamp": datetime.datetime.now(),
        }


class TakePictureMissingResult(BaseTask):
    """Take picture missing result task."""

    def __init__(self, samples: list[str | ObjectId], *args, **kwargs):
        """Take picture missing result task.

        Args:
            samples (list[str|ObjectId]): List of sample names or sample IDs.
        """
        super().__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]

    @property
    def result_specification(self) -> type[BaseModel]:
        """Take picture missing result task result specification."""
        return TakePictureResult

    def run(self):
        """Run the take picture missing result task."""
        with self.lab_view.request_resources({RobotArm: {}}) as (
            devices,
            sample_positions,
        ):
            robot_arm: RobotArm = devices[RobotArm]
            robot_arm.run_program("take_picture.urp")
        return {"timestamp": datetime.datetime.now()}
