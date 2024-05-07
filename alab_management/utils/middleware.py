from dramatiq import get_broker
from dramatiq_abort import Abortable, backends

from alab_management.utils.data_objects import get_collection

__abortable_registered = False


def register_abortable_middleware():
    """This function registers the abortable middleware to the dramatiq broker."""
    global __abortable_registered  # pylint: disable=global-statement
    if not __abortable_registered:
        abortable = Abortable(
            backend=backends.MongoDBBackend(collection=get_collection("abortable"))
        )
        get_broker().add_middleware(abortable)
        __abortable_registered = True
