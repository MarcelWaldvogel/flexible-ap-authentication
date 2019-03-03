# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import subprocess
import radguestauth.auth as auth
from radguestauth.users.storage import UserIdentifier, UserData


class AuthUtils(object):
    """
    Generic functions which are useful for multiple handlers.
    """

    @staticmethod
    def reject_only_when_blocked(user, state):
        """
        Can be used in authorize calls, allows known and waiting users.

        :param user: UserIdentifier to be handled
        :param state: The current state (as UserIdentifier might not contain
            a UserData object)
        :returns: A tuple to return in GuestAuthCore.authorize;
            with REJECT, ALLOW or NO_OP as first value and
            a dict with additional RADIUS attributes as second value
        """
        if state == UserData.JOIN_STATE_BLOCKED:
            return (auth.REJECT, None)

        return (auth.ALLOW, {'control:Cleartext-Password': user.password})

    @staticmethod
    def sudo_cmd(cmd, additional_args=None, success_return=None,
                 error_return=None):
        """
        Executes the given command via sudo. This is intended for the
        OpenWRT setup, where firewall changes and user disassociations
        are done via calls to the corresponding scripts or tools.

        :param cmd: The command as string
        :param additional_args: Optional list of arguments
        :param success_return: Return value if the execution succeeded
        :param error_return: Return value if the execution failed
        :returns: Configured values (see params) or None as default
        """
        args = ['sudo', cmd]

        if additional_args:
            args += additional_args

        try:
            subprocess.run(args, timeout=2, check=True)
            return success_return
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return error_return

    @staticmethod
    def disassociate_user(device_id):
        """
        Disassociates the user with the given device_id / MAC from the AP.

        Important: this is specific to the OpenWRT environment.
        Logic to send generic RADIUS CoA packets is needed if you want to use
        external APs or a different environment.

        :returns: A string message indicating success or failure
        """
        mac = UserIdentifier.format_mac(device_id)
        # Directly use hostapd_cli to avoid more complex CoA handling for
        # OpenWRT env
        return AuthUtils.sudo_cmd(
            'hostapd_cli', additional_args=['disassociate', mac],
            success_return='User forced to re-connect (disassociated).',
            error_return='Could not disassociate user.'
        )
