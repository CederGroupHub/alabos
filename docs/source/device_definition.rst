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
