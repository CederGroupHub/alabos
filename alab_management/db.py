"""
A convenient wrapper for MongoClient
in case we need to add authentication procedure
"""
import pymongo
from pymongo import collection

from .config import config

db_config = config["db"]

_client = pymongo.MongoClient(
    host=db_config.get("host", None),
    port=db_config.get("port", None),
    username=db_config.get("username", ""),
    password=db_config.get("password", ""),
)

_db = _client[db_config["name"]]


def get_collection(name: str) -> collection.Collection:
    """
    Get collection by name
    """
    return _db[name]
