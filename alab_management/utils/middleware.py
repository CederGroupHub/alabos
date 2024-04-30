from dramatiq import get_broker
from dramatiq_abort import Abortable, backends

from alab_management.utils.data_objects import get_collection


def register_abortable_middleware():
    abortable = Abortable(
        backend=backends.MongoDBBackend(collection=get_collection("abortable"))
    )
    get_broker().add_middleware(abortable)
