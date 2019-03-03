# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time
import functools

from abc import ABCMeta

from radguestauth.command import Command
from radguestauth.users.storage import UserData, UserIdentifier


def build_answer(base, optional):
    """
    Creates a chat message containing base. If optional is defined, it is
    appended with a newline. This is called in several commands below.
    """
    if optional:
        return '%s\n%s' % (base, optional)

    return '%s' % base


class UserModifyingCommand(Command):
    """
    Common base class for commands which modify user data (allow and modify).
    """
    __metaclass__ = ABCMeta

    MAX_HOURS = 24

    def __init__(self, user_mgr, auth_handler):
        self._user_manager = user_mgr
        self._auth_handler = auth_handler

    def _parse_modify(self, argv):
        """
        Parses the commands which allow an user to join n times (Syntax
        'n times') or for n hours ('for n h'), with n being an integer.

        :param argv: the argument values split by spaces
        :returns: In case the command was correct: a tuple (int, boolean) with
            the int being either the join count (boolean is true) or the hours
            (boolean is false). If the command was incorrect, a help message
            as string is returned.
        """
        n = None
        count_mode = False
        if len(argv) >= 2 and argv[0].isnumeric() and argv[1] == 'times':
            n = int(argv[0])
            count_mode = True
        elif (len(argv) >= 3 and argv[0] == 'for'
              and argv[1].isnumeric() and argv[2] == 'h'):
            n = int(argv[1])

            if n > self.MAX_HOURS:
                return 'No more than %s hours are possible' % self.MAX_HOURS
        else:
            return self.usage()

        return (n, count_mode)

    def _update_with_parse_tuple(self, user_id, parse_tuple):
        """
        Updates the UserIdentifier based on the parse result from
        _parse_modify.

        :param user_id: The UserIdentifier to update
        :param parse_tuple: Tuple (int, boolean) from _parse_modify
        :return: String to be sent to the host
        """
        if not isinstance(parse_tuple, tuple):
            return 'No update, parsing problem'

        n = parse_tuple[0]
        count_mode = parse_tuple[1]
        data = user_id.user_data
        data.join_state = UserData.JOIN_STATE_ALLOWED

        if count_mode:
            data.max_num_joins = n
            data.valid_until = None
        else:
            # use n as hours (60^2 seconds)
            data.valid_until = time.time() + n * 3600
            data.max_num_joins = 0

        self._user_manager.update(user_id)
        message = self._auth_handler.on_host_accept(user_id)
        return build_answer('OK', message)


class AllowCommand(UserModifyingCommand):
    """
    Allow an user.
    """

    def __init__(self, user_mgr, auth_handler):
        super(AllowCommand, self).__init__(user_mgr, auth_handler)

    def name(self):
        return 'OK'

    def execute(self, argv):
        if len(argv) not in [2, 3]:
            return self.usage()

        parsed = self._parse_modify(argv)

        if not isinstance(parsed, tuple):
            return parsed

        if not self._user_manager.is_request_pending():
            return 'No request pending.'

        req = self._user_manager.get_request()
        if not isinstance(req, UserIdentifier):
            return 'Invalid request in UserManager'

        req.user_data = UserData()
        message = self._update_with_parse_tuple(req, parsed)

        self._user_manager.finish_request()

        return message

    def usage(self):
        base = super(AllowCommand, self).usage()
        return (base + ' [count | time]\n\n'
                + 'where count ::= <n> times\n'
                + 'time ::= for <t> h\n\n'
                + 'Examples:\n'
                + 'OK 10 times\n'
                + 'OK for 3 h')


class DenyCommand(Command):
    """
    Deny an user.
    """

    def __init__(self, user_mgr, auth_handler):
        self._user_manager = user_mgr
        self._auth_handler = auth_handler

    def name(self):
        return 'NO'

    def execute(self, argv):
        if not self._user_manager.is_request_pending():
            return 'No request pending.'

        req = self._user_manager.get_request()
        if not isinstance(req, UserIdentifier):
            return 'Invalid request in UserManager'

        req.user_data = UserData()
        req.user_data.join_state = UserData.JOIN_STATE_BLOCKED
        self._user_manager.update(req)
        self._user_manager.finish_request()

        message = self._auth_handler.on_host_deny(req)
        return build_answer('User denied.', message)


