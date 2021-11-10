.. _defining_device:

=====================
Defining a new device
=====================

To define a device, you should inherit from :py:class:`BaseDevice <alab_management.device_view.base_device.BaseDevice>`.
Here is the code sample. For more, please refer to `example <https://github.com/idocx/alab_management/tree/master/example/devices>`_ in the repo .


.. autoclass:: alab_management.device_view.device.BaseDevice

    .. automethod:: __init__
    .. automethod:: emergent_stop
    .. autoproperty:: sample_positions


Register device
----------------

To make sure the device you defined can be loaded properly by the system, you need to register it in the system.

We provide a function :py:meth:`add_device <alab_management.device_view.device.add_device>` to register a device.

.. code-block:: python

  from alab_management import add_device
  from .devices.furnace import Furnace

  add_device(Furnace(name="furnace_1", address="127.0.0.1"))

It doesn't matter where you register the device as long as the code can be executed. But we recommend it be defined in
the ``__init__.py`` in the root dir to make sure it can always be reached.