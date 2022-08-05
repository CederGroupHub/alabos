"""
Logger module takes charge of recording information, warnings and errors during executing tasks
"""

from datetime import datetime, timedelta
from enum import Enum, auto, unique
from typing import Dict, Any, Union, Optional, Iterable, cast

from bson import ObjectId

from .utils.data_objects import get_collection


@unique
class LoggingType(Enum):
    """
    Different types of log
    """

    DEVICE_SIGNAL = auto()
    SAMPLE_AMOUNT = auto()
    CHARACTERIZATION_RESULT = auto()
    SYSTEM_LOG = auto()
    OTHER = auto()


class LoggingLevel(Enum):
    """
    Different level log
    """

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

    def log(
        self,
        level: Union[str, int, LoggingLevel],
        log_data: Dict[str, Any],
        logging_type: LoggingType = LoggingType.OTHER,
    ) -> ObjectId:
        """
        Basic log function
        Args:
            level: the level of this log, which can be string, int or :py:class:`LoggingLevel <LoggingLevel>`
            log_data: the data to be logged
            logging_type: the type of logging
        """
        if isinstance(level, str):
            level = LoggingLevel[level].value
        elif isinstance(level, LoggingLevel):
            level = level.value

        result = self._logging_collection.insert_one(
            {
                "task_id": self.task_id,
                "type": logging_type.name,
                "level": level,
                "log_data": log_data,
                "created_at": datetime.now(),
            }
        )

        return cast(ObjectId, result.inserted_id)

    def log_amount(self, log_data: Dict[str, Any]):
        """
        Log the amount of samples and chemicals (e.g. weight)
        """
        return self.log(
            level=LoggingLevel.INFO,
            log_data=log_data,
            logging_type=LoggingType.SAMPLE_AMOUNT,
        )

    def log_characterization_result(self, log_data: Dict[str, Any]):
        """
        Log the characterization result (e.g. XRD pattern)
        """
        return self.log(
            level=LoggingLevel.INFO,
            log_data=log_data,
            logging_type=LoggingType.CHARACTERIZATION_RESULT,
        )

    def log_device_signal(self, log_data: Dict[str, Any]):
        """
        Log the device sensor's signal (e.g. the voltage of batteries, the temperature of furnace)
        """
        return self.log(
            level=LoggingLevel.DEBUG,
            log_data=log_data,
            logging_type=LoggingType.DEVICE_SIGNAL,
        )

    def system_log(
        self, level: Union[str, int, LoggingLevel], log_data: Dict[str, Any]
    ):
        """
        Log that comes from the workflow system
        """
        return self.log(
            level=level, log_data=log_data, logging_type=LoggingType.SYSTEM_LOG
        )

    def filter_log(
        self, level: Union[str, int, LoggingLevel], within: timedelta
    ) -> Iterable[Dict[str, Any]]:
        """
        Find log within a range of time (1h/1d or else) higher than certain level
        """
        if isinstance(level, str):
            level = cast(int, LoggingLevel[level].value)
        elif isinstance(level, LoggingLevel):
            level = cast(int, LoggingLevel.value)

        return self._logging_collection.find(
            {"level": {"$gte": level}, "created_at": {"$gte": datetime.now() - within}}
        )
