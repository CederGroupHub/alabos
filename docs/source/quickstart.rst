Quick Start
===========

.. note::
  This tutorial is still under construction. We have only included the initializing program (definition reader).

Defining devices
----------------

To define a device, you should inherit from :py:class:`BaseDevice <alab_management.device_def.base_device.BaseDevice>`.
Here is the code sample. For more, please refer to `example <https://github.com/idocx/alab_management/tree/master/example/devices>`_ in the repo .

.. note::

  TODO: add explanations for each methods

.. code-block:: python

  @dataclass
  class Furnace(BaseDevice):
      name: str
      address: str
      port: int = 502

      description: ClassVar[str] = "Simple furnace"

      def __post_init__(self):
          self.driver = None

      def init(self):
          self.driver = FurnaceController(address=self.address)

      @property
      def sample_positions(self):
          return [
              SamplePosition(
                  "{name}.inside".format(name=self.name),
                  description="The position inside the furnace, where the samples are heated"
              ),
              SamplePosition(
                  "furnace_table",
                  description="Temporary position to transfer samples"
              )
          ]

Defining tasks
----------------

Similar to define devices, we need to inherit classes from :py:class:`BaseTask <alab_management.op_def.base_operation.BaseTask>`.

For moving operation, we need it to inherit from :py:class:`BaseMovingOperation <alab_management.op_def.base_operation.BaseMovingOperation>`.