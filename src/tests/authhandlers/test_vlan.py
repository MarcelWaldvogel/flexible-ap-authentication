# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import radguestauth.auth as auth
from unittest.mock import patch, ANY
from radguestauth.authhandlers.vlan import VlanAuthHandler
from radguestauth.users.storage import UserIdentifier, UserData
from .base_test import AuthBaseTest


class VlanAuthHandlerTest(AuthBaseTest):
    VLAN_PRIVATE = 1
    VLAN_CONNECTED = 2

    def _assert_vlan(self, vlan_id, result):
        self.assertDictContainsSubset(
            {'reply:Tunnel-Type': 'VLAN'}, result
        )
        self.assertDictContainsSubset(
            {'reply:Tunnel-Medium-Type': 'IEEE-802'}, result
        )
        self.assertDictContainsSubset(
            {'reply:Tunnel-Private-Group-ID': str(vlan_id)}, result
        )

    @patch('radguestauth.authhandlers.vlan.AuthUtils')
    def test_user_state_util_behavior(self, mock_utils):
        handler = VlanAuthHandler()
        self._check_user_state_util_behavior(mock_utils, handler)

    def test_post_auth_without_handle_state(self):
        # without handle_user_state call, the VLAN assignment should always
        # be the network without connectivity to the outside world
        handler = VlanAuthHandler()
        result = handler.on_post_auth(
            UserIdentifier('user', 'aa-bb'), 'session1234'
        )
        self._assert_vlan(self.VLAN_PRIVATE, result)

    def test_post_auth_session_mismatch(self):
        # when the session doesn't match, no connectivity should be granted
        testuser = UserIdentifier('user', 'aa-bb')
        handler = VlanAuthHandler()

        handler.handle_user_state(
            testuser, UserData.JOIN_STATE_ALLOWED, 'othersession'
        )
        result = handler.on_post_auth(testuser, 'session1234')
        self._assert_vlan(self.VLAN_PRIVATE, result)

    def test_post_auth_user_mismatch(self):
        # when the user doesn't match, no connectivity should be granted
        testuser = UserIdentifier('user', 'aa-bb')
        testsession = 'session1234'
        handler = VlanAuthHandler()

        handler.handle_user_state(
            testuser, UserData.JOIN_STATE_ALLOWED, testsession
        )
        result = handler.on_post_auth(
             UserIdentifier('user1', 'aa-bb'), testsession
        )
        self._assert_vlan(self.VLAN_PRIVATE, result)

        # calls to handle_user_state and on_post_auth usually occur
        # together, so assume this is the case here
        handler.handle_user_state(
            testuser, UserData.JOIN_STATE_ALLOWED, testsession
        )
        result = handler.on_post_auth(
             UserIdentifier('user', 'aa-b1'), testsession
        )
        self._assert_vlan(self.VLAN_PRIVATE, result)

    def test_post_auth_state_not_allowed(self):
        # when handle_user_state was called without an allowed state,
        # also assign private VLAN
        testuser = UserIdentifier('user', 'aa-bb')
        testsession = 'session1234'
        handler = VlanAuthHandler()

        handler.handle_user_state(
            testuser, UserData.JOIN_STATE_WAITING, testsession
        )
        result = handler.on_post_auth(testuser, testsession)
        self._assert_vlan(self.VLAN_PRIVATE, result)

        handler.handle_user_state(
            testuser, UserData.JOIN_STATE_BLOCKED, testsession
        )
        result = handler.on_post_auth(testuser, testsession)
        self._assert_vlan(self.VLAN_PRIVATE, result)

    def test_post_auth_allowed_user(self):
        # assign allowed user to the VLAN with connectivity
        testuser = UserIdentifier('user', 'aa-bb')
        testsession = 'session1234'
        handler = VlanAuthHandler()

        handler.handle_user_state(
            testuser, UserData.JOIN_STATE_ALLOWED, testsession
        )
        result = handler.on_post_auth(testuser, testsession)
        self._assert_vlan(self.VLAN_CONNECTED, result)

    def _check_disassociate_call_with(self, mock_utils, method_executor):
        """
        Checks if disassociate_user was called with the correct address and
        if its return value is used.

        :param mock_utils: mock for AuthUtils
        :param method_executor: A function with two arguments: the handler
            instance and an UserIdentifier. It is intended to be used with
            the on_host events (i.e. call handler.on_...).
            The function has to pass the return value of the called event
            handler.
        """
        mock_utils.disassociate_user.return_value = 'teststr'

        handler = VlanAuthHandler()
        result = method_executor(handler, UserIdentifier('user', 'aa-bb'))

        mock_utils.disassociate_user.assert_called_once_with('aa-bb')
        self.assertIn('teststr', result)

    @patch('radguestauth.authhandlers.vlan.AuthUtils')
    def test_reconnect_on_accept(self, mock_utils):
        self._check_disassociate_call_with(
            mock_utils,
            lambda handler, user: handler.on_host_accept(user)
        )

    @patch('radguestauth.authhandlers.vlan.AuthUtils')
    def test_reconnect_on_deny(self, mock_utils):
        self._check_disassociate_call_with(
            mock_utils,
            lambda handler, user: handler.on_host_deny(user)
        )
