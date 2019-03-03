# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import radguestauth.auth as auth
from radguestauth.users.storage import UserData


class DefaultAuthHandler(auth.AuthHandler):
    """
    Default behavior which can be used with any Access Point (No Firewall or
    VLANs).

    No additional actions are performed by this handler.
    """

    def start(self, config):  # pragma: no cover
        # Ignore this and similar methods in code coverage report
        pass

    def shutdown(self):  # pragma: no cover
        pass

    def handle_user_state(self, user, state, acct_session):
        # reject everyone except allowed users
        if state == UserData.JOIN_STATE_ALLOWED:
            return (auth.ALLOW, {'control:Cleartext-Password': user.password})

        return (auth.REJECT, None)

    def on_post_auth(self, user, acct_session):  # pragma: no cover
        return None

    def on_host_accept(self, user):  # pragma: no cover
        return None

    def on_host_deny(self, user):  # pragma: no cover
        return None
