# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from radguestauth.command import Command


class GeneratePasswordCommand(Command):
    """
    Generate a new password which is used for the next joining user.
    """

    def __init__(self, userMgr):
        self._user_manager = userMgr

    def name(self):
        return 'PASS'

    def execute(self, argv):
        return 'Next Password: %s' % self._user_manager.generate_password()
