# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time

from unittest import TestCase
from unittest.mock import Mock, call

from radguestauth.commands.user import (AllowCommand, DenyCommand,
                                        ListUsersCommand, ManageUserCommand)
from radguestauth.users.storage import UserIdentifier, UserData


# tests shared by allow and manage. Not based on TestCase so they are not
# executed in the base class. See also:
# https://stackoverflow.com/questions/48234672/how-to-use-same-unit-test-for-different-implementations-in-python/49545467#49545467
# This explicitly is independent from a potential base class (like
# UserModifyingCommand in the current implementation)
class ModifyBaseTest(object):
    # for the management command, this is an additional "allow"
    pre_arg = []
    # for the management command, this is the user name
    post_arg = []
    # more args for invalid_args (e.g. ok 3 times bar is wrong, but
    # manage allow 3 times bar would refer to user bar)
    additional_test_args = []

    def _run_request(self, arg):
        """
        Runs the command with desired mocks etc. Has to be specified explicitly
        for the tested class.
        Has to return the UserIdentifier which was used for testing.
        """
        pass

    def test_invalid_args(self):
        usage = self.cmd.usage()
        test_args = [
            ['foo'], ['foo', 'bar'], ['for', 'test', 'h'],
            ['for', 'x', 'h'], ['3', 'foo']
        ]
        test_args += self.additional_test_args

        for arg in test_args:
            result = self.cmd.execute(self.pre_arg + arg + self.post_arg)
            self.assertEqual(result, usage,
                             'No usage output for invalid arg: %s' % arg)

        self.mock_um.update.assert_not_called()
        self.mock_um.finish_request.assert_not_called()
        self.mock_um.find.assert_not_called()

    def test_request_n(self):
        testuser = self._run_request(['3', 'times'])
        self.assertEqual(3, testuser.user_data.max_num_joins)
        self.assertEqual(testuser.user_data.join_state,
                         UserData.JOIN_STATE_ALLOWED)
        self.mock_auth.on_host_accept.assert_called_once_with(testuser)

    def test_request_time(self):
        testuser = self._run_request(['for', '1', 'h'])
        # check if inside safety margin
        self.assertGreaterEqual(testuser.user_data.valid_until,
                                time.time() + (60 * 60) - 10,)
        self.assertLessEqual(testuser.user_data.valid_until,
                             time.time() + (60 * 60) + 10)
        self.assertEqual(testuser.user_data.join_state,
                         UserData.JOIN_STATE_ALLOWED)
        self.mock_auth.on_host_accept.assert_called_once_with(testuser)

    def test_request_time_over_max(self):
        t = str(self.cmd.MAX_HOURS + 1)
        self.cmd.execute(self.pre_arg + ['for', t, 'h'] + self.post_arg)

        # Request should not have been touched, no find should have been done
        self.mock_um.get_request.assert_not_called()
        self.mock_um.update.assert_not_called()
        self.mock_um.finish_request.assert_not_called()
        self.mock_um.find.assert_not_called()
        self.mock_auth.on_host_accept.assert_not_called()

    def test_no_arg(self):
        usage = self.cmd.usage()
        result = self.cmd.execute([])

        self.assertEqual(result, usage)

        self.mock_um.update.assert_not_called()
        self.mock_um.finish_request.assert_not_called()
        self.mock_um.find.assert_not_called()
        self.mock_auth.on_host_accept.assert_not_called()


