"""This module contains the Moving task."""

from traceback import format_exc

from alab_management.task_view.task import BaseTask
from alab_management.user_input import request_user_input

from .program_graphs.program_graph import (
    get_parent_path,
    reduce_position_name,
    total_graph,
)


class Moving(BaseTask):
    """This class represents the Moving task."""

    def __init__(self, sample: str, destination: str, *args, **kwargs):
        """Initialize the Moving task."""
        super().__init__(*args, **kwargs)
        self.sample = sample
        self.destination = destination

    def plan(self):
        """Plan the movement of the sample."""
        sample = self.lab_view.get_sample(sample=self.sample)
        source = sample.position

        source_reduced = reduce_position_name(source)
        dest_reduced = reduce_position_name(self.destination)

        path_reduced, arms_required = get_parent_path(source_reduced, dest_reduced)
        request = {}
        lookup_per_parent = {}
        for position in path_reduced:
            parent_device = self.lab_view.get_sample_position_parent_device(position)
            if parent_device not in request:
                request[parent_device] = {}
            if parent_device is not None:
                position_pieces = position.split("/")
                if parent_device in position_pieces:
                    position_pieces.remove(parent_device)
                position_processed = "/".join(position_pieces)
            else:
                position_processed = position
            request[parent_device][
                position_processed
            ] = 1  # need one position per parent.
            lookup_per_parent[position] = (parent_device, position_processed)

        for arm in arms_required:
            request[arm] = {}  # need arm devices without any sample positions.

        return request, lookup_per_parent

    def get_programs_to_run(self, source, destination):
        """Get the programs to run to move a sample from source to destination."""
        programs = total_graph[source][destination]["programs"]
        robot = total_graph[source][destination]["robot"]
        return programs, robot

    def run(self):
        """Run the Moving task."""
        sample_entry = self.lab_view.get_sample(self.sample)
        sample_id = sample_entry.sample_id

        if sample_entry.position == self.destination:
            return

        request, path_reduced = self.plan()

        with self.lab_view.request_resources(request) as (devices, sample_positions):
            path_as_list = list(path_reduced.keys())
            for j, (parent0, parent1) in enumerate(
                zip(path_as_list, path_as_list[1:], strict=False)
            ):
                if j == 0:
                    position0 = sample_entry.position
                else:
                    k0, k1 = path_reduced[parent0]
                    position0 = sample_positions[k0][k1][0]
                if j == len(path_as_list) - 2:
                    position1 = self.destination
                else:
                    k0, k1 = path_reduced[parent1]
                    position1 = sample_positions[k0][k1][0]
                programs, robot = self.get_programs_to_run(position0, position1)
                arm = devices[robot]

                arm.set_message(
                    f"Moving sample {self.sample} from {position0} to {position1}"
                )

                for k in range(3):
                    try:
                        arm.run_programs(programs)
                    except Exception:
                        if k == 2:
                            raise
                        response = request_user_input(
                            task_id=self.task_id,
                            prompt=f"Error while moving sample from {position0} to {position1} "
                            f"(1) Set the robot arm to home position;\n"
                            f"(2) If you want to skip this movement, put sample to {position1}. If you want to "
                            f"retry the task, put sample to {position0}. Press abort to stop.\n"
                            f"The error is {format_exc()}.",
                            options=["Skip", "Retry", "Abort"],
                        )
                        if response == "Abort":
                            raise
                        if response == "Skip":
                            break
                    else:
                        break

                arm.set_message("")

                self.lab_view.move_sample(
                    sample=sample_id,
                    position=position1,
                )
