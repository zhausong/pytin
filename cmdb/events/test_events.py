from django.test import TestCase

from events.models import HistoryEvent
from resources.models import Resource


class HistoryEventTest(TestCase):
    def test_resource_option_change_history(self):
        res1 = Resource.create(name='res1')

        self.assertEqual(1, len(HistoryEvent.objects.all()))

        res1.set_option('testfield', 'testval1')

        self.assertEqual(2, len(HistoryEvent.objects.all()))

        res1.set_option('testfield', 'testval2')

        self.assertEqual(3, len(HistoryEvent.objects.all()))

        events = HistoryEvent.objects.filter(type=HistoryEvent.UPDATE)

        self.assertEqual(2, len(events))
        self.assertEqual(HistoryEvent.UPDATE, events[0].type)
        self.assertEqual('testfield', events[0].field_name)
        self.assertEqual(None, events[0].field_old_value)
        self.assertEqual('testval1', events[0].field_new_value)

        self.assertEqual(HistoryEvent.UPDATE, events[1].type)
        self.assertEqual('testfield', events[1].field_name)
        self.assertEqual('testval1', events[1].field_old_value)
        self.assertEqual('testval2', events[1].field_new_value)

    def test_resource_change_history(self):
        res1 = Resource.create(name='res1')
        res2 = Resource.create(name='res2', parent=res1)

        # two create events
        events = HistoryEvent.objects.all()
        self.assertEqual(2, len(events))
        self.assertEqual(HistoryEvent.CREATE, events[0].type)
        self.assertEqual('res1', events[0].resource.name)
        self.assertEqual(HistoryEvent.CREATE, events[1].type)
        self.assertEqual('res2', events[1].resource.name)

        # Resource field changes
        res1.name = 'res1_new'
        res1.save()

        res2.name = 'res2_new'
        res2.parent_id = 0
        res2.save()

        events = HistoryEvent.objects.all()
        self.assertEqual(5, len(events))

        events = HistoryEvent.objects.filter(type=HistoryEvent.UPDATE)
        self.assertEqual(3, len(events))
        self.assertEqual('res1_new', events[0].resource.name)
        self.assertEqual('name', events[0].field_name)
        self.assertEqual('res1', events[0].field_old_value)
        self.assertEqual('res1_new', events[0].field_new_value)

        self.assertEqual('res2_new', events[1].resource.name)
        self.assertEqual('parent_id', events[1].field_name)
        self.assertEqual(unicode(res1.id), events[1].field_old_value)
        self.assertEqual('0', events[1].field_new_value)