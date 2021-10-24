from enum import Enum, auto


class SamplePositionStatus(Enum):
    UNKNOWN = auto()
    EMPTY = auto()
    OCCUPIED = auto()
    LOCKED = auto()


class SampleView:
    def update_simple_view(self, sample_id, destination: str):
        ...

    def query_simple_id(self):
        ...

    def find_possible_path(self, from_, to):
        ...

    def delete_sample(self, sample_id):
        ...