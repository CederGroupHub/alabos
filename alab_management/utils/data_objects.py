"""
A convenient wrapper for MongoClient. We can get a database object by calling ``get_collection`` function.
"""

from typing import Optional
import numpy as np

import pika
import pymongo
from pymongo import collection, database

from .db_lock import MongoLock
from bson import ObjectId
import json
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod


class _BaseGetMongoCollection(ABC):
    @classmethod
    @abstractmethod
    def init(cls):
        raise NotImplementedError

    @classmethod
    def get_collection(cls, name: str) -> collection.Collection:
        """
        Get collection by name
        """
        if cls.client is None:
            cls.init()

        return cls.db[name]  # type: ignore # pylint: disable=unsubscriptable-object

    @classmethod
    def get_lock(cls, name: str) -> MongoLock:
        if cls.db_lock is None:
            cls.db_lock = MongoLock(collection=cls.get_collection("_lock"), name=name)
        return cls.db_lock


class _GetMongoCollection(_BaseGetMongoCollection):
    client: Optional[pymongo.MongoClient] = None
    db: Optional[database.Database] = None
    db_lock: Optional[MongoLock] = None

    @classmethod
    def init(cls):
        from ..config import AlabConfig

        db_config = AlabConfig()["mongodb"]
        cls.client = pymongo.MongoClient(
            host=db_config.get("host", None),
            port=db_config.get("port", None),
            username=db_config.get("username", ""),
            password=db_config.get("password", ""),
        )
        cls.db = cls.client[AlabConfig()["general"]["name"]]  # type: ignore # pylint: disable=unsubscriptable-object


class _GetCompletedMongoCollection(_BaseGetMongoCollection):
    client: Optional[pymongo.MongoClient] = None
    db: Optional[database.Database] = None
    db_lock: Optional[MongoLock] = None

    @classmethod
    def init(cls):
        from ..config import AlabConfig

        ALAB_CONFIG = AlabConfig()
        if "mongodb_completed" not in ALAB_CONFIG:
            raise ValueError(
                "Cannot use the completed database feature until that database info is set. Please specify the mongodb_completed configuration in the config file!"
            )
        db_config = ALAB_CONFIG["mongodb_completed"]
        cls.client = pymongo.MongoClient(
            host=db_config.get("host", None),
            port=db_config.get("port", None),
            username=db_config.get("username", ""),
            password=db_config.get("password", ""),
        )
        cls.db = cls.client[AlabConfig()["general"]["name"] + "(completed)"]  # type: ignore # pylint: disable=unsubscriptable-object


def get_rabbitmq_connection():
    from ..config import AlabConfig

    rabbit_mq_config = AlabConfig()["rabbitmq"]
    _connection = pika.BlockingConnection(
        parameters=pika.ConnectionParameters(
            host=rabbit_mq_config.get("host", "localhost"),
            port=rabbit_mq_config.get("port", 5672),
            heartbeat=600,
            blocked_connection_timeout=300,
        )
    )
    return _connection


def make_bsonable(obj):
    """
    Sanitize the object to make it bsonable. This is a recursive function, it will
    convert all the objects in the object to bsonable objects.
    """
    if isinstance(obj, dict):
        obj = {str(key): make_bsonable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = make_bsonable(obj[i])
    elif isinstance(obj, set):
        obj = list(obj)
    elif isinstance(obj, np.ndarray):
        obj = obj.tolist()
    elif isinstance(obj, str):
        try:
            obj = ObjectId(obj)
        except:
            pass

    return obj


class ALabJSONEncoder(json.JSONEncoder):
    def default(self, z):
        if isinstance(z, ObjectId):
            return str(z)
        elif isinstance(z, np.ndarray):
            return z.tolist()
        elif isinstance(z, np.int64):
            return int(z)
        elif isinstance(z, np.float64):
            return float(z)
        elif isinstance(z, Enum):
            return z.value
        elif isinstance(z, datetime):
            return z.isoformat()
        else:
            return super().default(z)


def make_jsonable(obj):
    """Converts a Python object to a JSON serializable object. Handles some typical ALab types (ObjectId, Enums, Numpy arrays, etc.) that are not JSON serializable by default. This is mostly used in API calls."""

    return json.loads(ALabJSONEncoder().encode(obj))


get_collection = _GetMongoCollection.get_collection
get_lock = _GetMongoCollection.get_lock

get_completed_collection = _GetCompletedMongoCollection.get_collection
get_completed_lock = _GetCompletedMongoCollection.get_lock
