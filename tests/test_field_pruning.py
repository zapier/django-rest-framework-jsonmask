from __future__ import unicode_literals

from django.test import TestCase
from django.urls import reverse


class TestRawFieldPruning(TestCase):
    """
    Tests that endpoints can easily be
    """

    def test_default_rest_framework_behavior(self):
        """
        This is more of an example really, showing default behavior
        """
        url = reverse('raw-data')
        response = self.client.get('%s?fields=a,b' % url)
        self.assertEqual(200, response.status_code)

        expected = {
            'a': 'test',
            'b': {
                'nested': 'test',
            },
        }

        assert expected == response.json()

        response = self.client.get('%s?fields=d/a/d' % url)
        self.assertEqual(200, response.status_code)

        expected = {
            'd': {
                'a': {
                    'd': 'value',
                },
            },
        }

        assert expected == response.json()
