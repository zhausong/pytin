from __future__ import unicode_literals

import json

from django.db import models
from django.utils import timezone

from assets.models import Server
from cmdb.lib import loader
from resources.models import Resource


class TaskTrackerStatus(object):
    STATUS_NEW = 'new'
    STATUS_PROGRESS = 'progress'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = (
        (STATUS_NEW, 'Request created.'),
        (STATUS_PROGRESS, 'Request in progress.'),
        (STATUS_SUCCESS, 'Request completed.'),
        (STATUS_FAILED, 'Request failed.'),
    )


class CloudTaskTracker(models.Model):
    task_class = models.CharField('Python class of the cloud task.', max_length=55, db_index=True)
    created_at = models.DateTimeField('Date created', auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField('Date updated', auto_now=True, db_index=True)
    status = models.CharField(max_length=25, db_index=True, choices=TaskTrackerStatus.STATUS_CHOICES,
                              default=TaskTrackerStatus.STATUS_NEW)

    context_json = models.TextField('Cloud command context.')
    return_json = models.TextField('Cloud command return data.')

    error = models.TextField('Error message in case of failed state.')

    def __unicode__(self):
        return "%s %s (%s)" % (self.id, self.task_class, self.status)

    @property
    def is_failed(self):
        return self.status == TaskTrackerStatus.STATUS_FAILED

    @property
    def is_success(self):
        return self.status == TaskTrackerStatus.STATUS_SUCCESS

    @property
    def is_progress(self):
        return self.status == TaskTrackerStatus.STATUS_PROGRESS

    @property
    def is_new(self):
        return self.status == TaskTrackerStatus.STATUS_NEW

    @property
    def is_ready(self):
        return self.is_failed or self.is_success

    @property
    def context(self):
        return json.loads(self.context_json)

    @context.setter
    def context(self, value):
        assert value

        self.context_json = json.dumps(value)

    @property
    def return_data(self):
        return json.loads(self.return_json)

    @return_data.setter
    def return_data(self, value):
        self.return_json = json.dumps(value)

    def progress(self):
        self.updated_at = timezone.now()
        self.status = TaskTrackerStatus.STATUS_PROGRESS
        self.save()

    def success(self, return_data=None):
        if not return_data:
            return_data = {}

        self.return_data = return_data
        self.status = TaskTrackerStatus.STATUS_SUCCESS
        self.save()

    def failed(self, error_message=None):
        if not error_message:
            error_message = ''

        self.error = error_message
        self.status = TaskTrackerStatus.STATUS_FAILED
        self.save()

    @property
    def task(self):
        tracked_task_class = loader.get_class(self.task_class)
        wrapped_task = tracked_task_class(self, **self.context)
        return wrapped_task

    @staticmethod
    def execute(cloud_task_class, **context):
        assert cloud_task_class

        full_cloud_task_class_name = "%s.%s" % (cloud_task_class.__module__, cloud_task_class.__name__)

        task_tracker = CloudTaskTracker(task_class=full_cloud_task_class_name)
        task_tracker.context = context
        task_tracker.save()

        task_tracker.task.execute()

        return task_tracker

    @staticmethod
    def get(tracker_id):
        assert tracker_id > 0

        return CloudTaskTracker.objects.get(pk=tracker_id)

    @staticmethod
    def find(**query):
        assert id > 0

        return CloudTaskTracker.objects.filter(**query)

    def get_result(self):
        if self.is_success:
            return self.return_data

        if self.is_failed:
            return self.error

        try:
            result_data = self.task.get_result()

            self.success(result_data)

            return result_data
        except Exception, ex:
            self.failed(ex.message)
            raise ex


class CmdbCloudConfig(object):
    """
    Entry point for the CMDB data query.
    """
    task_tracker = CloudTaskTracker

    def get_hypervisors(self):
        """
        Returns the known hypervisors from the cloud.
        :return:
        """
        return Server.active.filter(role='hypervisor', status=Resource.STATUS_INUSE).order_by('id')
