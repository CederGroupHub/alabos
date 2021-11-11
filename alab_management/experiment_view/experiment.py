from typing import List, Any, Dict

from pydantic.main import BaseModel


class _Sample(BaseModel):
    name: str


class _Task(BaseModel):
    type: str
    parameters: Dict[str, Any]
    samples: Dict[str, str]


class InputExperiment(BaseModel):
    """
    This is the format that user should follow to write to experiment database
    """
    name: str
    samples: List[_Sample]
    tasks: List[_Task]
