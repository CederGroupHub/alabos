from datetime import datetime
from typing import Optional, List, Dict, Any

from bson import ObjectId

from alab_management.config import config
from alab_management.db import get_collection


class SampleView:
    """
    Sample view manages all the database operations regarding to samples
    """
    def __init__(self):
        self._collection = get_collection(config["sample_positions"]["sample_db"])
        self._sample_position = get_collection(config["sample_positions"]["sample_position_db"])
        self._position_connection = get_collection(config["sample_positions"]["position_connection_db"])

    def create_sample(self) -> ObjectId:
        """
        Create a single sample in the database an return its object_id

        By default the initial position of this sample is defined to ``None``.
        """
        result = self._collection.insert_one({
            "type": "single_sample",
            "position": None,
            "last_updated": datetime.now(),
        })
        return result.inserted_id

    def creat_sample_batch(self, *sample_ids) -> ObjectId:
        """
        Create a sample batch in the database and return its object_id

        Args:
            *sample_ids:  the list of sample ids contained in this batch
        """
        result = self._collection.insert_one({
            "type": "sample_batch",
            "samples": sample_ids,
            "position": None,
            "last_updated": datetime.now(),
        })

        for sample_id in sample_ids:
            self._collection.update_one({"_id": sample_id}, {"$set": {
                "position": result.inserted_id,
                "last_updated": datetime.now(),
            }})
        return result.inserted_id

    def update_sample_position(self, sample_id: ObjectId, new_position: str):
        """
        Update the position of one sample

        if ``sample_id`` refers to a sample in batched sample, a ``TypeError``
        will be raised.

        Args:
            sample_id: identifier of the sample
            new_position: updated position
        """
        result = self._collection.find_one({"_id": sample_id})
        if result is None:
            raise KeyError(f"Cannot find sample with id ({sample_id}).")
        if isinstance(result["position"], ObjectId):
            raise TypeError(f"Current sample is in a batch, you cannot update it position along.")
        self._collection.update_one({"_id": sample_id}, {"$set": {
            "position": new_position,
            "last_updated": datetime.now(),
        }})

    def query_sample(self, sample_id: ObjectId) -> Optional[str]:
        """
        Query current position of a sample

        Returns:
            The sample position name of the sample. If the sample's
            position has not been initialized, return ``None``.
        """
        sample = self._collection.find_one({"_id": sample_id})
        if isinstance(sample["position"], ObjectId):
            sample = self._collection.find_one({"_id": sample["position"]})
        return sample["position"]

    def find_possible_path(self, src: str, dest: str, container: Optional[str]) -> List[Dict[str, Any]]:
        """
        Find a possible path from give sample position (src) to another (dest)

        Args:
            src: the name of start sample position
            dest: the name of end sample position
            container: the name of required container, if None,
              will put no restriction on container (for test purpose only)

        Returns:
            A list of position connection with {
                "src": <str>,
                "dest": <str>,
                "task_name": <str, possible task name>
            }
        """
        if not self.is_valid_position(src):
            raise ValueError(f"Unknown sample position src ({src})")
        if not self.is_valid_position(dest):
            raise ValueError(f"Unknown sample position dest ({dest})")
        if container is None:
            container_criteria = {"$exists": True}
        else:
            container_criteria = container

        # returned structure:
        # [{
        #   "positions": [{"src": <str>, "dest": <str>, "container": <str>}, ...],
        #   "stops": <int>
        # }, ...]
        result = self._position_connection.aggregate([
            {'$match': {'src': src, 'container': container_criteria}},
            {'$graphLookup': {
                'from': self._position_connection.name,
                'startWith': '$src',
                'connectFromField': 'dest',
                'connectToField': 'src',
                'as': 'possible_dest',
                'depthField': 'stops',
                'restrictSearchWithMatch': {
                    'container': container_criteria,
                }
            }},
            {'$unwind': {'path': '$possible_dest'}},
            {'$project': {
                'src': '$possible_dest.src',
                'dest': '$possible_dest.dest',
                'task_name': '$possible_dest.task_name',
                'stops': '$possible_dest.stops'
            }},
            {'$group': {
                '_id': '$stops',
                'positions': {
                    '$addToSet': {
                        'src': '$src',
                        'dest': '$dest',
                        'task_name': '$task_name'
                    }
                }
            }},
            {'$project': {'_id': 0, 'positions': 1, 'stops': '$_id'}},
            {'$sort': {"stops": 1}},
        ])

        def get_stops() -> int:
            """Find the number of stop from src to dest,
              if not found, a ``ValueError`` will be raised."""
            for accessible_positions in result:
                positions = accessible_positions["positions"]
                for position in positions:
                    if position["src"] == dest:
                        stops = accessible_positions["stops"]
                        return stops
            raise ValueError(f"Cannot get from src ({src}) to "
                             f"dest ({dest}) with container ({container}).")

        def find_path_in_graph() -> List[Dict[str, Any]]:
            """Find a path from src to dest, which will search
              the graph (DAG) from leaves (dest) to root (src)"""
            stops = get_stops()
            path = []
            last_dest = dest

            for stop in range(stops - 1, 0, -1):
                for position in result[stop]:
                    if position["dest"] == last_dest:
                        path.append(position.copy())
                        last_dest = position["src"]
                        break

            path.reverse()
            return path

        return find_path_in_graph()

    def delete_sample(self, sample_id: ObjectId):
        """
        Remove a single sample from the database

        If cannot find this sample_id, a ``KeyError`` will be raised.
        If the sample type is not ``single_sample``, a ``TypeError`` will be raised.
        """
        result = self._collection.find_one({"_id": sample_id})
        if result is None:
            raise KeyError(f"Cannot find sample with id ({sample_id}).")
        if result["type"] != "single_sample":
            raise TypeError(f"Requested sample_id ({sample_id}) is not a single sample.")
        self._collection.delete_one({"_id": sample_id})

    def delete_sample_batch(self, batch_id: ObjectId):
        """
        Remove a sample batch from the database

        If cannot find this batch_id, a ``KeyError`` will be raised.
        If the sample type is not ``sample_batch``, a ``TypeError`` will be raised.
        """
        result = self._collection.find_one({"_id": batch_id})
        if result is None:
            raise KeyError(f"Cannot find sample batch with id ({batch_id}).")
        if result["type"] != "sample_batch":
            raise TypeError(f"Requested batch_id ({batch_id}) is not a sample batch.")
        self._collection.delete_one({"_id": batch_id})

        for sample_id in result["samples"]:
            self.update_sample_position(sample_id, new_position=result["position"])

    def is_valid_position(self, sample_position: str) -> bool:
        """
        Check if a sample position name is a valid sample position
        """
        return self._sample_position.find_one({"name": sample_position}) is not None
