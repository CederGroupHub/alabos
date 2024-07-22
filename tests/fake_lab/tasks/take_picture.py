import datetime

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator

from alab_management.task_view.task import BaseTask, LargeResult

from ..devices.robot_arm import RobotArm  # noqa


class TakePictureResult(BaseModel):
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
    def __init__(self, samples: list[str | ObjectId], *args, **kwargs):
        super().__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]

    @property
    def result_specification(self) -> BaseModel:
        return TakePictureResult

    def run(self):
        with self.lab_view.request_resources({RobotArm: {}}) as (
            devices,
            sample_positions,
        ):
            robot_arm: RobotArm = devices[RobotArm]
            robot_arm.run_program("take_picture.urp")
            sample_id = self.lab_view.get_sample(self.sample).sample_id
            picture_location = robot_arm.get_most_recent_picture_location()
            picture = LargeResult(local_path=picture_location)
        # by doing this, checking is done during running.
        # this can lead to task being marked as failed if result does not meet the specification.
        return TakePictureResult(
            sample_id=sample_id, picture=picture, timestamp=datetime.datetime.now()
        )


class TakePictureMissingResult(BaseTask):
    def __init__(self, samples: list[str | ObjectId], *args, **kwargs):
        super().__init__(samples=samples, *args, **kwargs)
        self.sample = samples[0]

    @property
    def result_specification(self) -> type[BaseModel]:
        return TakePictureResult

    def run(self):
        with self.lab_view.request_resources({RobotArm: {}}) as (
            devices,
            sample_positions,
        ):
            robot_arm: RobotArm = devices[RobotArm]
            robot_arm.run_program("take_picture.urp")
        return {"timestamp": datetime.datetime.now()}
