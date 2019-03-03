# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import TestCase
from unittest.mock import Mock
import radguestauth.commands.password
import radguestauth.commands.user
import radguestauth.commands.help


class BaseCommandBehaviorTest(TestCase):
    def _assert_nonempty(self, teststring):
        self.assertIsNotNone(teststring)
        self.assertNotEqual(teststring, '')

    def test_base_properties(self):
        # for all commands listed here, check if they provide a name and
        # nonempty usage
        cmdlist = [
            radguestauth.commands.password.GeneratePasswordCommand(Mock()),
            radguestauth.commands.user.AllowCommand(Mock(), Mock()),
            radguestauth.commands.user.DenyCommand(Mock(), Mock()),
            radguestauth.commands.user.ManageUserCommand(Mock(), Mock()),
            radguestauth.commands.user.ListUsersCommand(Mock()),
            radguestauth.commands.help.HelpCommand(dict())
        ]

        for cmd in cmdlist:
            cname = cmd.name()
            usage = cmd.usage()
            self._assert_nonempty(cname)
            self._assert_nonempty(usage)
