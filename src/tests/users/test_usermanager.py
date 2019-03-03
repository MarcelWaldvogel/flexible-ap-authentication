# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time

from unittest import TestCase
from unittest.mock import Mock

from radguestauth.users.usermanager import UserManager
from radguestauth.users.storage import UserIdentifier, UserData


# N.B.: those tests heavily rely on the custom UserIdentifier equality
# (considered equal if name and device match), e.g. for set comparisons
class UserManagerTest(TestCase):
    def _get_mgr_with_one_user(self):
        return self._get_mgr_with_one_user_and_data(None)

    def _get_mgr_with_one_user_and_data(self, data):
        testuser = UserIdentifier('foo', 'bar')
        mgr = self._get_mgr_with(testuser, data)
        return mgr, testuser

    def _get_mgr_with(self, testuser, data):
        mgr = UserManager()
        # add the user first
        mgr.add_request(testuser)
        testuser.user_data = data
        mgr.update(testuser)
        mgr.finish_request()
        self.assertListEqual(list(mgr.list_users()), [testuser])
        self.assertFalse(mgr.is_request_pending())

        return mgr

    def _get_mgr_with_two_users(self):
        mgr = UserManager()
        testuser1 = UserIdentifier('foo', 'bar')
        testuser2 = UserIdentifier('john doe', 'phone')

        mgr.add_request(testuser1)
        mgr.update(testuser1)
        mgr.finish_request()

        mgr.add_request(testuser2)
        mgr.update(testuser2)
        mgr.finish_request()

        return mgr, testuser1, testuser2

    def assert_state_new(self, result):
        self.assertEqual(result, UserData.JOIN_STATE_NEW)

    def assert_state_waiting(self, result):
        self.assertEqual(result, UserData.JOIN_STATE_WAITING)

    def assert_state_blocked(self, result):
        self.assertEqual(result, UserData.JOIN_STATE_BLOCKED)

    def assert_state_allowed(self, result):
        self.assertEqual(result, UserData.JOIN_STATE_ALLOWED)

    def test_initial_state(self):
        mgr = UserManager()

        self.assertFalse(mgr.is_request_pending())
        self.assertListEqual(list(mgr.list_users()), [])
        self.assert_state_new(
            mgr.may_join(UserIdentifier('some test', ''))
        )

    def test_may_join_no_userdata(self):
        mgr, testuser = self._get_mgr_with_one_user()

        result = mgr.may_join(testuser)

        self.assert_state_blocked(result)

    def test_may_join_invalid_data(self):
        mgr, testuser = self._get_mgr_with_one_user()

        result = mgr.may_join('invalid data')

        self.assert_state_blocked(result)

    def test_may_join_new_user(self):
        mgr, testuser = self._get_mgr_with_one_user()

        result = mgr.may_join(UserIdentifier('other', 'device'))

        self.assert_state_new(result)

    def test_may_join_pending_request(self):
        mgr, testuser = self._get_mgr_with_one_user()
        mgr.add_request(UserIdentifier('other', 'device'))

        # request user should be in waiting state, but others
        # still in new state.
        result = mgr.may_join(UserIdentifier('other', 'device'))
        result_new_user = mgr.may_join(UserIdentifier('other2', 'device2'))

        self.assert_state_waiting(result)
        self.assert_state_new(result_new_user)

    def test_may_join_user_expired(self):
        data = Mock(UserData)
        data.check_expired.return_value = True
        data.join_state = UserData.JOIN_STATE_ALLOWED
        mgr, testuser = self._get_mgr_with_one_user_and_data(data)

        result = mgr.may_join(testuser)

        data.check_expired.assert_called_once_with(True)
        self.assert_state_new(result)
        # user should have been removed
        self.assertListEqual(list(mgr.list_users()), [])

    def test_may_join_user_not_expired(self):
        data = Mock(UserData)
        data.check_expired.return_value = False
        data.join_state = UserData.JOIN_STATE_ALLOWED
        mgr, testuser = self._get_mgr_with_one_user_and_data(data)

        result = mgr.may_join(testuser)

        data.check_expired.assert_called_once_with(True)
        self.assert_state_allowed(result)

    def test_may_join_blocked_user(self):
        data = UserData()
        data.max_num_joins = 1
        data.num_joins = 2
        valid_time = time.time() - 10000
        data.valid_until = valid_time
        data.join_state = UserData.JOIN_STATE_BLOCKED
        mgr, testuser = self._get_mgr_with_one_user_and_data(data)

        result = mgr.may_join(testuser)

        self.assert_state_blocked(result)
        # attributes should be unchanged
        self.assertEqual(data.max_num_joins, 1)
        self.assertEqual(data.num_joins, 2)
        self.assertEqual(data.valid_until, valid_time)

    def test_may_join_other_device(self):
        # reject other devices
        data = UserData()
        data.max_num_joins = 1
        data.valid_until = time.time() + 10000
        mgr, testuser = self._get_mgr_with_one_user_and_data(data)

        result = mgr.may_join(UserIdentifier('foo', 'someotherdevice'))

        self.assert_state_blocked(result)

        # this should also apply if the stored user has no assigned data
        # (i.e. no state)
        mgr, testuser = self._get_mgr_with_one_user()

        result = mgr.may_join(UserIdentifier('foo', 'someotherdevice'))

        self.assert_state_blocked(result)

    def test_may_join_other_name(self):
        # reject other users having the same device ID
        data = UserData()
        data.max_num_joins = 1
        data.valid_until = time.time() + 10000
        mgr, testuser = self._get_mgr_with_one_user_and_data(data)

        result = mgr.may_join(UserIdentifier('other', 'bar'))

        self.assert_state_blocked(result)

        # this should also apply if the stored user has no assigned data
        # (i.e. no state)
        mgr, testuser = self._get_mgr_with_one_user()

        result = mgr.may_join(UserIdentifier('other', 'bar'))

        self.assert_state_blocked(result)

    def test_may_join_other_name_request(self):
        # also reject if a device ID is used by the current request user
        mgr, testuser = self._get_mgr_with_one_user()
        mgr.add_request(UserIdentifier('testuser2', 'device'))

        result = mgr.may_join(UserIdentifier('other', 'device'))

        self.assert_state_blocked(result)

    def test_may_join_other_name_different_id_format(self):
        # also reject when the device IDs are formatted differently
        data = UserData()
        data.max_num_joins = 1
        data.valid_until = time.time() + 10000
        user = UserIdentifier('foo', 'AB-C0')
        mgr = self._get_mgr_with(user, data)

        result = mgr.may_join(UserIdentifier('other', 'ab:c0'))

        self.assert_state_blocked(result)

    def test_may_join_device_id_reuse(self):
        mgr, testuser = self._get_mgr_with_one_user()
        # At this point, the user below would be rejected (see previous test).
        # After removing the test user 'foo', other users should be able
        # to join with this device ID
        mgr.remove(testuser)

        result = mgr.may_join(UserIdentifier('other', 'bar'))

        self.assert_state_new(result)

    def test_may_join_other_object(self):
        # should work with an independent object having the same attributes
        data = UserData()
        data.max_num_joins = 1
        data.valid_until = time.time() + 10000
        mgr, testuser = self._get_mgr_with_one_user_and_data(data)

        result = mgr.may_join(UserIdentifier('foo', 'bar'))

        self.assert_state_allowed(result)

    def test_add_request_invalid_data(self):
        mgr = UserManager()

        self.assertFalse(mgr.add_request('invalid data'))
        self.assertFalse(mgr.is_request_pending())
        self.assertIsNone(mgr.get_request())

    def test_add_request(self):
        mgr = UserManager()
        testuser = UserIdentifier('foo', 'bar')

        self.assertFalse(mgr.is_request_pending())
        res = mgr.add_request(testuser)

        self.assertTrue(res)
        self.assertTrue(mgr.is_request_pending())
        self.assertEqual(testuser, mgr.get_request())
        self.assertListEqual(list(mgr.list_users()), [])

    def test_add_request_duplicate(self):
        mgr = UserManager()
        testuser = UserIdentifier('foo', 'bar')

        self.assertFalse(mgr.is_request_pending())
        res1 = mgr.add_request(testuser)
        res2 = mgr.add_request(UserIdentifier('test', '2'))

        self.assertTrue(res1)
        self.assertFalse(res2)
        self.assertTrue(mgr.is_request_pending())
        self.assertEqual(testuser, mgr.get_request())
        self.assertListEqual(list(mgr.list_users()), [])

    def test_add_request_existing(self):
        mgr, testuser = self._get_mgr_with_one_user()
        # neither the same object nor another one with the same attributes
        # may be accepted
        res1 = mgr.add_request(testuser)
        res2 = mgr.add_request(UserIdentifier('foo', 'bar'))

        self.assertFalse(res1)
        self.assertFalse(res2)
        self.assertFalse(mgr.is_request_pending())

    def test_add_two_users(self):
        mgr = UserManager()
        testuser1 = UserIdentifier('foo', 'bar')
        testuser2 = UserIdentifier('john doe', 'phone')

        res1 = mgr.add_request(testuser1)
        mgr.update(testuser1)
        mgr.finish_request()

        res2 = mgr.add_request(testuser2)
        mgr.update(testuser2)
        mgr.finish_request()

        self.assertTrue(res1)
        self.assertTrue(res2)
        self.assertFalse(mgr.is_request_pending())
        userlist = mgr.list_users()
        self.assertEqual(len(userlist), 2)
        self.assertIn(testuser1, userlist)
        self.assertIn(testuser2, userlist)

    def test_add_request_user_has_password(self):
        mgr = UserManager()
        testuser = UserIdentifier('foo', 'bar')

        pw = mgr.generate_password()
        mgr.add_request(testuser)

        requested = mgr.get_request()
        self.assertEqual(pw, requested.password)

    def test_update_request(self):
        mgr = UserManager()
        testuser = UserIdentifier('foo', 'bar')

        pw = mgr.generate_password()
        mgr.add_request(testuser)
        testdata = UserData()
        testuser.user_data = testdata
        testuser.password = pw
        mgr.update(testuser)
        mgr.finish_request()

        # generate another password, which should not affect the stored one
        mgr.generate_password()

        found = mgr.find('foo')
        self.assertEqual(found.name, testuser.name)
        self.assertEqual(found.device_id, testuser.device_id)
        self.assertEqual(found.password, pw)
        self.assertEqual(found.user_data, testdata)

    def test_reject_user_request(self):
        mgr = UserManager()
        # finish the request without update
        testuser = UserIdentifier('foo', 'bar')
        mgr.add_request(testuser)
        mgr.finish_request()
        self.assertListEqual(list(mgr.list_users()), [])
        self.assertFalse(mgr.is_request_pending())

    def test_remove_user(self):
        mgr, testuser = self._get_mgr_with_one_user()
        mgr.remove(testuser)
        self.assertListEqual(list(mgr.list_users()), [])
        # check again with a separate object
        mgr, testuser = self._get_mgr_with_one_user()
        mgr.remove(UserIdentifier('foo', 'bar'))
        self.assertListEqual(list(mgr.list_users()), [])

    def test_remove_user_wrong_arg(self):
        mgr, testuser = self._get_mgr_with_one_user()
        mgr.remove('wrong')
        self.assertListEqual(list(mgr.list_users()), [testuser])

    def test_find_user(self):
        mgr, testuser = self._get_mgr_with_one_user()
        result1 = mgr.find('xyz')
        result2 = mgr.find('foo')
        self.assertIsNone(result1)
        self.assertEqual(result2, testuser)

    def test_get_expired_users(self):
        mgr, testuser1, testuser2 = self._get_mgr_with_two_users()
        testuser2.user_data = UserData()
        # set to very low timestamp to ensure expiration
        testuser2.user_data.valid_until = 123
        mgr.update(testuser2)

        # both users should be in the list, but only testuser2 should
        # be expired.
        users = mgr.list_users()
        expired_users = mgr.get_expired_users()
        self.assertIn(testuser1, users)
        self.assertIn(testuser2, users)
        self.assertListEqual(expired_users, [testuser2])

        # now update first user, should be expired as well then
        testuser1.user_data = UserData()
        testuser1.user_data.valid_until = 123
        mgr.update(testuser1)
        expired_users_updated = mgr.get_expired_users()
        self.assertIn(testuser1, expired_users_updated)
        self.assertIn(testuser2, expired_users_updated)

    def test_generate_password(self):
        mgr = UserManager()
        pw = mgr.generate_password()

        self.assertIsInstance(pw, str)
        self.assertNotEqual(pw, '')
