from alab_control.furnace_epc_3016 import FurnaceController

from alab_management.device_def import BaseDevice, SamplePosition


class Furnace(BaseDevice, alias="bakery_oven"):
    def __init__(self, name, address, port):
        super(Furnace, self).__init__(name=name)
        self.furnace_controller = FurnaceController(address=address, port=port)

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                "{name}.inside".format(name=self.name),
                num=4,
                description="The position inside the furnace, where the samples are heated"
            ),
            SamplePosition(
                "furnace_table",
                num=1,
                description="Temporary position to transfer samples"
            )
        ]
