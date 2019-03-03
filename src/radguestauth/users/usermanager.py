# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time

from random import SystemRandom
from operator import attrgetter

from radguestauth.users.storage import UserIdentifier, UserData


class UserManager(object):
    """
    Keeps track of known users and provides logic to let new users join.
    """

    def __init__(self):
        self._request_user = None
        self._current_password = ''
        # keeps UserIdentifier objects with their name as key
        self._users = dict()
        # also keep track of used MAC addresses to avoid duplicates
        self._mac_addrs = set()

    def may_join(self, user_id):
        """
        Determines if the given user may join. An UserData.JOIN_STATE is
        returned.

        User state transitions:
        * new --> (request gets added) waiting
            --> (host reaction) allowed/blocked
        * When valid_until or num_joins is exceeded: allowed --> new
        * When user is dropped: allowed/blocked --> new
        """
        # block if given user is not valid
        if not isinstance(user_id, UserIdentifier):
            return UserData.JOIN_STATE_BLOCKED

        # The request user doesn't have UserData assigned yet,
        # so handle separately before querying the user list.
        if (self._request_user and user_id == self._request_user):
            return UserData.JOIN_STATE_WAITING

        stored = self._users.get(user_id.name)
        # When the user wasn't found, a new request can be added if there
        # is no other user with this MAC/device ID
        if stored is None:
            if user_id.device_id_as_mac() in self._mac_addrs:
                return UserData.JOIN_STATE_BLOCKED

            return UserData.JOIN_STATE_NEW

        # block user if devices don't match or data is invalid
        if (user_id != stored
                or not isinstance(stored.user_data, UserData)):
            return UserData.JOIN_STATE_BLOCKED

        # If the user is blocked do not process time or number of joins
        if stored.user_data.join_state == UserData.JOIN_STATE_BLOCKED:
            return UserData.JOIN_STATE_BLOCKED

        # finally check validity time and number of joins, and remove the user
        # if any is exceeded. Then, the host will be prompted again.
        if stored.check_expired(True):
            self.remove(user_id)
            return UserData.JOIN_STATE_NEW

        # at this point, all checks are passed and the stored state can be
        # considered (very likely ALLOWED).
        return stored.user_data.join_state

    def is_request_pending(self):
        return (self._request_user is not None)

    def add_request(self, user_id):
        if not isinstance(user_id, UserIdentifier):
            return False

        if self.is_request_pending():
            return False

        # TODO: this form only allows each name to be used once, with one
        # device. Enhance such that multiple devices are possible
        if self._users.get(user_id.name):
            return False

        self._request_user = UserIdentifier(user_id.name, user_id.device_id,
                                            self._current_password)
        self._mac_addrs.add(user_id.device_id_as_mac())

        return True

    def get_request(self):
        return self._request_user

    def finish_request(self):
        self._request_user = None

    def find(self, username):
        return self._users.get(username)

    def update(self, user_id):
        if not isinstance(user_id, UserIdentifier):
            return

        # update a stored item, or add the request user to the list
        if self._users.get(user_id.name) or self._request_user == user_id:
            self._users[user_id.name] = user_id

    def remove(self, user_id):
        if not isinstance(user_id, UserIdentifier):
            return

        if self._users.get(user_id.name):
            self._mac_addrs.remove(user_id.device_id_as_mac())
            self._users.pop(user_id.name)

    def list_users(self):
        return sorted(self._users.values(), key=attrgetter('name'))

    def get_expired_users(self):
        return list(filter(lambda u: u.check_expired(), self._users.values()))

    def generate_password(self):
        # TODO: For now, use random numbers. Improve this mechanism later.
        rand = SystemRandom()
        self._current_password = str(rand.randint(0, 999999))
        return self._current_password