class AllowCommandTest(ModifyBaseTest, TestCase):
    additional_test_args = [
        ['3', 'foo', 'bar'], ['for', '7', 'h', 'other']
    ]

    def _run_request(self, arg):
        self.mock_um.is_request_pending.return_value = True
        testuser = UserIdentifier('user', 'device')
        self.mock_um.get_request.return_value = testuser

        self.cmd.execute(arg)

        self.mock_um.update.assert_called_once_with(testuser)
        self.mock_um.finish_request.assert_called_once()
        return testuser

    def setUp(self):
        self.mock_um = Mock()
        self.mock_auth = Mock()
        self.cmd = AllowCommand(self.mock_um, self.mock_auth)

    def test_no_request(self):
        self.mock_um.is_request_pending.return_value = False

        self.cmd.execute(['3', 'times'])

        self.mock_um.update.assert_not_called()
        self.mock_um.finish_request.assert_not_called()

    def test_invalid_request(self):
        self.mock_um.is_request_pending.return_value = True
        self.mock_um.get_request.return_value = 'foo'
        self.cmd.execute(['3', 'times'])

        self.mock_um.update.assert_not_called()
        self.mock_um.finish_request.assert_not_called()


class DenyCommandTest(TestCase):
    def setUp(self):
        self.mock_um = Mock()
        self.mock_auth = Mock()
        self.cmd = DenyCommand(self.mock_um, self.mock_auth)

    def _run_with_request(self, args):
        self.mock_um.is_request_pending.return_value = True
        testuser = UserIdentifier('user', 'device')
        self.mock_um.get_request.return_value = testuser

        self.cmd.execute(args)

        self.mock_um.update.assert_called_once_with(testuser)
        self.mock_um.finish_request.assert_called_once()
        self.assertEqual(testuser.user_data.join_state,
                         UserData.JOIN_STATE_BLOCKED)
        self.mock_auth.on_host_deny.assert_called_once_with(testuser)

    def test_no_request(self):
        self.mock_um.is_request_pending.return_value = False

        self.cmd.execute([])
        # ignore other args
        self.cmd.execute(['blah'])

        self.mock_um.update.assert_not_called()
        self.mock_um.finish_request.assert_not_called()
        self.mock_auth.on_host_deny.assert_not_called()

    def test_with_request(self):
        self._run_with_request([])

        # ignore other args
        self.mock_um.reset_mock()
        self.mock_auth.reset_mock()
        self._run_with_request(['blah'])

    def test_invalid_request(self):
        self.mock_um.is_request_pending.return_value = True
        self.mock_um.get_request.return_value = 'foo'
        self.cmd.execute([])

        self.mock_um.update.assert_not_called()
        self.mock_um.finish_request.assert_not_called()
        self.mock_auth.on_host_deny.assert_not_called()


class ListUsersCommandTest(TestCase):
    def setUp(self):
        self.mock_um = Mock()
        self.cmd = ListUsersCommand(self.mock_um)

    def _exec_list(self):
        result = self.cmd.execute([])
        # args should be ignored
        result_args = self.cmd.execute(['with', 'unnecessary', 'args'])

        self.mock_um.list_users.assert_called()
        self.assertIn('someone', result)
        self.assertIn('123', result)
        self.assertIn('someoneElse', result)
        self.assertIn('deviceId1', result)
        self.assertEqual(result, result_args)
        return result

    def test_list_output(self):
        self.mock_um.list_users.return_value = [
            UserIdentifier('someone', '123'),
            UserIdentifier('someoneElse', 'deviceId1'),
        ]

        result = self._exec_list()
        self.assertFalse('[blocked]' in result)

    def test_block_state(self):
        user1 = UserIdentifier('someone', '123')
        user1.user_data = UserData()
        user1.user_data.join_state = UserData.JOIN_STATE_ALLOWED
        user2 = UserIdentifier('someoneElse', 'deviceId1')
        user2.user_data = UserData()
        user2.user_data.join_state = UserData.JOIN_STATE_BLOCKED
        self.mock_um.list_users.return_value = [
            user1, user2
        ]

        result = self._exec_list()
        self.assertEqual(result.count('[blocked]'), 1)


