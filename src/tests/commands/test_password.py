# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import TestCase
from unittest.mock import Mock
from radguestauth.commands.password import GeneratePasswordCommand


class GeneratePasswordCommandTest(TestCase):
    def test_usermanager_call(self):
        mock_um = Mock()
        mock_um.generate_password.return_value = 'mypw1234'
        cmd = GeneratePasswordCommand(mock_um)
        result = cmd.execute([])

        self.assertIn('mypw1234', result)
        mock_um.generate_password.assert_called_once()
