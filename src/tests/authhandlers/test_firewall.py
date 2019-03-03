# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import radguestauth.auth as auth
from unittest.mock import patch, ANY
from radguestauth.authhandlers.firewall import FirewallAuthHandler
from radguestauth.users.storage import UserIdentifier, UserData
from .base_test import AuthBaseTest


@patch('radguestauth.authhandlers.firewall.AuthUtils')
class FirewallAuthHandlerTest(AuthBaseTest):

    def _prepare_on_host_mocks(self, mock_fmt_mac, mock_utils,
                               expected_msg='message'):
        # use patched format_mac function to ensure it is always called
        mock_fmt_mac.return_value = 'aa:bb'
        mock_utils.sudo_cmd.return_value = expected_msg

    def _assert_on_host_call(self, mock_fmt_mac, mock_utils,
                             expected_script, result=None,
                             expected_msg='message'):
        mock_fmt_mac.assert_called_once_with('aabb')
        mock_utils.sudo_cmd.assert_called_once_with(
            expected_script, additional_args=['aa:bb'], error_return=ANY
        )
        if result and expected_msg:
            self.assertIn(expected_msg, result)

    def test_user_state_util_behavior(self, mock_utils):
        handler = FirewallAuthHandler()
        self._check_user_state_util_behavior(mock_utils, handler)

    @patch('radguestauth.users.storage.UserIdentifier.format_mac')
    def test_user_state_waiting_drop(self, mock_fmt_mac, mock_utils):
        self._prepare_on_host_mocks(mock_fmt_mac, mock_utils)

        handler = FirewallAuthHandler()
        handler.handle_user_state(
            UserIdentifier('user', 'aabb'), UserData.JOIN_STATE_WAITING, ''
        )

        self._assert_on_host_call(
            mock_fmt_mac, mock_utils,
            '/etc/radguestauth/fw_user_drop.sh'
        )

    def test_post_auth_waiting_add_timeout(self, mock_utils):
        handler = FirewallAuthHandler()
        handler.handle_user_state(
            UserIdentifier('user', 'aabb'), UserData.JOIN_STATE_WAITING,
            'session'
        )

        result = handler.on_post_auth(
            UserIdentifier('user', 'aabb'), 'session'
        )

        self.assertIsInstance(result, dict)
        self.assertIsNotNone(result.get('reply:Session-Timeout'))

    def test_post_auth_allowed_no_timeout(self, mock_utils):
        # no timeout should be set for allowed users
        handler = FirewallAuthHandler()
        handler.handle_user_state(
            UserIdentifier('user', 'aabb'), UserData.JOIN_STATE_ALLOWED,
            'session'
        )

        result = handler.on_post_auth(
            UserIdentifier('user', 'aabb'), 'session'
        )

        self.assertIsNone(result)

    def test_firewall_resets(self, mock_utils):
        expected_script = '/etc/radguestauth/fw_reset.sh'

        handler = FirewallAuthHandler()

        handler.start({})
        mock_utils.sudo_cmd.assert_called_once_with(
            expected_script, error_return=ANY, additional_args=None
        )
        mock_utils.reset_mock()

        handler.shutdown()
        mock_utils.sudo_cmd.assert_called_once_with(
            expected_script, error_return=ANY, additional_args=None
        )

    @patch('radguestauth.users.storage.UserIdentifier.format_mac')
    def test_add_on_accept(self, mock_fmt_mac, mock_utils):
        self._prepare_on_host_mocks(mock_fmt_mac, mock_utils)

        handler = FirewallAuthHandler()
        result = handler.on_host_accept(UserIdentifier('user', 'aabb'))

        self._assert_on_host_call(
            mock_fmt_mac, mock_utils,
            '/etc/radguestauth/fw_user_add.sh', result
        )

    @patch('radguestauth.users.storage.UserIdentifier.format_mac')
    def test_drop_on_deny(self, mock_fmt_mac, mock_utils):
        self._prepare_on_host_mocks(mock_fmt_mac, mock_utils)

        handler = FirewallAuthHandler()
        result = handler.on_host_deny(UserIdentifier('user', 'aabb'))

        self._assert_on_host_call(
            mock_fmt_mac, mock_utils,
            '/etc/radguestauth/fw_user_drop.sh', result
        )

    @patch('radguestauth.users.storage.UserIdentifier.format_mac')
    def test_disassociate_blocked_on_deny(self, mock_fmt_mac, mock_utils):
        # test with and without return value of the sudo_cmd call
        for message in ['message', None]:
            mock_fmt_mac.reset_mock()
            mock_utils.reset_mock()
            self._prepare_on_host_mocks(mock_fmt_mac, mock_utils,
                                        expected_msg=message)
            mock_utils.disassociate_user.return_value = 'OK'
            testuser = UserIdentifier('user', 'aabb')
            testuser.user_data = UserData()
            testuser.user_data.join_state = UserData.JOIN_STATE_BLOCKED

            handler = FirewallAuthHandler()
            result = handler.on_host_deny(testuser)

            # ensure the script also gets called when UserData is given
            self._assert_on_host_call(
                mock_fmt_mac, mock_utils,
                '/etc/radguestauth/fw_user_drop.sh', result,
                expected_msg=message
            )
            # blocked user needs to be disassociated as well
            mock_utils.disassociate_user.assert_called_once_with('aabb')
            self.assertIn('OK', result)