class ManageUsersCommandBase(ModifyBaseTest):
    """
    This is again a base class to enable testing easily with usernames
    having spaces and usernames having no spaces.
    Subclasses only have to specify post_arg and user_name.
    """
    pre_arg = ['allow']
    additional_test_args = [
        ['for', 'x', 'h', 'blah', 'other']
    ]

    def _run_request(self, arg):
        self.cmd.execute(self.pre_arg + arg + self.post_arg)

        self.mock_um.find.assert_called_once_with(self.user_name)
        self.mock_um.update.assert_called_once_with(self.testuser)
        self.mock_um.is_request_pending.assert_not_called()
        self.mock_um.get_request.assert_not_called()
        self.mock_um.finish_request.assert_not_called()
        self.mock_um.remove.assert_not_called()
        return self.testuser

    def _assert_blocked(self):
        self.mock_um.find.assert_called_once_with(self.user_name)
        self.mock_um.update.assert_called_once_with(self.testuser)
        self.mock_um.remove.assert_not_called()
        self.assertEqual(self.testuser.user_data.join_state,
                         UserData.JOIN_STATE_BLOCKED)

    def setUp(self):
        self.mock_um = Mock()
        self.mock_auth = Mock()
        self.cmd = ManageUserCommand(self.mock_um, self.mock_auth)
        self.testuser = UserIdentifier('user', 'device', 'pw')
        self.testdata = UserData()
        self.testuser.user_data = self.testdata
        self.mock_um.find.return_value = self.testuser

    def test_show(self):
        expected = str(self.testuser)
        result = self.cmd.execute(['show'] + self.post_arg)

        self.mock_um.find.assert_called_once_with(self.user_name)
        self.assertIn(expected, result)

    def test_block(self):
        self.cmd.execute(['block'] + self.post_arg)
        self._assert_blocked()

    def test_block_no_userdata(self):
        self.testuser.user_data = None
        self.cmd.execute(['block'] + self.post_arg)

        self.assertIsNotNone(self.testuser.user_data)
        self._assert_blocked()

    def test_drop(self):
        self.cmd.execute(['drop'] + self.post_arg)

        self.mock_um.find.assert_called_once_with(self.user_name)
        self.mock_um.remove.assert_called_once_with(self.testuser)
        self.mock_auth.on_host_deny.assert_called_once_with(self.testuser)

    def test_drop_auth_handler_blocked(self):
        self.testdata.join_state = UserData.JOIN_STATE_BLOCKED
        self.cmd.execute(['drop'] + self.post_arg)

        # do not notify auth handler when user was blocked, as everything was
        # already handled before on deny or block
        self.mock_auth.on_host_deny.assert_not_called()

    def test_drop_auth_handler_allowed(self):
        self.testdata.join_state = UserData.JOIN_STATE_ALLOWED
        self.cmd.execute(['drop'] + self.post_arg)

        # ensure AuthHandler gets notified when the user was allowed
        self.mock_auth.on_host_deny.assert_called_once_with(self.testuser)

    def test_unknown(self):
        result = self.cmd.execute(['xyz'] + self.post_arg)

        self.assertEqual(result, self.cmd.usage())
        self.mock_um.find.assert_not_called()

    def test_not_found(self):
        self.mock_um.find.return_value = None

        # use a set to determine if all messages are the same
        result_set = set()
        result_set.add(self.cmd.execute(['show'] + self.post_arg))
        result_set.add(self.cmd.execute(['drop'] + self.post_arg))
        result_set.add(self.cmd.execute(['allow', '2', 'times']
                                        + self.post_arg))
        result_set.add(self.cmd.execute(['allow', 'for', '1', 'h']
                                        + self.post_arg))

        self.assertEqual(len(result_set), 1)
        self.assertEqual(self.mock_um.find.call_count, 4)
        for i, mcall in enumerate(self.mock_um.find.mock_calls):
            self.assertEqual(mcall, call(self.user_name),
                             'find call %s was invalid' % i)
        self.mock_um.remove.assert_not_called()
        self.mock_um.update.assert_not_called()


class ManageUsersCommandSimpleNameTest(ManageUsersCommandBase, TestCase):
    post_arg = ['user']
    user_name = 'user'


class ManageUsersCommandExtNameTest(ManageUsersCommandBase, TestCase):
    post_arg = ['user', 'with', 'spaces']
    user_name = 'user with spaces'
