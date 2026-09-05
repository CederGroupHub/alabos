from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock

from bson import ObjectId

from alab_management.lab_view import LabView


class TestSampleLocationCleanup(TestCase):
    def test_error_cleanup_releases_occupancy_without_removing_sample(self):
        task_id = ObjectId()
        sample_id = ObjectId()
        lab_view = LabView.__new__(LabView)
        lab_view._task_id = task_id
        lab_view._LabView__task_entry = {
            "type": "Moving",
            "samples": [{"sample_id": sample_id, "name": "sample"}],
        }
        lab_view._sample_view = MagicMock()
        lab_view._sample_view.get_sample.return_value = SimpleNamespace(
            position="rack/slot/1"
        )
        lab_view._resource_requester = MagicMock()
        lab_view.request_user_input = MagicMock(return_value="OK")

        lab_view.request_cleanup(error_message="test failure")

        lab_view._sample_view.release_sample_occupancy.assert_called_once_with(
            sample_id=sample_id,
            task_id=task_id,
            task_type="Moving",
            actor="alabos",
            reason="Task cleanup after unrecoverable error",
        )
        lab_view._sample_view.remove_sample_from_lab.assert_not_called()
        lab_view._resource_requester.release_all_resources.assert_called_once_with()

    def test_cancel_cleanup_releases_each_sample_occupancy(self):
        lab_view = MagicMock()
        sample_ids = [ObjectId(), ObjectId()]

        LabView.release_samples_occupancy(
            lab_view,
            [{"sample_id": sample_id} for sample_id in sample_ids],
            reason="Task was cancelled",
        )

        self.assertEqual(2, lab_view.release_sample_occupancy.call_count)
        for sample_id in sample_ids:
            lab_view.release_sample_occupancy.assert_any_call(
                sample_id, reason="Task was cancelled"
            )
