"""
A convenient wrapper for MongoClient
in case we need to add authentication procedure
"""
from typing import Optional

import pymongo
from pymongo import collection, database
from .utils.db_lock import MongoLock


class _GetCollection:
    client: Optional[pymongo.MongoClient] = None
    db: Optional[database.Database] = None
    db_lock: Optional[MongoLock] = None

    @classmethod
    def init(cls):
        from .config import AlabConfig

        db_config = AlabConfig()["db"]
        cls.client = pymongo.MongoClient(
            host=db_config.get("host", None),
            port=db_config.get("port", None),
            username=db_config.get("username", ""),
            password=db_config.get("password", ""),
        )
        cls.db = cls.client[db_config["name"]]  # type: ignore # pylint: disable=unsubscriptable-object

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


get_collection = _GetCollection.get_collection
get_lock = _GetCollection.get_lock
