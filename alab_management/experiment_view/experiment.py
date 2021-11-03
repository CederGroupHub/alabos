from enum import Enum, auto
from typing import List, Dict, Any

from bson import ObjectId
from pydantic import BaseModel


class ExperimentStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()



class Experiment(BaseModel):
    _id: ObjectId
    samples: List[str]
    tasks: List
    status: ExperimentStatus


