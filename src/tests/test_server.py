# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import TestCase
from radguestauth.server import json_rest_unpack


class ServerTest(TestCase):
    """
    Only tests helper methods in radguestauth.server

    The Flask app is tested with integration tests.
    """
    def test_json_rest_unpack_invalid(self):
        invalid_args = [
            'foobar', 4, {'a': 'b'}, None
        ]
        for arg in invalid_args:
            res = json_rest_unpack(arg)
            self.assertEqual(res, {})

    def test_json_rest_unpack(self):
        input_dict = {
            'attr1': {
                'type': 'type1',
                'value': [1]
            },
            'attr2': {
                'type': 'type2',
                'value': ['val']
            },
            'attr3': {
                'type': 'type3',
                'value': ['foo', 'bar', 2]
            },
        }

        res = json_rest_unpack(input_dict)

        self.assertDictEqual(res, {
            'attr1': '1',
            'attr2': 'val',
            'attr3': 'foo'
        })
