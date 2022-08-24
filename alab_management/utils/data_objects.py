"""
A convenient wrapper for MongoClient. We can get a database object by calling ``get_collection`` function.
"""

from typing import Optional

import pika
import pymongo
from pymongo import collection, database

from .db_lock import MongoLock


class _GetMongoCollection:
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


def get_rabbitmq_connection():
    from ..config import AlabConfig

    rabbit_mq_config = AlabConfig()["rabbitmq"]
    _connection = pika.BlockingConnection(
        parameters=pika.ConnectionParameters(
            host=rabbit_mq_config.get("host", "localhost"),
            port=rabbit_mq_config.get("port", 5672),
        )
    )
    return _connection


get_collection = _GetMongoCollection.get_collection
get_lock = _GetMongoCollection.get_lock
