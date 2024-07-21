"""Define the format of experiment request."""

from typing import Any

from bson import BSON, ObjectId  # type: ignore
from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class _Sample(BaseModel):
    name: str = Field(pattern=r"^[^$.]+$")
    sample_id: str | None = None
    tags: list[str]
    metadata: dict[str, Any]

    @field_validator("sample_id")
    def if_provided_must_be_valid_objectid(cls, v):
        if v is None:
            return  # management will autogenerate a valid objectid

        try:
            return ObjectId(v)
        except Exception as exc:
            raise ValueError(
                "An experiment received over the API contained a sample with an invalid sample_id. The sample_id was "
                "set to {v}, which is not a valid ObjectId."
            ) from exc

    @field_validator("metadata")
    def must_be_bsonable(cls, v):
        """If v is not None, we must confirm that it can be encoded to BSON."""
        try:
            BSON.encode(v)
            return v
        except Exception as exc:
            raise ValueError(
                "An experiment received over the API contained a sample with invalid metadata. The metadata was set "
                f"to {v}, which is not BSON-serializable."
            ) from exc


class _Task(BaseModel):
    type: str
    parameters: dict[str, Any]
    prev_tasks: list[int]
    samples: list[str]
    task_id: str | None = None

    @field_validator("task_id")
    def if_provided_must_be_valid_objectid(cls, v):
        if v is None:
            return  # management will autogenerate a valid objectid

        try:
            return ObjectId(v)
        except Exception as exc:
            raise ValueError(
                "An experiment received over the API contained a task with an invalid task_id. The task_id was set to "
                f"{v}, which is not a valid ObjectId."
            ) from exc

    @field_validator("parameters")
    def must_be_bsonable(cls, v):
        """If v is not None, we must confirm that it can be encoded to BSON."""
        try:
            BSON.encode(v)
            return v
        except Exception as exc:
            raise ValueError(
                "An experiment received over the API contained a task with invalid parameters. The parameters was set "
                f"to {v}, which is not BSON-serializable."
            ) from exc


class InputExperiment(BaseModel):
    """This is the format that user should follow to write to experiment database."""

    name: str = Field(pattern=r"^[^$.]+$")
    samples: list[_Sample]
    tasks: list[_Task]
    tags: list[str]
    metadata: dict[str, Any]

    @field_validator("metadata")
    def must_be_bsonable(cls, v):
        """If v is not None, we must confirm that it can be encoded to BSON."""
        try:
            BSON.encode(v)
            return v

        except Exception as exc:
            raise ValueError(
                "An experiment received over the API contained invalid metadata. The metadata was set to {v}, "
                "which is not BSON-serializable."
            ) from exc
