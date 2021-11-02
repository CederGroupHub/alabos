"""
Logger module takes charge of recording information, warnings and errors during executing tasks
"""

from datetime import datetime
from enum import Enum, auto, unique
from typing import Dict, Any, Union

from bson import ObjectId

from alab_management.db import get_collection


@unique
class LoggingType(Enum):
    DEVICE_SIGNAL = auto()
    SAMPLE_AMOUNT = auto()
    CHARACTERIZATION_RESULT = auto()
    OTHER = auto()


class LoggingLevel(Enum):
    CRITICAL = 50
    FATAL = CRITICAL
    ERROR = 40
    WARNING = 30
    WARN = WARNING
    INFO = 20
    DEBUG = 10


class DBLogger:
    def __init__(self, task_id: ObjectId):
        self.task_id = task_id
        self.logging_collection = get_collection("logs")

    def log(self,
            level: Union[str, int, LoggingLevel],
            log_data: Dict[str, Any],
            logging_type: LoggingType = LoggingType.OTHER):
        if isinstance(level, str):
            level = LoggingLevel[level].value
        elif isinstance(level, LoggingLevel):
            level = LoggingLevel.value

        self.logging_collection.insert_one({
            "task_id": self.task_id,
            "type": logging_type,
            "level": level,
            "log_data": log_data,
            "created_at": datetime.now()
        })

    def log_amount(self, log_data: Dict[str, Any]):
        self.log(level=LoggingLevel.INFO, log_data=log_data, logging_type=LoggingType.SAMPLE_AMOUNT)

    def log_characterization_result(self, log_data: Dict[str, Any]):
        self.log(level=LoggingLevel.INFO, log_data=log_data, logging_type=LoggingType.CHARACTERIZATION_RESULT)

    def log_device_signal(self, log_data: Dict[str, Any]):
        self.log(level=LoggingLevel.DEBUG, log_data=log_data, logging_type=LoggingType.DEVICE_SIGNAL)
