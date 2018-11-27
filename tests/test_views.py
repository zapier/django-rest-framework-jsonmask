from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from . import factories, views


class DataMixin(object):

    def setUp(self):
        super(DataMixin, self).setUp()

        self.t1 = factories.TicketFactory()
        self.t1c1 = factories.CommentFactory(
            ticket=self.t1,
        )
        self.t1c2 = factories.CommentFactory(
            author=self.t1.author,
            ticket=self.t1,
        )

        self.t2 = factories.TicketFactory()
        self.t2c1 = factories.CommentFactory(
            ticket=self.t2,
        )
        self.t2c2 = factories.CommentFactory(
            author=self.t2.author,
            ticket=self.t2,
        )
        self.t2c3 = factories.CommentFactory(
            author=self.t2c1.author,
            ticket=self.t2,
        )


class TestViews(DataMixin, TestCase):

    def test_plain(self):
        url = reverse('ticket-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        self.assertEqual(resp.json(), [
            {
                'title': self.t1.title,
                'body': self.t1.body,
                'author': {
                    'username': self.t1.author.username,
                    'email': self.t1.author.email,
                },
                'comments': [
                    {
                        'body': self.t1c1.body,
                        'author': {
                            'username': self.t1c1.author.username,
                            'email': self.t1c1.author.email,
                        },
                    },
                    {
                        'body': self.t1c2.body,
                        'author': {
                            'username': self.t1c2.author.username,
                            'email': self.t1c2.author.email,
                        },
                    },
                ],
            },
            {
                'title': self.t2.title,
                'body': self.t2.body,
                'author': {
                    'username': self.t2.author.username,
                    'email': self.t2.author.email,
                },
                'comments': [
                    {
                        'body': self.t2c1.body,
                        'author': {
                            'username': self.t2c1.author.username,
                            'email': self.t2c1.author.email,
                        },
                    },
                    {
                        'body': self.t2c2.body,
                        'author': {
                            'username': self.t2c2.author.username,
                            'email': self.t2c2.author.email,
                        },
                    },
                    {
                        'body': self.t2c3.body,
                        'author': {
                            'username': self.t2c3.author.username,
                            'email': self.t2c3.author.email,
                        },
                    },
                ],
            }
        ])

    def test_no_comments(self):
        url = reverse('ticket-list')
        resp = self.client.get(url + '?excludes=comments')
        self.assertEqual(resp.status_code, 200)

        self.assertEqual(resp.json(), [
            {
                'title': self.t1.title,
                'body': self.t1.body,
                'author': {
                    'username': self.t1.author.username,
                    'email': self.t1.author.email,
                },
            },
            {
                'title': self.t2.title,
                'body': self.t2.body,
                'author': {
                    'username': self.t2.author.username,
                    'email': self.t2.author.email,
                },
            }
        ])

    def test_no_comments_via_fields(self):
        url = reverse('ticket-list')
        resp = self.client.get(url + '?fields=title,body,author')
        self.assertEqual(resp.status_code, 200)

        self.assertEqual(resp.json(), [
            {
                'title': self.t1.title,
                'body': self.t1.body,
                'author': {
                    'username': self.t1.author.username,
                    'email': self.t1.author.email,
                },
            },
            {
                'title': self.t2.title,
                'body': self.t2.body,
                'author': {
                    'username': self.t2.author.username,
                    'email': self.t2.author.email,
                },
            }
        ])

    def test_nested(self):
        url = reverse('ticket-list')
        resp = self.client.get(url + '?fields=title,author/username')
        self.assertEqual(resp.status_code, 200)

        self.assertEqual(resp.json(), [
            {
                'title': self.t1.title,
                'author': {
                    'username': self.t1.author.username,
                },
            },
            {
                'title': self.t2.title,
                'author': {
                    'username': self.t2.author.username,
                },
            }
        ])


class TestPerformance(DataMixin, TestCase):

    def setUp(self):
        super(TestPerformance, self).setUp()

        self.rf = RequestFactory()

    def get_viewset(self, request):
        view_instance = views.TicketViewSet()
        view_instance.request = request
        view_instance.request.user = AnonymousUser()
        view_instance.kwargs = {}
        view_instance.format_kwarg = 'format'
        return view_instance

    def test_default_num_queries(self):

        request = self.rf.get(
            reverse('ticket-list'),
        )
        view_instance = self.get_viewset(request)
        queryset = view_instance.get_queryset()
        serializer = view_instance.get_serializer(queryset, many=True)

        with self.assertNumQueries(4):
            """
            1. Load Tickets
            3. Prefetch Authors
            3. Prefetch Comments
            4. Prefetch Comment Authors
            """
            serializer.data

    def test_pruned_num_queries(self):

        request = self.rf.get(
            reverse('ticket-list'),
            data={'fields': 'title,body'},
        )
        view_instance = self.get_viewset(request)
        queryset = view_instance.get_queryset()
        serializer = view_instance.get_serializer(queryset, many=True)

        with self.assertNumQueries(1):
            """
            1. Load Tickets
            """
            data = serializer.data
            self.assertNotIn('comments', data[0])
            self.assertNotIn('author', data[0])

    def test_partially_pruned(self):

        request = self.rf.get(
            reverse('ticket-list'),
            data={'fields': 'title,body,author,comments/body'},
        )
        view_instance = self.get_viewset(request)
        queryset = view_instance.get_queryset()
        serializer = view_instance.get_serializer(queryset, many=True)

        with self.assertNumQueries(3):
            """
            1. Load Tickets
            3. Prefetch Authors
            3. Prefetch Comments
            """
            serializer.data


class TestSettings(DataMixin, TestCase):

    @override_settings(REST_FRAMEWORK_JSONMASK_FIELDS_NAME='asdf')
    def test_old_fields_name(self):
        url = reverse('ticket-list')
        resp = self.client.get(url + '?fields=title,body')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('author', resp.json()[0])
        self.assertIn('comments', resp.json()[0])

    @override_settings(REST_FRAMEWORK_JSONMASK_FIELDS_NAME='asdf')
    def test_override_fields_name(self):
        url = reverse('ticket-list')
        resp = self.client.get(url + '?asdf=title,body')
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('author', resp.json()[0])
        self.assertNotIn('comments', resp.json()[0])

    @override_settings(REST_FRAMEWORK_JSONMASK_EXCLUDES_NAME='asdf')
    def test_old_excludes_name(self):
        url = reverse('ticket-list')
        resp = self.client.get(url + '?excludes=title,body')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('title', resp.json()[0])
        self.assertIn('body', resp.json()[0])

    @override_settings(REST_FRAMEWORK_JSONMASK_EXCLUDES_NAME='asdf')
    def test_override_excludes_name(self):
        url = reverse('ticket-list')
        resp = self.client.get(url + '?asdf=title,body')
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('title', resp.json()[0])
        self.assertNotIn('body', resp.json()[0])
