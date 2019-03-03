# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time
import radguestauth.auth as auth
from unittest import TestCase
from unittest.mock import patch, Mock, ANY, call
from radguestauth.core import GuestAuthCore
from radguestauth.authhandlers.default import DefaultAuthHandler
from radguestauth.users.storage import UserIdentifier, UserData


# use a separate test class for helpers, as those are independent from
# Mocks.
class GuestAuthCoreHelpersTest(TestCase):
    @staticmethod
    def _message_dict(eap_message):
        return {'EAP-Message': eap_message}

    def test_get_eap_type_short(self):
        input = GuestAuthCoreHelpersTest._message_dict('0x00')
        result = GuestAuthCore.get_eap_type(input)
        self.assertEqual(result, -1)

    def test_get_eap_type_no_attr(self):
        input = {'Other-Message': '1234'}
        result = GuestAuthCore.get_eap_type(input)
        self.assertEqual(result, -1)

    def test_get_eap_type_invalid(self):
        # skip non-hex values for type
        input = GuestAuthCoreHelpersTest._message_dict(
            '0x020100160xy'
        )
        result = GuestAuthCore.get_eap_type(input)
        self.assertEqual(result, -1)

    def test_get_eap_type(self):
        # message has type 4
        input = GuestAuthCoreHelpersTest._message_dict(
            '0x0201001604100a5cedafe5b632'
        )
        result = GuestAuthCore.get_eap_type(input)
        self.assertEqual(result, 4)

    def test_skip_eap_message_no_attr(self):
        input = {'Other-Message': '1234'}
        result = GuestAuthCore.skip_eap_message(input)
        self.assertFalse(result)

    def test_skip_eap_message_nak(self):
        # Some imaginary message with type 3 (NAK)
        input = GuestAuthCoreHelpersTest._message_dict(
            '0x020100160301020301abcd'
        )
        result = GuestAuthCore.skip_eap_message(input)
        self.assertTrue(result)

    def test_skip_eap_message_peap(self):
        # EAP-PEAP (0x19) message should not be skipped
        input = GuestAuthCoreHelpersTest._message_dict(
            '0x0201001619100a5cedafe5b63240b6244fc5a4bf9736'
        )
        result = GuestAuthCore.skip_eap_message(input)
        self.assertFalse(result)


