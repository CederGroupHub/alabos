from alab_management.task_view.task import BaseTask

class MeasureRGB(BaseTask):
    """Measurement task definition."""
    def __init__(self, R=0, G=0, B=0, **kwargs):
        super().__init__(**kwargs)
        self.R = R
        self.G = G
        self.B = B

    def run(self):
        print('Running a job')
        with self.lab_view.request_resources({"rgb": {}}) as (devices, _):
            print(devices)
            return devices["rgb"].measure(self.R, self.G, self.B)
