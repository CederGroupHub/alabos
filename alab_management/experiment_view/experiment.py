"""
Define the format of experiment request.
"""

from typing import List, Any, Dict, Optional

from pydantic import BaseModel, constr, validator  # pylint: disable=no-name-in-module
from bson import ObjectId


class _Sample(BaseModel):
    name: constr(regex=r"^[^$.]+$")  # type: ignore # noqa: F722
    sample_id: Optional[str] = None

    @validator("sample_id")
    def if_provided_must_be_valid_objectid(cls, v):
        if v is None:
            return  # management will autogenerate a valid objectid

        try:
            return ObjectId(v)
        except:
            raise ValueError(
                "An experiment received over the API contained a sample with an invalid sample_id. The sample_id was set to {v}, which is not a valid ObjectId."
            )


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
        except:
            raise ValueError(
                "An experiment received over the API contained a task with an invalid task_id. The task_id was set to {v}, which is not a valid ObjectId."
            )


class InputExperiment(BaseModel):
    """
    This is the format that user should follow to write to experiment database
    """

    name: constr(regex=r"^[^$.]+$")  # type: ignore # noqa: F722
    samples: List[_Sample]
    tasks: List[_Task]
