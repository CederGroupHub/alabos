"""
This module contains the CompletedSampleView class, which is responsible for
saving samples to the completed database.
"""

from bson import ObjectId  # type: ignore
import time

from alab_management.utils.data_objects import get_collection, get_completed_collection


class CompletedSampleView:
    """Sample view manages the sample status, which is a collection of tasks."""

    def __init__(self):
        self._working_sample_collection = get_collection("samples")
        self._completed_sample_collection = get_completed_collection("samples")

    def save_sample(self, sample_id: ObjectId):
        """Saves a sample dictionary to the completed database. This should be copying a sample from the working
        database to the completed database.
        """
        # if self.exists(sample_id):
        #     raise ValueError(
        #         f"Sample with id {sample_id} already exists in the completed database!"
        #     )

        sample_dict = self._working_sample_collection.find_one(
            {"_id": ObjectId(sample_id)}
        )
        if sample_dict is None:
            raise ValueError(
                f"Sample with id {sample_id} does not exist in the database!"
            )
        if self.exists(sample_id):
            self._completed_sample_collection.update_one(
                filter={"_id": ObjectId(sample_id)},
                update={"$set": sample_dict},
                upsert=True,
            )
        else:
            self._completed_sample_collection.insert_one(sample_dict)
            # wait for the insert to complete
            while self._completed_sample_collection.find_one(
                {"_id": ObjectId(sample_id)}
            ) is None:
                time.sleep(0.5)

    def exists(self, sample_id: ObjectId | str) -> bool:
        """Check if a sample exists in the database.

        Args:
            sample_id (ObjectId): id of the sample within sample collection

        Returns
        -------
            bool: True if sample exists in the database
        """
        return (
            self._completed_sample_collection.count_documents(
                {"_id": ObjectId(sample_id)}
            )
            > 0
        )
