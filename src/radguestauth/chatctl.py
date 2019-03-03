# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from radguestauth.chats.udp import UdpChat
from radguestauth.chat import Chat
from radguestauth.loader import ImplLoader
from radguestauth.users.storage import UserIdentifier
from radguestauth.commands.user import (AllowCommand, DenyCommand,
                                        ListUsersCommand, ManageUserCommand)
from radguestauth.commands.help import HelpCommand
from radguestauth.commands.password import GeneratePasswordCommand


class ChatController(object):
    """
    Manages command execution on incoming messages, user notification et cetera
    """

    def __init__(self, user_mgr, auth_handler):
        self._chat = None
        self._user_manager = user_mgr
        self._auth_handler = auth_handler
        # keep instance of password command to enable password generation
        # on startup
        self._pw_command = GeneratePasswordCommand(self._user_manager)
        self._commands = dict()

        # -- Create an instance of each command here to enable it. --
        known_commands = [
            AllowCommand(self._user_manager, self._auth_handler),
            DenyCommand(self._user_manager, self._auth_handler),
            ListUsersCommand(self._user_manager),
            ManageUserCommand(self._user_manager, self._auth_handler),
            self._pw_command,
            HelpCommand(self._commands),
        ]
        # -- no more changes necessary to add new commands --

        # Automatically resolve names for all commands and store them in a dict
        for cmd in known_commands:
            self._commands[cmd.name().lower()] = cmd

    def start(self, config):
        """
        Initialize the chat system based on the given configuration.
        """
        loader = ImplLoader(Chat, UdpChat)
        chat_impl = loader.load(config.get('chat', 'udp'))
        self._chat = chat_impl()

        self._chat.register_receive(self.receive_callback)
        self._chat.startup(config)
        self._chat.send_message('Guest Auth module started.')

        if config.get('generate_password_on_startup') == 'yes':
            self._chat.send_message(self._pw_command.execute([]))

    def receive_callback(self, text):
        """
        Callback method which handles incoming messages.

        :param text: the chat message as string
        """
        lst = text.replace('\n', '').split(' ')
        cmd = lst[0]
        args = lst[1:]

        command_instance = self._commands.get(cmd.lower())
        if command_instance:
            result = command_instance.execute(args)
        else:
            result = 'Unknown command: %s' % text

        self._chat.send_message(result)

    def notify_join(self, user_id):
        if not isinstance(user_id, UserIdentifier):
            return

        self._chat.send_message('%s wants to join with device %s'
                                % (user_id.name, user_id.device_id))

    def stop(self):
        self._chat.send_message('Guest Auth module is shutting down.')
        self._chat.shutdown()
