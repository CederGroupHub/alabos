"""A convenient wrapper for MongoClient. We can get a database object by calling ``get_collection`` function."""

import contextlib
import json
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path

import numpy as np
import pika
import pymongo
from bson import ObjectId
from pymongo import collection, database

from alab_management.config import AlabOSConfig
from alab_management.utils.db_lock import MongoLock


class _BaseGetMongoCollection(ABC):
    client: pymongo.MongoClient | None = None
    db: database.Database | None = None
    db_lock: MongoLock | None = None

    @classmethod
    @abstractmethod
    def init(cls):
        raise NotImplementedError

    @classmethod
    def get_collection(cls, name: str) -> collection.Collection:
        """Get collection by name."""
        if cls.db is None:
            cls.init()

        return cls.db[name]  # type: ignore # pylint: disable=unsubscriptable-object

    @classmethod
    def get_lock(cls, name: str) -> MongoLock:
        if cls.db_lock is None:
            cls.db_lock = MongoLock(collection=cls.get_collection("_lock"), name=name)
        return cls.db_lock


class _GetMongoCollection(_BaseGetMongoCollection):
    @classmethod
    def init(cls):
        db_config = AlabOSConfig()["mongodb"]
        cls.client = pymongo.MongoClient(
            host=db_config.get("host", None),
            port=db_config.get("port", None),
            username=db_config.get("username", ""),
            password=db_config.get("password", ""),
        )
        sim_mode_flag = AlabOSConfig().is_sim_mode()
        # force to enable sim mode, just in case
        cls.db = cls.client[
            AlabOSConfig()["general"]["name"] + ("_sim" * sim_mode_flag)
        ]


class _GetCompletedMongoCollection(_BaseGetMongoCollection):
    @classmethod
    def init(cls):
        alabos_config = AlabOSConfig()
        if "mongodb_completed" not in alabos_config:
            raise ValueError(
                "Cannot use the completed database feature until that database info is set. Please specify the "
                "mongodb_completed configuration in the config file!"
            )
        db_config = alabos_config["mongodb_completed"]
        cls.client = pymongo.MongoClient(
            host=db_config.get("host", None),
            port=db_config.get("port", None),
            username=db_config.get("username", ""),
            password=db_config.get("password", ""),
        )
        sim_mode_flag = AlabOSConfig().is_sim_mode()
        if sim_mode_flag:
            cls.db = cls.client[
                AlabOSConfig()["general"]["name"] + "(completed)" + "_sim"
            ]
        else:
            cls.db = cls.client[AlabOSConfig()["general"]["name"] + "(completed)"]
        # type: ignore # pylint: disable=unsubscriptable-object


def get_rabbitmq_connection():
    """Get a connection to the RabbitMQ server."""
    rabbit_mq_config = AlabOSConfig()["rabbitmq"]
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
        with contextlib.suppress(Exception):
            obj = ObjectId(obj)
    elif isinstance(obj, Path):
        obj = str(obj)

    return obj


class ALabJSONEncoder(json.JSONEncoder):
    """
    A customized JSON encoder.

    It can handle some typical ALab types (ObjectId, Enums, Numpy arrays, etc.) that are not JSON
    serializable by default.
    """

    def default(self, z):
        """Converts a Python object to a JSON serializable object."""
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
    """Converts a Python object to a JSON serializable object. Handles some typical ALab types (ObjectId, Enums,
    Numpy arrays, etc.) that are not JSON serializable by default. This is mostly used in API calls.
    """
    return json.loads(ALabJSONEncoder().encode(obj))


get_collection = _GetMongoCollection.get_collection
get_lock = _GetMongoCollection.get_lock

get_completed_collection = _GetCompletedMongoCollection.get_collection
get_completed_lock = _GetCompletedMongoCollection.get_lock


class DocumentNotUpdatedError(Exception):
    """Exception raised when a document is not updated in the database."""
