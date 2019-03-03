# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import radguestauth.auth as auth
from radguestauth.users.storage import UserIdentifier, UserData
from unittest import TestCase


class AuthBaseTest(TestCase):
    """
    Base class with common checks appropriate for multiple AuthHandlers
    """

    def _check_user_state_util_behavior(self, mock_utils, handler):
        """
        Ensures that the reject_only_when_blocked behavior is used to
        determine the user state.

        :param mock_utils: Mock of the AuthUtils class
        :param handler: the AuthHandler implementation
        :returns: The result of handler.handler_user_state
        """
        user = UserIdentifier('user', '')
        expected_result = (auth.REJECT, None)
        mock_utils.reject_only_when_blocked.return_value = expected_result

        result = handler.handle_user_state(user,
                                           UserData.JOIN_STATE_BLOCKED, '')

        mock_utils.reject_only_when_blocked.assert_called_once_with(
            user, UserData.JOIN_STATE_BLOCKED
        )

        self.assertEqual(result, expected_result)
