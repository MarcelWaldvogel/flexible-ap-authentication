# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from abc import ABCMeta, abstractmethod

# return values for RADIUS calls
REJECT = 0
ALLOW = 1
NO_OP = 2


class AuthHandler(object):
    """
    Interface which defines hooks for user authorization.

    The on_authorize methods should be mainly used to define attributes which
    are returned by the authorize call.

    If your handler needs to perform actions like changing system config files,
    the on_host methods are the right place to do.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def start(self, config):
        """
        Enables the handler to process the radguestauth config dict.
        Gets called on startup.

        :param config: config dict from core module
        """
        return NotImplemented

    @abstractmethod
    def shutdown(self):
        """
        Called when the guestauth module exits.
        """
        return NotImplemented

    @abstractmethod
    def handle_user_state(self, user, state, acct_session):
        """
        Based on the user's join state, determine the return value for
        GuestAuthCore.authorize

        :param user: UserIdentifier to be handled
        :param state: The current state (as UserIdentifier might not contain
            a UserData object)
        :param acct_session: The FreeRADIUS accounting session ID
        :returns: A tuple to return in GuestAuthCore.authorize;
            with REJECT, ALLOW or NO_OP as first value and
            a dict with additional RADIUS attributes as second value
        """
        return NotImplemented

    @abstractmethod
    def on_post_auth(self, user, acct_session):
        """
        Called in GuestAuthCore.post_auth. Determines the return value for
        RADIUS post_auth events.

        :param user: UserIdentifier to be handled (without UserData)
        :param acct_session: The FreeRADIUS accounting session ID
        :returns: A dict like in authorize, or None if no attributes are set
        """
        return NotImplemented

    @abstractmethod
    def on_host_accept(self, user):
        """
        Called when the host accepted the user.

        :param user: UserIdentifier to be handled
        :returns: a message as string which is sent to the host
        """
        return NotImplemented

    @abstractmethod
    def on_host_deny(self, user):
        """
        Called when the host denied the user.

        :param user: UserIdentifier to be handled
        :returns: a message as string which is sent to the host
        """
        return NotImplemented
