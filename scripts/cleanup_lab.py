from alab_management.config import config
from alab_management.db import get_collection


def clean_up_db():
    device_collection = get_collection(config["devices"]["device_db"])
    sample_position_collection = get_collection(config["sample_positions"]["sample_db"])

    device_collection.drop()
    sample_position_collection.drop()


if __name__ == '__main__':
    clean_up_db()
