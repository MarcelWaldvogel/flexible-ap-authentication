# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import radguestauth.auth as auth
from unittest import TestCase
from unittest.mock import patch, ANY
from subprocess import TimeoutExpired, CalledProcessError
from radguestauth.authhandlers.util import AuthUtils
from radguestauth.users.storage import UserIdentifier, UserData


class AuthUtilsTest(TestCase):

    def test_reject_only_when_blocked(self):
        user = UserIdentifier('user', '')
        user.password = 'pw'

        expected_reject = (auth.REJECT, None)
        expected_accept = (auth.ALLOW, {
            'control:Cleartext-Password': 'pw'
        })

        result_block = AuthUtils.reject_only_when_blocked(
            user, UserData.JOIN_STATE_BLOCKED
        )
        result_waiting = AuthUtils.reject_only_when_blocked(
            user, UserData.JOIN_STATE_WAITING
        )
        result_ok = AuthUtils.reject_only_when_blocked(
            user, UserData.JOIN_STATE_ALLOWED
        )

        self.assertEqual(expected_reject, result_block)
        self.assertEqual(expected_accept, result_waiting)
        self.assertEqual(expected_accept, result_ok)

    @patch('subprocess.run')
    def test_sudo_cmd_call(self, mock_subproc_run):
        AuthUtils.sudo_cmd('test')
        mock_subproc_run.assert_called_once_with(
            ['sudo', 'test'], check=True, timeout=ANY
        )

        mock_subproc_run.reset_mock()
        AuthUtils.sudo_cmd('test', ['my', 'args'])
        mock_subproc_run.assert_called_once_with(
            ['sudo', 'test', 'my', 'args'], check=True, timeout=ANY
        )

    @patch('subprocess.run')
    def test_sudo_cmd_return_values(self, mock_subproc_run):
        # use inline def, as this helper is only used here
        def _run_assert(expected_msg):
            result = AuthUtils.sudo_cmd('test', success_return='mymessage',
                                        error_return='myerror')
            mock_subproc_run.assert_called_once()
            self.assertEqual(result, expected_msg)

        _run_assert('mymessage')

        mock_subproc_run.reset_mock()
        mock_subproc_run.side_effect = TimeoutExpired('x', 5)

        _run_assert('myerror')

        mock_subproc_run.reset_mock(side_effect=True)
        mock_subproc_run.side_effect = CalledProcessError(1, 'cmd')

        _run_assert('myerror')

    def _run_disassoc(self, mock_subproc_run):
        result = AuthUtils.disassociate_user('AA-BB-CC')
        mock_subproc_run.assert_called_once_with(
            ['sudo', 'hostapd_cli', 'disassociate', 'aa:bb:cc'], check=True,
            timeout=ANY
        )
        self.assertIsInstance(result, str)

    @patch('subprocess.run')
    def test_disassociate_user(self, mock_subproc_run):
        # sunny day scenario without errors
        self._run_disassoc(mock_subproc_run)

    @patch('subprocess.run')
    def test_disassociate_user_error_handling(self, mock_subproc_run):
        # the command should still return a string when an exception is thrown
        mock_subproc_run.side_effect = TimeoutExpired('x', 5)
        self._run_disassoc(mock_subproc_run)

        mock_subproc_run.reset_mock(side_effect=True)
        mock_subproc_run.side_effect = CalledProcessError(1, 'cmd')
        self._run_disassoc(mock_subproc_run)
