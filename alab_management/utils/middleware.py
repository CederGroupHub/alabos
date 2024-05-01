import dramatiq
from dramatiq import get_broker
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.middleware.age_limit import AgeLimit
from dramatiq.middleware.callbacks import Callbacks
from dramatiq.middleware.pipelines import Pipelines
from dramatiq.middleware.prometheus import Prometheus
from dramatiq.middleware.retries import Retries
from dramatiq.middleware.shutdown import ShutdownNotifications
from dramatiq.middleware.time_limit import TimeLimit
from dramatiq_abort import Abortable, backends

from alab_management.utils.data_objects import get_collection


def patch_dramatiq():
    class PatchedPrometheus(Prometheus):
        @property
        def forks(self):
            return []

    broker_middleware = [
        PatchedPrometheus, AgeLimit, TimeLimit,
        ShutdownNotifications, Callbacks, Pipelines, Retries
    ]

    broker_middleware = [m() for m in broker_middleware]

    rabbitmq_broker = RabbitmqBroker(
        host="127.0.0.1",
        port=5672,
        heartbeat=60,
        connection_attempts=5,
        blocked_connection_timeout=30,
        middleware=broker_middleware
    )
    dramatiq.set_broker(rabbitmq_broker)


def register_abortable_middleware():
    abortable = Abortable(
        backend=backends.MongoDBBackend(collection=get_collection("abortable"))
    )
    get_broker().add_middleware(abortable)
