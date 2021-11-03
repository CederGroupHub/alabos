from dataclasses import dataclass
from typing import Optional

from bson import ObjectId


@dataclass(frozen=True)
class Sample:
    """
    Basic sample object

    - ``_id``: the unique id of a sample in the database
    - ``name``: the name of this sample
    - ``position``: current position of the sample, if None, which means the sample has not been initialized
      in the lab
    """
    _id: ObjectId
    name: str
    position: Optional[str]
