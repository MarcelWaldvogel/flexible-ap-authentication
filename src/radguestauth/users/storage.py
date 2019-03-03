# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time


class UserIdentifier(object):
    """
    Describes an user entity.
    """

    def __init__(self, name, device_id, password=None):
        self.name = name
        self.device_id = device_id
        self.password = password
        self.user_data = None

    def __eq__(self, cmp):
        # users are considered equal if name and device match, regardless
        # what user_data is assigned or what password is stored
        if not isinstance(cmp, UserIdentifier):
            return False

        return (self.name == cmp.name
                and self.device_id == cmp.device_id)

    def __str__(self):
        pw_str = (('Password: ' + self.password) if self.password
                  else 'No password.')
        dat_str = str(self.user_data) if self.user_data else 'No user data.'

        return ('Name: ' + self.name + '\nDevice ID: ' + self.device_id
                + '\n' + pw_str + '\n\n'
                + dat_str)

    def device_id_as_mac(self):
        """
        Gets the device ID formatted as a regular MAC address
        separated by colons.
        """
        return UserIdentifier.format_mac(self.device_id)

    def check_expired(self, increase_num_joins=False):
        """
        Calls UserData.check_expired on the associated UserData item,
        if available. Otherwise, False is returned.
        """
        if isinstance(self.user_data, UserData):
            return self.user_data.check_expired(increase_num_joins)

        return False

    @staticmethod
    def format_mac(rad_device_id):
        """
        Converts a FreeRADIUS device ID with dashes to a regular MAC address
        separated by colons.

        This static method is provided for convenience, as sometimes no user
        object instances are involved (e.g. in AuthHandlers).

        If an UserIdentifier object is available, device_id_as_mac is the
        better choice.
        """
        return rad_device_id.replace('-', ':').lower()


class UserData(object):
    """
    Describes additional data assigned to an User.
    """
    # See UserManager.may_join for details on state transitions.
    JOIN_STATE_NEW = 0
    JOIN_STATE_WAITING = 1
    JOIN_STATE_ALLOWED = 2
    JOIN_STATE_BLOCKED = 3

    def state_string(self):
        """
        Returns the join_state as string.
        """
        state = 'Waiting for approval'
        if self.join_state == self.JOIN_STATE_ALLOWED:
            state = 'Allowed'
        elif self.join_state == self.JOIN_STATE_BLOCKED:
            state = 'Blocked'

        return state

    def __init__(self):
        self.valid_until = None
        self.num_joins = 0
        self.max_num_joins = 0
        self.join_state = self.JOIN_STATE_ALLOWED

    def __str__(self):
        return ('User data:\nValid until: '
                + time.strftime('%Y-%m-%d %H:%M:%S',
                                time.gmtime(self.valid_until))
                + '\nNumber of joins: ' + str(self.num_joins)
                + '\nMax. number of allowed joins: ' + str(self.max_num_joins)
                + '\nState: ' + self.state_string())

    def check_expired(self, increase_num_joins=False):
        """
        Checks if the valid_until time has expired or the num_joins
        are exceeded. Optionally, the num_joins can be increased
        after the check.

        :param increase_num_joins: If True, and if max_num_joins is set,
            the num_joins are increased by one.
        :returns: True if the limits expired.
        """
        if (self.valid_until and self.valid_until < time.time()):
            return True
        elif self.max_num_joins != 0:
            if self.num_joins >= self.max_num_joins:
                return True
            elif increase_num_joins:
                # not expired, but increase number
                self.num_joins += 1

        return False
