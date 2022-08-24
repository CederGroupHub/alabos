"""
This file defines the database lock class, which can block other processes to access the database.
"""

import time
from contextlib import contextmanager
from typing import Optional

from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError


class MongoLockAcquireError(Exception):
    """
    Raised when failing to acquire a lock
    """


class MongoLockReleaseError(Exception):
    """
    Raised when failing to release a lock
    """


class MongoLock:
    """
    Use a distributed lock to lock a collection or something else
    """

    def __init__(self, name: str, collection: Collection):
        self._lock_collection = collection
        self._name = name
        self._locked: bool = self._lock_collection.find_one({"_id": name}) is not None

    @property
    def name(self) -> str:
        return self._name

    @contextmanager
    def __call__(self, timeout: Optional[float] = None):
        yield self.acquire(timeout=timeout)
        self.release()

    def acquire(self, timeout: Optional[float] = None):
        start_time = time.time()
        while timeout is None or time.time() - start_time <= timeout:
            try:
                self._lock_collection.insert_one({"_id": self._name})
            except DuplicateKeyError:
                time.sleep(0.1)
                continue
            else:
                self._locked = True
                return
        raise MongoLockAcquireError("Acquire lock timeout")

    def release(self):
        result = self._lock_collection.delete_one({"_id": self._name})
        if result.deleted_count != 1:
            raise MongoLockReleaseError(
                f"Fail to release a lock (name={self._name}). "
                f"Are you sure if the key is right?"
            )
        self._locked = False
