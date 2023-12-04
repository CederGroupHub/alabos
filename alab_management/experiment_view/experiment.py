"""Define the format of experiment request."""

from typing import Any, Dict, List, Optional

from bson import BSON, ObjectId  # type: ignore
from pydantic import constr  # pylint: disable=no-name-in-module
from pydantic import BaseModel, validator


class _Sample(BaseModel):
    name: constr(regex=r"^[^$.]+$")  # type: ignore
    sample_id: Optional[str] = None
    tags: List[str]
    metadata: Dict[str, Any]

    @validator("sample_id")
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

    @validator("metadata")
    def must_be_bsonable(cls, v):
        """If v is not None, we must confirm that it can be encoded to BSON."""
        try:
            BSON.encode(v)
            return v
        except Exception as exc:
            raise ValueError(
                "An experiment received over the API contained a sample with invalid metadata. The metadata was set "
                "to {v}, which is not BSON-serializable."
            ) from exc


class _Task(BaseModel):
    type: str
    parameters: Dict[str, Any]
    prev_tasks: List[int]
    samples: List[str]
    task_id: Optional[str] = None

    @validator("task_id")
    def if_provided_must_be_valid_objectid(cls, v):
        if v is None:
            return  # management will autogenerate a valid objectid

        try:
            return ObjectId(v)
        except Exception as exc:
            raise ValueError(
                "An experiment received over the API contained a task with an invalid task_id. The task_id was set to "
                "{v}, which is not a valid ObjectId."
            ) from exc


class InputExperiment(BaseModel):
    """This is the format that user should follow to write to experiment database."""

    name: constr(regex=r"^[^$.]+$")  # type: ignore
    samples: List[_Sample]
    tasks: List[_Task]
    tags: List[str]
    metadata: Dict[str, Any]

    @validator("metadata")
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
