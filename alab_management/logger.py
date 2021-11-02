"""
Logger module takes charge of recording information, warnings and errors during executing tasks
"""

from datetime import datetime, timedelta
from enum import Enum, auto, unique
from typing import Dict, Any, Union, Optional, List, Iterable

from bson import ObjectId

from .db import get_collection


@unique
class LoggingType(Enum):
    DEVICE_SIGNAL = auto()
    SAMPLE_AMOUNT = auto()
    CHARACTERIZATION_RESULT = auto()
    SYSTEM_LOG = auto()
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
    """
    A custom logger that wrote data to database, where we predefined some log pattern
    """
    def __init__(self, task_id: Optional[ObjectId]):
        self.task_id = task_id
        self._logging_collection = get_collection("logs")

    def log(self,
            level: Union[str, int, LoggingLevel],
            log_data: Dict[str, Any],
            logging_type: LoggingType = LoggingType.OTHER):
        if isinstance(level, str):
            level = LoggingLevel[level].value
        elif isinstance(level, LoggingLevel):
            level = LoggingLevel.value

        self._logging_collection.insert_one({
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

    def system_log(self, log_data: Dict[str, Any]):
        self.log(level=LoggingLevel.DEBUG, log_data=log_data, logging_type=LoggingType.SYSTEM_LOG)

    def filter_log(self, level: Union[str, int, LoggingLevel], within: timedelta) -> Iterable[Dict[str, Any]]:
        if isinstance(level, str):
            level = LoggingLevel[level].value
        elif isinstance(level, LoggingLevel):
            level = LoggingLevel.value

        return self._logging_collection.find({"level": {"$gte": level},
                                              "created_at": {"$gte": datetime.now() - within}})
