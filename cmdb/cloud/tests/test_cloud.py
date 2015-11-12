from __future__ import unicode_literals

from django.test import TestCase

from cloud.models import CloudConfig, CloudTaskTracker

from cloud.tests import MockHypervisorBackend


class CloudControllerTest(TestCase):
    def test_controller_create_success(self):
        cloud = CloudConfig()

        backend = MockHypervisorBackend(cloud)

        task_tracker = backend.create_vps(ram=1024, cpu=2, hdd=50)

        self.assertEqual(CloudTaskTracker.STATUS_NEW, task_tracker.status)

        # report progress to tracker
        task_tracker.progress()
        self.assertEqual(CloudTaskTracker.STATUS_PROGRESS, task_tracker.status)

        # run task somewhere (or locally)
        wrapped_task = task_tracker.task
        wrapped_task.execute()

        # report that the task is finished
        task_tracker.success(wrapped_task.result)

        self.assertEqual(CloudTaskTracker.STATUS_SUCCESS, task_tracker.status)

        print task_tracker.return_data

    def test_controller_create_success_sync(self):
        cloud = CloudConfig()

        backend = MockHypervisorBackend(cloud)

        task_tracker = backend.create_vps_sync(ram=1024, cpu=2, hdd=50)

        self.assertEqual(CloudTaskTracker.STATUS_SUCCESS, task_tracker.status)

        print task_tracker.return_data