# from imports lead to a change of the namespace
@patch('radguestauth.core.ImplLoader')
@patch('radguestauth.core.ChatController')
@patch('radguestauth.core.UserManager')
class GuestAuthCoreTest(TestCase):
    def _get_auth_handler_mock(self, mock_loader):
        """
        Lets the ImplLoader return a Mock to abstract AuthHandler.
        """
        auth_mock_obj = Mock(auth.AuthHandler)
        auth_mock = Mock()
        auth_mock.return_value = auth_mock_obj
        mock_loader_obj = Mock()
        mock_loader_obj.load.return_value = auth_mock
        mock_loader.return_value = mock_loader_obj

        return auth_mock_obj

    def _assert_called_once_with_user_id(self, callable_mock, name, device):
        """
        Tests if the mock method was called once with an UserIdentifier having
        the given name and device attributes.
        """
        callable_mock.assert_called_once()
        # args is a tuple of non-keyword and keyword arguments. The callable
        # is expected to take exactly one non-keyword argument.
        argument = callable_mock.call_args[0][0]
        self.assertIsInstance(argument, UserIdentifier)
        self.assertEqual(argument.name, name)
        self.assertEqual(argument.device_id, device)

    def _init_and_start(self):
        """
        Creates an instance and ensures startup() gets called with a default
        config.
        """
        gacore = GuestAuthCore()
        gacore.startup({'chat': 'udp'})
        return gacore

    def test_helpers_initialized(self, mock_usermgr, mock_chat, mock_loader):
        # mock object creation
        mock_usermgr_obj = Mock()
        mock_usermgr.return_value = mock_usermgr_obj
        mock_auth = self._get_auth_handler_mock(mock_loader)

        self._init_and_start()

        mock_loader.assert_called_once_with(auth.AuthHandler,
                                            DefaultAuthHandler)

        # check if both util classes were initialized and that the chat
        # gets the correct UserManager and AuthHandler references.
        mock_usermgr.assert_called()
        mock_chat.assert_called_once_with(mock_usermgr_obj, mock_auth)

    def test_chat_started_correctly(self, mock_usermgr, mock_chat, mock_loader):
        # prepare test data
        mock_chat_obj = Mock()
        mock_chat.return_value = mock_chat_obj
        test_dict = {'chat': 'test', 'other_config': 'foobar'}
        gacore = GuestAuthCore()

        gacore.startup(test_dict)

        # check if chat was started with expected config
        mock_chat_obj.start.assert_called_once_with(test_dict)

    def test_skip_outer_message(self, mock_usermgr, mock_chat, mock_loader):
        # prepare test data
        mock_usermgr_obj = Mock()
        mock_chat_obj = Mock()
        mock_usermgr.return_value = mock_usermgr_obj
        mock_chat.return_value = mock_chat_obj
        gacore = self._init_and_start()

        expected_result = (auth.NO_OP, None)
        # has type 19, which would be OK as inner message
        result = gacore.authorize({
            'User-Name': 'user',
            'Calling-Station-Id': 'aabb',
            'EAP-Message': '0x0200000c19736f6d656f6e65'
        })

        mock_usermgr_obj.may_join.assert_not_called()
        mock_usermgr_obj.is_request_pending.assert_not_called()
        mock_usermgr_obj.add_request.assert_not_called()
        mock_chat_obj.notify_join.assert_not_called()
        self.assertEqual(expected_result, result)

    def test_skip_inner_message(self, mock_usermgr, mock_chat, mock_loader):
        # prepare test data
        mock_usermgr_obj = Mock()
        mock_chat_obj = Mock()
        mock_usermgr.return_value = mock_usermgr_obj
        mock_chat.return_value = mock_chat_obj
        gacore = self._init_and_start()

        expected_result = (auth.NO_OP, None)
        # skip type 01 (identity message), as request containing the method
        # (like PEAP) should be processed
        result = gacore.authorize({
            'User-Name': 'user',
            'Calling-Station-Id': 'aabb',
            'EAP-Message': '0x0206000c01736f6d656f6e65',
            'FreeRADIUS-Proxied-To': '127.0.0.1'
        })

        mock_usermgr_obj.may_join.assert_not_called()
        mock_usermgr_obj.is_request_pending.assert_not_called()
        mock_usermgr_obj.add_request.assert_not_called()
        mock_chat_obj.notify_join.assert_not_called()
        self.assertEqual(expected_result, result)

    def test_eap_pwd_remember_attrs(self, mock_usermgr, mock_chat, mock_loader):
        # prepare test data
        mock_usermgr_obj = Mock()
        mock_chat_obj = Mock()
        mock_usermgr.return_value = mock_usermgr_obj
        mock_chat.return_value = mock_chat_obj
        mock_auth = self._get_auth_handler_mock(mock_loader)
        gacore = self._init_and_start()

        # outer message should return NO_OP, but remember the attributes
        expected_result_outer = (auth.NO_OP, None)
        # 0x34 is EAP-PWD.
        result_outer = gacore.authorize({
            'User-Name': 'user',
            'Calling-Station-Id': 'aabb',
            'EAP-Message': '0x0200000c34736f6d656f6e65'
        })

        mock_usermgr_obj.may_join.assert_not_called()
        mock_usermgr_obj.is_request_pending.assert_not_called()
        mock_usermgr_obj.add_request.assert_not_called()
        mock_chat_obj.notify_join.assert_not_called()
        mock_auth.handle_user_state.assert_not_called()
        self.assertEqual(expected_result_outer, result_outer)

        mock_usermgr_obj.may_join.return_value = UserData.JOIN_STATE_BLOCKED

        expected_result_inner = (auth.REJECT, None)
        mock_auth.handle_user_state.return_value = expected_result_inner
        # only call with username like the FreeRADIUS inner tunnel does
        result_inner = gacore.authorize({
            'User-Name': 'user'
        })
        # even though not given this time, the calls should contain the
        # correct device
        self._assert_called_once_with_user_id(
            mock_usermgr_obj.may_join, 'user', 'aabb'
        )
        self._assert_called_once_with_user_id(
            mock_auth.handle_user_state, 'user', 'aabb'
        )
        self.assertEqual(expected_result_inner, result_inner)

    def test_reject_new_on_pending_request(self, mock_usermgr, mock_chat, mock_loader):
        # When a request is ongoing, no new users should be accepted.
        # prepare test data
        mock_usermgr_obj = Mock()
        mock_usermgr_obj.may_join.return_value = UserData.JOIN_STATE_NEW
        mock_usermgr_obj.is_request_pending.return_value = True
        mock_usermgr.return_value = mock_usermgr_obj
        gacore = self._init_and_start()

        expected_result = (auth.REJECT, None)
        result = gacore.authorize({
            'User-Name': 'user',
            'Calling-Station-Id': 'aabb'
        })

        # no request should have been added and the user should be rejected.
        self._assert_called_once_with_user_id(
            mock_usermgr_obj.may_join, 'user', 'aabb'
        )
        mock_usermgr_obj.is_request_pending.assert_called_once()
        mock_usermgr_obj.add_request.assert_not_called()
        self.assertEqual(expected_result, result)

    def test_allow_known_on_pending_request(self, mock_usermgr, mock_chat, mock_loader):
        # prepare test data
        mock_usermgr_obj = Mock()
        # state WAITING means there is a request for this user
        mock_usermgr_obj.may_join.return_value = UserData.JOIN_STATE_WAITING
        mock_usermgr_obj.get_request.return_value = UserIdentifier('user', 'aabb')
        mock_usermgr.return_value = mock_usermgr_obj
        mock_auth = self._get_auth_handler_mock(mock_loader)
        gacore = self._init_and_start()

        expected_result = (auth.ALLOW, {'control:Cleartext-Password': 'secure'})
        mock_auth.handle_user_state.return_value = expected_result
        result = gacore.authorize({
            'User-Name': 'user',
            'Calling-Station-Id': 'aabb'
        })

        # no request should have been added and the user should be rejected.
        self._assert_called_once_with_user_id(
            mock_usermgr_obj.may_join, 'user', 'aabb'
        )
        mock_usermgr_obj.get_request.assert_called_once()
        mock_usermgr_obj.add_request.assert_not_called()
        self._assert_called_once_with_user_id(
            mock_auth.handle_user_state, 'user', 'aabb'
        )
        # User identifier handled above, session ID not given
        mock_auth.handle_user_state.assert_called_once_with(
            ANY, UserData.JOIN_STATE_WAITING, ANY
        )
        self.assertEqual(expected_result, result)

    def test_reject_blocked_user(self, mock_usermgr, mock_chat, mock_loader):
        # prepare test data
        mock_usermgr_obj = Mock()
        mock_chat_obj = Mock()
        mock_usermgr_obj.may_join.return_value = UserData.JOIN_STATE_BLOCKED
        mock_usermgr.return_value = mock_usermgr_obj
        mock_chat.return_value = mock_chat_obj
        mock_auth = self._get_auth_handler_mock(mock_loader)
        gacore = self._init_and_start()

        expected_result = (auth.REJECT, None)
        mock_auth.handle_user_state.return_value = expected_result
        result = gacore.authorize({
            'User-Name': 'user',
            'Calling-Station-Id': 'aabb'
        })

        # user should be rejected, and no request or notification should have
        # been made.
        self._assert_called_once_with_user_id(
            mock_usermgr_obj.may_join, 'user', 'aabb'
        )
        mock_usermgr_obj.is_request_pending.assert_not_called()
        mock_usermgr_obj.add_request.assert_not_called()
        mock_chat_obj.notify_join.assert_not_called()
        self.assertEqual(expected_result, result)

    def test_add_request_non_pending(self, mock_usermgr, mock_chat, mock_loader):
        # prepare test data
        mock_usermgr_obj = Mock()
        mock_chat_obj = Mock()
        mock_usermgr_obj.may_join.return_value = UserData.JOIN_STATE_NEW
        mock_usermgr_obj.is_request_pending.return_value = False
        mock_usermgr_obj.add_request.return_value = True
        # after add_request, the request can be obtained via get_request
        mock_usermgr_obj.get_request.return_value = UserIdentifier('user', 'aabb')
        mock_usermgr.return_value = mock_usermgr_obj
        mock_chat.return_value = mock_chat_obj
        mock_auth = self._get_auth_handler_mock(mock_loader)
        gacore = self._init_and_start()

        expected_result = (auth.REJECT, None)
        mock_auth.handle_user_state.return_value = expected_result
        result = gacore.authorize({
            'User-Name': 'user',
            'Calling-Station-Id': 'aabb'
        })

        # the user should be rejected, but a request should have been added
        self._assert_called_once_with_user_id(
            mock_usermgr_obj.may_join, 'user', 'aabb'
        )
        mock_usermgr_obj.is_request_pending.assert_called_once()
        self._assert_called_once_with_user_id(
            mock_usermgr_obj.add_request, 'user', 'aabb'
        )
        # ensure that get_request wasn't called before add_request
        mock_usermgr_obj.assert_has_calls([call.add_request(ANY),
                                           call.get_request()])
        mock_usermgr_obj.get_request.assert_called_once()
        self._assert_called_once_with_user_id(
            mock_chat_obj.notify_join, 'user', 'aabb'
        )
        self._assert_called_once_with_user_id(
            mock_auth.handle_user_state, 'user', 'aabb'
        )
        # User identifier handled above, session ID not given
        # The state should have been changed to WAITING after adding the
        # request
        mock_auth.handle_user_state.assert_called_once_with(
            ANY, UserData.JOIN_STATE_WAITING, ANY
        )
        self.assertEqual(expected_result, result)

    def test_add_request_non_pending_error(self, mock_usermgr, mock_chat, mock_loader):
        # block if add_request failed
        # prepare test data
        mock_usermgr_obj = Mock()
        mock_usermgr_obj.may_join.return_value = UserData.JOIN_STATE_NEW
        mock_usermgr_obj.is_request_pending.return_value = False
        mock_usermgr_obj.add_request.return_value = False
        mock_usermgr.return_value = mock_usermgr_obj
        gacore = self._init_and_start()

        expected_result = (auth.REJECT, None)
        result = gacore.authorize({
            'User-Name': 'user',
            'Calling-Station-Id': 'aabb'
        })

        # no request should have been added and the user should be rejected.
        self._assert_called_once_with_user_id(
            mock_usermgr_obj.may_join, 'user', 'aabb'
        )
        mock_usermgr_obj.is_request_pending.assert_called_once()
        self._assert_called_once_with_user_id(
            mock_usermgr_obj.add_request, 'user', 'aabb'
        )
        self.assertEqual(expected_result, result)

    def test_reject_without_username(self, mock_usermgr, mock_chat, mock_loader):
        # prepare test data
        mock_usermgr_obj = Mock()
        mock_usermgr.return_value = mock_usermgr_obj
        gacore = self._init_and_start()

        expected_result = (auth.REJECT, None)
        # call without any attributes
        result1 = gacore.authorize({})

        mock_usermgr_obj.may_join.assert_not_called()
        self.assertEqual(expected_result, result1)

        # a call with only a device ID should return the same
        result2 = gacore.authorize({'Calling-Station-Id': 'aabb'})

        mock_usermgr_obj.may_join.assert_not_called()
        self.assertEqual(expected_result, result2)

    def test_reject_without_device(self, mock_usermgr, mock_chat, mock_loader):
        # prepare test data
        # prepare test data
        mock_usermgr_obj = Mock()
        mock_usermgr.return_value = mock_usermgr_obj
        gacore = self._init_and_start()
        expected_result = (auth.REJECT, None)

        result = gacore.authorize({'User-Name': 'user'})

        mock_usermgr_obj.may_join.assert_not_called()
        self.assertEqual(expected_result, result)

    def test_allow_on_may_join(self, mock_usermgr, mock_chat, mock_loader):
        # prepare test data
        mock_usermgr_obj = Mock()
        test_user = UserIdentifier('user', 'aabb')
        test_user.password = 'secure'
        mock_usermgr_obj.find.return_value = test_user
        mock_usermgr_obj.may_join.return_value = UserData.JOIN_STATE_ALLOWED
        mock_usermgr.return_value = mock_usermgr_obj
        mock_auth = self._get_auth_handler_mock(mock_loader)
        gacore = self._init_and_start()

        expected_result = (auth.ALLOW, {'control:Cleartext-Password': 'secure'})
        mock_auth.handle_user_state.return_value = expected_result
        result = gacore.authorize({
            'User-Name': 'user',
            'Calling-Station-Id': 'aabb'
        })

        self._assert_called_once_with_user_id(
            mock_usermgr_obj.may_join, 'user', 'aabb'
        )
        self._assert_called_once_with_user_id(
            mock_auth.handle_user_state, 'user', 'aabb'
        )
        # User identifier handled above, session ID not given
        mock_auth.handle_user_state.assert_called_once_with(
            ANY, UserData.JOIN_STATE_ALLOWED, ANY
        )
        mock_usermgr_obj.find.assert_called_once_with('user')
        self.assertEqual(expected_result, result)

    def test_post_auth_too_few_args(self, mock_usermgr, mock_chat, mock_loader):
        mock_auth = self._get_auth_handler_mock(mock_loader)
        gacore = self._init_and_start()

        gacore.post_auth({})
        gacore.post_auth({'User-Name': 'user'})
        gacore.post_auth({'Calling-Station-Id': 'aabb'})

        mock_auth.on_post_auth.assert_not_called()

    def test_post_auth(self, mock_usermgr, mock_chat, mock_loader):
        mock_auth = self._get_auth_handler_mock(mock_loader)
        expected_result = {'control:Test': 'val'}
        mock_auth.on_post_auth.return_value = expected_result.copy()
        gacore = self._init_and_start()

        result = gacore.post_auth({
            'User-Name': 'user',
            'Calling-Station-Id': 'aabb'
        })

        mock_auth.on_post_auth.assert_called_once_with(
            UserIdentifier('user', 'aabb'), ANY
        )
        self.assertEqual(expected_result, result)
        self.assertIsNone(result.get('reply:Session-Timeout'))

    def test_post_auth_session(self, mock_usermgr, mock_chat, mock_loader):
        mock_auth = self._get_auth_handler_mock(mock_loader)
        gacore = self._init_and_start()

        gacore.post_auth({
            'User-Name': 'user',
            'Calling-Station-Id': 'aabb',
            'Acct-Session-Id': '12345'
        })

        mock_auth.on_post_auth.assert_called_once_with(
            UserIdentifier('user', 'aabb'), '12345'
        )

    def _prepare_timeout_user(self, mock_usermgr):
        testuser = UserIdentifier('user', 'aabb')
        testuser.user_data = UserData()
        test_validity = 600
        testuser.user_data.valid_until = time.time() + test_validity
        mock_usermgr_obj = Mock()
        mock_usermgr_obj.find.return_value = testuser
        mock_usermgr.return_value = mock_usermgr_obj

        return mock_usermgr_obj, test_validity

    def _assert_timeout_attr(self, result, test_validity):
        timeout = result.get('reply:Session-Timeout')
        self.assertIsNotNone(timeout)
        # timeout has to be at least the specified validity, and shouldn't be
        # more than 5 minutes higher.
        self.assertTrue(timeout >= test_validity)
        self.assertTrue(timeout < test_validity + 300)

    def test_post_auth_timeout(self, mock_usermgr, mock_chat, mock_loader):
        # When an user has valid_until set, a timeout attribute should be
        # added.
        mock_usermgr_obj, test_validity = self._prepare_timeout_user(
            mock_usermgr
        )

        mock_auth = self._get_auth_handler_mock(mock_loader)
        expected_result = {'control:Test': 'val'}
        mock_auth.on_post_auth.return_value = expected_result.copy()

        gacore = self._init_and_start()

        result = gacore.post_auth({
            'User-Name': 'user',
            'Calling-Station-Id': 'aabb'
        })

        mock_auth.on_post_auth.assert_called_once_with(
            UserIdentifier('user', 'aabb'), ANY
        )
        mock_usermgr_obj.find.assert_called_once_with('user')
        self.assertDictContainsSubset(expected_result, result)
        self._assert_timeout_attr(result, test_validity)

    def test_post_auth_timeout_handler_none(self, mock_usermgr, mock_chat, mock_loader):
        # The attribute should also be added if the AuthHandler returns None.
        mock_usermgr_obj, test_validity = self._prepare_timeout_user(
            mock_usermgr
        )

        mock_auth = self._get_auth_handler_mock(mock_loader)
        mock_auth.on_post_auth.return_value = None

        gacore = self._init_and_start()

        result = gacore.post_auth({
            'User-Name': 'user',
            'Calling-Station-Id': 'aabb'
        })

        mock_auth.on_post_auth.assert_called_once_with(
            UserIdentifier('user', 'aabb'), ANY
        )
        mock_usermgr_obj.find.assert_called_once_with('user')
        self.assertIsInstance(result, dict)
        self._assert_timeout_attr(result, test_validity)

    def test_post_auth_timeout_no_valid_until(self, mock_usermgr, mock_chat, mock_loader):
        testuser = UserIdentifier('user', 'aabb')
        testuser.user_data = UserData()
        testuser.user_data.valid_until = None
        testuser.user_data.max_num_joins = 10
        mock_usermgr_obj = Mock()
        mock_usermgr_obj.find.return_value = testuser
        mock_usermgr.return_value = mock_usermgr_obj

        mock_auth = self._get_auth_handler_mock(mock_loader)
        expected_result = {'control:Test': 'val'}
        mock_auth.on_post_auth.return_value = expected_result.copy()
        gacore = self._init_and_start()

        result = gacore.post_auth({
            'User-Name': 'user',
            'Calling-Station-Id': 'aabb'
        })

        mock_auth.on_post_auth.assert_called_once_with(
            UserIdentifier('user', 'aabb'), ANY
        )
        mock_usermgr_obj.find.assert_called_once_with('user')
        # no timeout should be added without valid_until.
        self.assertEqual(expected_result, result)
        self.assertIsNone(result.get('reply:Session-Timeout'))

    def test_drop_expired_users(self, mock_usermgr, mock_chat, mock_loader):
        testuser1 = UserIdentifier('user', 'aabb')
        testuser2 = UserIdentifier('user2', 'aabb2')
        testuser3 = UserIdentifier('user3', 'aabb3')
        mock_usermgr_obj = Mock()
        mock_usermgr_obj.get_expired_users.return_value = [
            testuser1, testuser2
        ]
        mock_usermgr_obj.is_request_pending.return_value = True
        mock_usermgr_obj.get_request.return_value = testuser3
        mock_usermgr.return_value = mock_usermgr_obj
        mock_auth = self._get_auth_handler_mock(mock_loader)
        gacore = self._init_and_start()

        gacore.drop_expired_users()

        mock_usermgr_obj.remove.assert_has_calls(
            [call(testuser1), call(testuser2)],
            any_order=True
        )
        mock_usermgr_obj.finish_request.assert_called_once()

        mock_auth.on_host_deny.assert_has_calls(
            [call(testuser1), call(testuser2), call(testuser3)],
            any_order=True
        )

        # no more calls should have been made
        self.assertEqual(mock_usermgr_obj.remove.call_count, 2)
        self.assertEqual(mock_auth.on_host_deny.call_count, 3)

    def test_chat_stopped_correctly(self, mock_usermgr, mock_chat, mock_loader):
        mock_chat_obj = Mock()
        mock_chat.return_value = mock_chat_obj
        gacore = self._init_and_start()

        gacore.shutdown()

        mock_chat_obj.stop.assert_called_once()

    def test_auth_handler_shutdown(self, mock_usermgr, mock_chat, mock_loader):
        mock_loader = self._get_auth_handler_mock(mock_loader)
        gacore = self._init_and_start()

        gacore.shutdown()

        mock_loader.shutdown.assert_called_once()
