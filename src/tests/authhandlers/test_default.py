# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import radguestauth.auth as auth
from unittest import TestCase
from radguestauth.authhandlers.default import DefaultAuthHandler
from radguestauth.users.storage import UserIdentifier, UserData


class DefaultAuthHandlerTest(TestCase):
    def test_reject_waiting(self):
        user = UserIdentifier('user', '')

        handler = DefaultAuthHandler()

        expected_result = (auth.REJECT, None)
        result = handler.handle_user_state(user,
                                           UserData.JOIN_STATE_WAITING, '')

        self.assertEqual(expected_result, result)

    def test_reject_blocked(self):
        user = UserIdentifier('user', '')

        handler = DefaultAuthHandler()

        expected_result = (auth.REJECT, None)
        result = handler.handle_user_state(user,
                                           UserData.JOIN_STATE_BLOCKED, '')

        self.assertEqual(expected_result, result)

    def test_user_allowed(self):
        user = UserIdentifier('user', '')
        user.password = 'a password'

        handler = DefaultAuthHandler()

        expected_result = (auth.ALLOW, {
            'control:Cleartext-Password': 'a password'
        })
        result = handler.handle_user_state(user,
                                           UserData.JOIN_STATE_ALLOWED, '')

        self.assertEqual(expected_result, result)
