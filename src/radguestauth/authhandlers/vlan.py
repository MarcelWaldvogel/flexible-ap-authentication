# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import radguestauth.auth as auth
from radguestauth.users.storage import UserData
from radguestauth.authhandlers.util import AuthUtils


class VlanAuthHandler(auth.AuthHandler):
    """
    Uses 802.1q dynamic VLAN assignment instead of just accepting and
    rejecting users like DefaultAuthHandler.
    """

    def __init__(self):
        self._set_defaults()

    def _set_defaults(self):
        self._session = ''
        self._user = None
        self._state = UserData.JOIN_STATE_BLOCKED

    def start(self, config):
        pass

    def shutdown(self):
        pass

    def handle_user_state(self, user, state, acct_session):
        # remember attributes to match with post_auth call
        self._user = user
        self._state = state
        self._session = acct_session

        return AuthUtils.reject_only_when_blocked(user, state)

    def on_post_auth(self, user, acct_session):
        # Assign to VLAN with connectivity if attributes match and user is
        # allowed.
        if (acct_session == self._session and user == self._user
                and self._state == UserData.JOIN_STATE_ALLOWED):
            vlan = '2'
        else:
            vlan = '1'
        # always reset stored values to avoid wrong VLAN assignments
        self._set_defaults()
        return {'reply:Tunnel-Type': 'VLAN',
                'reply:Tunnel-Medium-Type': 'IEEE-802',
                'reply:Tunnel-Private-Group-ID': vlan}

    def _reconnect_user(self, device_id):
        return ('Trying to re-connect user to update VLAN...\n%s'
                % AuthUtils.disassociate_user(device_id))

    def on_host_accept(self, user):
        return self._reconnect_user(user.device_id)

    def on_host_deny(self, user):
        return self._reconnect_user(user.device_id)