class ListUsersCommand(Command):
    """
    List known users.
    """

    def __init__(self, user_mgr):
        self._user_manager = user_mgr

    def _get_user_line(self, user):
        blockstr = ''
        if (user.user_data is not None
                and user.user_data.join_state == UserData.JOIN_STATE_BLOCKED):
            blockstr = ' [blocked]'

        return '%s (device %s)%s\n' % (user.name, user.device_id, blockstr)

    def name(self):
        return 'LIST'

    def execute(self, argv):
        result = ''
        if self._user_manager.is_request_pending():
            req_user = self._user_manager.get_request()
            result += ('There is an ongoing request for %s.\n'
                       % self._get_user_line(req_user))
            result += 'Use OK or NO to decide about this user.\n'
            result += 'Until then, only allowed users may join.\n\n'

        result += 'Known users:\n'
        for u in self._user_manager.list_users():
            result += '* %s\n' % self._get_user_line(u)

        return result


class ManageUserCommand(UserModifyingCommand):
    """
    Change user options like validity time, maximum Joins etc.
    """

    def __init__(self, user_mgr, auth_handler):
        super(ManageUserCommand, self).__init__(user_mgr, auth_handler)

    def _block_user(self, user_id):
        userdata = user_id.user_data

        if userdata is None:
            userdata = UserData()
            user_id.user_data = userdata

        userdata.join_state = UserData.JOIN_STATE_BLOCKED
        self._user_manager.update(user_id)
        message = self._auth_handler.on_host_deny(user_id)

        return build_answer('User denied.', message)

    def _drop_user(self, user_id):
        was_blocked = (
            user_id.user_data
            and user_id.user_data.join_state == UserData.JOIN_STATE_BLOCKED
        )
        self._user_manager.remove(user_id)
        # In case the user was already blocked, the auth handler doesn't need
        # to perform any action (was done on blocking or deny handling).
        # Otherwise, notify the AuthHandler.
        message = None
        if not was_blocked:
            message = self._auth_handler.on_host_deny(user_id)

        return build_answer('User removed.', message)

    def name(self):
        return 'MANAGE'

    def execute(self, argv):
        if len(argv) >= 2:
            cname = argv[0].lower()
            # if a valid command was found, define an action (i.e. a function
            # performing an action on the UserIdentifier)
            action = None
            # index where the username starts (might have been split by spaces)
            user_pos = 1
            # text to return if action has no return value
            return_text = None

            if cname == 'show':
                # return the string representation of the user
                action = str
            elif cname == 'allow':
                # subcommand syntax is identical to the allow command, so
                # drop the first keyword and use common parse logic.
                parsed = self._parse_modify(argv[1:])

                if not isinstance(parsed, tuple):
                    return parsed

                # user name position depends on "<n> times" vs "for <t> h" mode
                # indicated by the boolean in the secod tuple parameter
                user_pos = 3 if parsed[1] else 4
                # update the user and return OK if successful. Use a partial
                # function such that a callable taking only the UserIdentifier
                # results.
                action = functools.partial(self._update_with_parse_tuple,
                                           parse_tuple=parsed)
            elif cname == 'block':
                action = self._block_user
            elif cname == 'drop':
                action = self._drop_user

            # execute the respective logic if the command was valid
            if action:
                # get username as one string again
                username = ' '.join(argv[user_pos:])
                user_id = self._user_manager.find(username)
                if not user_id:
                    return 'Unknown user'

                result = action(user_id)
                if return_text:
                    return return_text
                # use value returned by action if no text was set for the
                # command
                return result

        # default fall-through
        return self.usage()

    def usage(self):
        base = super(ManageUserCommand, self).usage()
        return (base + ' [show | count | time | block | drop] name\n\n'
                + 'where show ::= SHOW\n'
                + 'count ::= ALLOW <n> times\n'
                + 'time ::= ALLOW for <t> h\n'
                + 'block ::= BLOCK\n'
                + 'drop ::= DROP\n\n'
                + 'Examples:\n'
                + 'MANAGE SHOW bob\n'
                + 'MANAGE ALLOW for 3 h bob\n\n'
                + 'block denies the user without notification, drop deletes '
                + 'the user information, leading to notifications when the '
                + 'user joins again.')
