from __future__ import unicode_literals

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from assets.models import Server, ServerPort
from events.models import HistoryEvent
from resources.models import Resource


class ResourcesAPITests(APITestCase):
    def setUp(self):
        super(ResourcesAPITests, self).setUp()

        user_name = 'admin'

        user, created = User.objects.get_or_create(username=user_name, password=user_name, email='admin@admin.com',
                                                   is_staff=True)
        token, created = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    def test_resource_retrieve_paged(self):
        for x in range(1, 25):
            ServerPort.objects.create(name='res-%s' % x)

        response = self.client.get('/v1/resources/', data={'type': 'ServerPort'}, format='json')

        self.assertEqual(200, response.status_code)
        self.assertEqual(10, len(response.data['results']))

        response = self.client.get(response.data['next'], format='json')
        self.assertEqual(200, response.status_code)
        self.assertEqual(10, len(response.data['results']))

    def test_resource_delete(self):
        res1 = Resource.objects.create(name='res1')
        res2 = Server.objects.create(name='res2', parent=res1)

        response = self.client.delete('/v1/resources/%s/' % res2.id, format='json')  # remove physical server

        self.assertEqual(204, response.status_code)  # no data on delete

        res2.refresh_from_db()

        self.assertEqual('res2', res2.name)
        self.assertEqual(Resource.STATUS_DELETED, res2.status)
        self.assertEqual('Server', res2.type)

    def test_resource_create(self):
        payload = {
            'status': Resource.STATUS_INUSE,
            'name': 'res1',
            'options': [
                {'name': 'somename1', 'value': 'someval1'},
                {'name': 'somename2', 'value': 'someval2'}
            ]
        }

        response = self.client.post('/v1/resources/', payload, format='json')

        self.assertEqual(201, response.status_code)
        self.assertEqual('res1', response.data['name'])
        self.assertEqual('Resource', response.data['type'])
        self.assertEqual(2, len(response.data['options']))
        self.assertEqual('somename1', response.data['options'][0]['name'])
        self.assertEqual('someval1', response.data['options'][0]['value'])
        self.assertEqual('somename2', response.data['options'][1]['name'])
        self.assertEqual('someval2', response.data['options'][1]['value'])

    def test_resource_update_journaling_off(self):
        """
        Testing updates with joutnaling on/off.
        :return:
        """
        res1 = Resource.objects.create(name='res1')
        res2 = Server.objects.create(name='res2', parent=res1, extrafield='extravalue', extrafield2='extravalue2')

        self.assertEqual(4, len(HistoryEvent.objects.all()))

        # journaled updates
        response = self.client.put('/v1/resources/%s/' % res2.id,
                                   {'status': Resource.STATUS_INUSE,
                                    'name': 'res2_ed',
                                    'options': [
                                        {'name': 'extrafield', 'value': 'extravalue_ed'},
                                        {'name': 'extrafield2', 'value': 'extravalue2_ed'}
                                    ]
                                    },
                                   format='json')
        self.assertEqual(200, response.status_code)
        self.assertEqual(8, len(HistoryEvent.objects.all()))

        # journaling is off
        self.client.put('/v1/resources/%s/' % res2.id,
                        {'options': [
                            {'name': 'extrafield', 'value': 'extravalue_ed2', 'journaling': False},
                            {'name': 'extrafield2', 'value': 'extravalue2_ed2'}
                        ]
                        },
                        format='json')
        self.assertEqual(200, response.status_code)
        self.assertEqual(9, len(HistoryEvent.objects.all()))

    def test_resource_update(self):
        res1 = Resource.objects.create(name='res1')
        res2 = Server.objects.create(name='res2', parent=res1, extrafield='extravalue', extrafield2='extravalue2')

        response = self.client.put('/v1/resources/%s/' % res2.id,
                                   {'status': Resource.STATUS_INUSE,
                                    'name': 'res2_ed',
                                    'options': [
                                        {'name': 'extrafield', 'value': 'extravalue_ed'},
                                        {'name': 'extrafield2', 'value': 'extravalue2_ed'}
                                    ]
                                    },
                                   format='json')

        self.assertEqual(200, response.status_code)
        self.assertEqual('res2_ed', response.data['name'])
        self.assertEqual(Resource.STATUS_INUSE, response.data['status'])
        self.assertEqual('Server', response.data['type'])
        self.assertEqual(res2.id, response.data['id'])
        self.assertEqual(1, response.data['parent'])
        self.assertEqual(2, len(response.data['options']))
        self.assertEqual('extrafield2', response.data['options'][0]['name'])
        self.assertEqual('extravalue2_ed', response.data['options'][0]['value'])
        self.assertEqual('extrafield', response.data['options'][1]['name'])
        self.assertEqual('extravalue_ed', response.data['options'][1]['value'])

        res2.refresh_from_db()

        self.assertEqual('res2_ed', res2.name)
        self.assertEqual(Resource.STATUS_INUSE, res2.status)
        self.assertEqual('Server', res2.type)
        self.assertEqual('extravalue_ed', res2.get_option_value('extrafield'))

    def test_resource_details(self):
        res1 = Resource.objects.create(name='res1')
        res2 = Server.objects.create(name='res2', parent=res1)

        response = self.client.get('/v1/resources/%s/' % res2.id, format='json')

        self.assertEqual(200, response.status_code)

        self.assertEqual('res2', response.data['name'])
        self.assertEqual(Resource.STATUS_FREE, response.data['status'])
        self.assertEqual('Server', response.data['type'])
        self.assertEqual(res2.id, response.data['id'])
        self.assertEqual(1, response.data['parent'])

    def test_resources_filter(self):
        res1 = Resource.objects.create(name='res1', param1='paramval1')
        res2 = Server.objects.create(name='res2', parent=res1, param2='paramval2')
        res3 = ServerPort.objects.create(name='res3', parent=res2, param3='paramval3', param1='paramval1')

        response = self.client.get('/v1/resources/', format='json')

        self.assertEqual(200, response.status_code)
        self.assertEqual(3, response.data['count'])

        # filter by param1
        response = self.client.get('/v1/resources/', data={'param1': 'paramval1'}, format='json')

        self.assertEqual(200, response.status_code)
        self.assertEqual(2, response.data['count'])

        Resource.objects.create(name='Test re')
        Resource.objects.create(name='Test res2')
        Resource.objects.create(name='Super res3')
        Resource.objects.create(name='Surest res4')

        # all set
        response = self.client.get('/v1/resources/', {}, format='json')
        self.assertEqual(200, response.status_code)

        self.assertEqual(7, response.data['count'])
        self.assertEqual(7, len(response.data['results']))

        # 'Test' word
        response = self.client.get('/v1/resources/', {'name__contains': 'Test'}, format='json')
        self.assertEqual(200, response.status_code)

        self.assertEqual(2, response.data['count'])
        self.assertEqual(2, len(response.data['results']))

        # Exact match
        response = self.client.get('/v1/resources/', {'name': 'Test re'}, format='json')
        self.assertEqual(200, response.status_code)

        self.assertEqual(1, response.data['count'])
        self.assertEqual(1, len(response.data['results']))
