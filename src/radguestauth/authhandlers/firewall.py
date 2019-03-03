# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import radguestauth.auth as auth
from radguestauth.authhandlers.util import AuthUtils
from radguestauth.users.storage import UserIdentifier, UserData


class FirewallAuthHandler(auth.AuthHandler):
    """
    This handler uses the OpenWRT firewall to allow and block users.
    """
    def __init__(self):
        self._last_session_waiting = None

    def _run_cmd(self, cmd, device_id=None):
        full_cmd = '/etc/radguestauth/fw_%s.sh' % cmd
        args = None
        if device_id:
            args = [UserIdentifier.format_mac(device_id)]

        return AuthUtils.sudo_cmd(
            full_cmd, additional_args=args,
            error_return='Command failed: %s' % cmd
        )

    def start(self, config):
        self._run_cmd('reset')

    def shutdown(self):
        self._run_cmd('reset')

    def handle_user_state(self, user, state, acct_session):
        if state == UserData.JOIN_STATE_WAITING:
            # ensure that the user is not in the whitelist.
            # This occurs when the user was previously allowed and the
            # timeout/join numbers expire.
            self._run_cmd('user_drop', user.device_id)
            self._last_session_waiting = acct_session
        else:
            self._last_session_waiting = None

        return AuthUtils.reject_only_when_blocked(user, state)

    def on_post_auth(self, user, acct_session):
        if (self._last_session_waiting
                and acct_session == self._last_session_waiting):
            # let waiting users re-connect frequently such that a
            # potential timeout gets set after the user was allowed
            return {'reply:Session-Timeout': 60}
        return None

    def on_host_accept(self, user):
        return self._run_cmd('user_add', user.device_id)

    def on_host_deny(self, user):
        res_msg = self._run_cmd('user_drop', user.device_id)
        # force re-connect in case of blocking.
        if (user.user_data
                and user.user_data.join_state == UserData.JOIN_STATE_BLOCKED):
            if res_msg:
                res_msg += '\n'
            else:
                # could be None, so set to empty str
                res_msg = ''
            res_msg += AuthUtils.disassociate_user(user.device_id)

        return res_msg
