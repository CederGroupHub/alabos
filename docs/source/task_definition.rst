=====================
Defining a new task
=====================


Similar to define devices, we need to inherit classes from :py:class:`BaseTask <alab_management.task_view.task.BaseTask>`.

.. autoclass:: alab_management.task_view.task.BaseTask

    .. automethod:: __init__
    .. automethod:: run


Register task
----------------


To make sure the task you defined can be loaded properly by the system, you need to register it in the system.

We provide a function :py:meth:`add_task <alab_management.task_view.task.add_task>` to register a device.

.. code-block:: python

  from alab_management import add_task
  from .tasks.heating import Heating

  add_task(Heating)

It doesn't matter where you register the device as long as the code can be executed. But we recommend it be defined in
the ``__init__.py`` in the root dir to make sure it can always be reached.