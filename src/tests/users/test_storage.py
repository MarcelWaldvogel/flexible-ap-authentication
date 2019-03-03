# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time
from unittest import TestCase
from unittest.mock import Mock

from radguestauth.users.storage import UserIdentifier, UserData


class UserStorageTest(TestCase):
    def test_user_id_equality(self):
        """
        Checks if the equality of two UserIdentifier objects ignores the
        password and data attributes. This is needed as UserIdentifier objects
        without all attributes set are used e.g. for querying.
        """
        identifier1 = UserIdentifier('foo', 'bar', 'pass')
        identifier2 = UserIdentifier('foo', 'bar', 'word')

        self.assertEqual(identifier1, identifier2)

        identifier3 = UserIdentifier('foo', 'bar', 'word')
        testdata = UserData()
        testdata.max_num_joins = 12
        identifier3.user_data = testdata

        self.assertEqual(identifier1, identifier3)
        self.assertEqual(identifier2, identifier3)

        self.assertNotEqual(identifier1, UserIdentifier('foo', 'baz', 'pass'))
        self.assertNotEqual(identifier1, UserIdentifier('fo0', 'bar', 'pass'))
        self.assertNotEqual(identifier1, 'some other type')

    def test_str_representation(self):
        # incrementally adds attributes and checks if they appear in str(item).
        # The str representation is important for several chat commands.
        identifier = UserIdentifier('foo', 'bar')
        # str needs to work without password and data
        self.assertIn('foo', str(identifier))
        self.assertIn('bar', str(identifier))

        identifier.password = 'passw0rd!'
        self.assertIn('passw0rd!', str(identifier))

        data = UserData()
        state_str = data.state_string()
        self.assertIn(state_str, str(data))

        # this is 1970-01-01 00:01:40
        data.valid_until = 100
        data.num_joins = 42
        data.max_num_joins = 1234
        # keep some freedoms on the actual output
        self.assertIn('1970', str(data))
        self.assertIn('00:01:40', str(data))
        self.assertIn('42', str(data))
        self.assertIn('1234', str(data))

        data_str = str(data)
        identifier.user_data = data
        self.assertIn(data_str, str(identifier))

    def test_data_state_string(self):
        check_map = {
            UserData.JOIN_STATE_WAITING: 'waiting',
            UserData.JOIN_STATE_ALLOWED: 'allowed',
            UserData.JOIN_STATE_BLOCKED: 'blocked'
        }

        for state, representation in check_map.items():
            data = UserData()
            data.join_state = state
            self.assertIn(representation, data.state_string().lower())

    def test_mac_formatting(self):
        test_mac = 'aa:bb:cc:dd:e0:12'
        items_to_check = [
            test_mac, 'AA:BB:CC:DD:E0:12', 'AA-BB-CC-DD-E0-12',
            'aa-bb-cc-dd-e0-12', 'aa-bb-cc:Dd-e0-12'
        ]

        for addr in items_to_check:
            formatted_obj = UserIdentifier('a', addr).device_id_as_mac()
            formatted_static = UserIdentifier.format_mac(addr)
            self.assertEqual(formatted_obj, test_mac)
            self.assertEqual(formatted_static, test_mac)

    def _increment_num_join_helper(self, max_num_joins, num_joins, valid_until,
                                   expected_num_joins):
        data = UserData()
        data.max_num_joins = max_num_joins
        data.num_joins = num_joins
        data.valid_until = valid_until

        data.check_expired(True)

        self.assertEqual(data.num_joins, expected_num_joins)

    def _run_check_expired(self, data, expected_result):
        # with and without increment, the result should be the same
        self.assertEqual(data.check_expired(), expected_result)
        self.assertEqual(data.check_expired(True), expected_result)

    def test_check_expired_increment_num_joins(self):
        # with num limit only: Increment numbers
        self._increment_num_join_helper(10, 0, None, 1)
        self._increment_num_join_helper(10, 3, None, 4)
        # no limit: No increment
        self._increment_num_join_helper(0, 0, None, 0)
        self._increment_num_join_helper(0, 1, None, 1)
        self._increment_num_join_helper(0, 0, time.time() + 10000, 0)
        self._increment_num_join_helper(0, 1, time.time() + 10000, 1)
        # both limits: Increment again
        self._increment_num_join_helper(10, 0, time.time() + 10000, 1)
        self._increment_num_join_helper(10, 3, time.time() + 10000, 4)

    def test_check_expired_num(self):
        data = UserData()
        data.max_num_joins = 10

        self._run_check_expired(data, False)

    def test_check_expired_time(self):
        data = UserData()
        data.valid_until = time.time() + 10000

        self._run_check_expired(data, False)

    def test_check_expired_num_exceeded(self):
        data = UserData()
        data.max_num_joins = 10
        data.num_joins = 11

        self._run_check_expired(data, True)

    def test_check_expired_time_exceeded(self):
        data = UserData()
        data.valid_until = time.time() - 10000

        self._run_check_expired(data, True)

    def test_check_expired_time_and_num_valid(self):
        data = UserData()
        data.max_num_joins = 1
        data.valid_until = time.time() + 10000

        self._run_check_expired(data, False)

    def test_check_expired_time_and_num_one_exceeded(self):
        # num exceeded
        data = UserData()
        data.max_num_joins = 1
        data.num_joins = 2
        data.valid_until = time.time() + 10000

        self._run_check_expired(data, True)

        # time exceeded
        data = UserData()
        data.max_num_joins = 1
        data.num_joins = 0
        data.valid_until = time.time() - 10000

        self._run_check_expired(data, True)

    def test_check_expired_time_and_num_both_exceeded(self):
        data = UserData()
        data.max_num_joins = 1
        data.num_joins = 2
        data.valid_until = time.time() - 10000

        self._run_check_expired(data, True)

    def test_check_expired_pass_to_data(self):
        # the UserIdentifier call should be forwarded to the
        # UserData item
        data_mock = Mock(UserData)
        data_mock.check_expired.return_value = True

        user_id = UserIdentifier('name', 'device')
        user_id.user_data = data_mock

        self.assertTrue(user_id.check_expired())
        data_mock.check_expired.assert_called_once()

        data_mock.reset_mock()
        self.assertTrue(user_id.check_expired(True))
        data_mock.check_expired.assert_called_once_with(True)

    def test_check_expired_no_data(self):
        user_id = UserIdentifier('name', 'device')

        self.assertFalse(user_id.check_expired())
        self.assertFalse(user_id.check_expired(True))
