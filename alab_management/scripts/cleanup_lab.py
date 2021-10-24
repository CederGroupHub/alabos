from ..config import config
from ..db import get_collection


def clean_up_db():
    device_collection = get_collection(config["devices"]["device_db"])
    task_collection = get_collection(config["tasks"]["task_db"])
    sample_position_collection = get_collection(config["sample_positions"]["sample_db"])

    device_collection.drop()
    task_collection.drop()
    sample_position_collection.drop()


def main():
    clean_up_db()
