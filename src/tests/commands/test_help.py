# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import TestCase
from unittest.mock import Mock
from radguestauth.commands.help import HelpCommand


class HelpCommandTest(TestCase):
    def setUp(self):
        self.usage1 = 'this is cmd1 usage'
        self.usage2 = '#1234'
        cmock1 = Mock()
        cmock1.name.return_value = 'command'
        cmock1.usage.return_value = self.usage1
        cmock2 = Mock()
        cmock2.name.return_value = 'otherThing'
        cmock2.usage.return_value = self.usage2
        self.cmd_dict = {
            'command': cmock1,
            'otherThing': cmock2
        }

        self.cmd = HelpCommand(self.cmd_dict)

    def _assert_no_exec(self):
        for cmock in self.cmd_dict.values():
            cmock.execute.assert_not_called()

    def test_no_args(self):
        output = self.cmd.execute([])

        for name in self.cmd_dict.keys():
            self.assertIn(name, output)

        self._assert_no_exec()

    def test_exising_cmd(self):
        output = self.cmd.execute(['command'])

        self.assertIn(self.usage1, output)
        self.assertFalse(self.usage2 in output)
        self._assert_no_exec()

    def test_non_exising_cmd(self):
        output = self.cmd.execute(['command12'])

        self.assertFalse(self.usage1 in output)
        self.assertFalse(self.usage2 in output)
        self._assert_no_exec()
