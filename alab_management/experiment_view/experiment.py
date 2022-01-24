from typing import List, Any, Dict

from pydantic import BaseModel, constr  # pylint: disable=no-name-in-module


class _Sample(BaseModel):
    name: str


class _Task(BaseModel):
    type: str
    parameters: Dict[str, Any]
    prev_tasks: List[int]
    samples: Dict[str, str]


class InputExperiment(BaseModel):
    """
    This is the format that user should follow to write to experiment database
    """
    name: constr(regex=r"^[^$.]+$")  # type: ignore # noqa: F722
    samples: List[_Sample]
    tasks: List[_Task]
