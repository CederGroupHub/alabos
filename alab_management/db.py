"""
A convenient wrapper for MongoClient
in case we need to add authentication procedure
"""
import pymongo

from config import config

db_config = config["db"]

_db = pymongo.MongoClient(
    host=db_config["host"],
    port=db_config["port"],
    username=db_config["username"],
    password=db_config["password"],
)[db_config["name"]]


def get_collection(name: str) -> pymongo.collection.Collection:
    """
    Get collection by name
    """
    return _db[name]
