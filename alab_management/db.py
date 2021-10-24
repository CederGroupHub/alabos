"""
A convenient wrapper for MongoClient
in case we need to add authentication procedure
"""
import pymongo

from .config import config

db_config = config["db"]

_db = pymongo.MongoClient(
    host=db_config.get("host", None),
    port=db_config.get("port", None),
    username=db_config.get("username", ""),
    password=db_config.get("password", ""),
)[db_config["name"]]


def get_collection(name: str) -> pymongo.collection.Collection:
    """
    Get collection by name
    """
    return _db[name]
