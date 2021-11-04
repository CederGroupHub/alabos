from typing import Optional, List, Any, Dict

from bson import ObjectId
from pydantic import Field
from pydantic.main import BaseModel


class _Sample(BaseModel):
    name: str
    sample_id: Optional[ObjectId] = Field(default=None)


class _Task(BaseModel):
    type: str
    parameters: Dict[str, Any]
    samples: Dict[str, str]


class Experiment(BaseModel):
    name: str
    status: str
    samples: List[_Sample]
    tasks: List[_Task]