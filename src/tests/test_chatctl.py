# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import TestCase
from unittest.mock import patch, Mock
from radguestauth.chatctl import ChatController
from radguestauth.users.storage import UserIdentifier


@patch('radguestauth.chatctl.ImplLoader')
class ChatControllerTest(TestCase):
    def _startup_controller(self, mock_loader, config={'chat': 'udp'}):
        # mock chat instance, chat class, and loader instance
        mock_chat_obj = Mock()
        mock_chat = Mock()
        mock_chat.return_value = mock_chat_obj
        mock_loader_obj = Mock()
        mock_loader_obj.load.return_value = mock_chat
        mock_loader.return_value = mock_loader_obj

        chatc = ChatController(Mock(), Mock())
        chatc.start(config)

        # chat should be loaded according to given config
        mock_loader_obj.load.assert_called_once_with(config.get('chat'))

        # tests only need a chat instance, so do not return other mocks
        return (chatc, mock_chat_obj)

    def _check_sent_messages_for(self, chat_mock, check_items):
        chat_mock.send_message.assert_called()

        found_items = set()
        for call in chat_mock.send_message.call_args_list:
            # first non-keyword argument of send_message
            text = call[0][0]
            for item in check_items:
                if item in text:
                    found_items.add(item)

        return found_items

    def _assert_in_chat_messages(self, mock_chat_obj, check_items):
        res = self._check_sent_messages_for(mock_chat_obj, check_items)
        self.assertSetEqual(set(check_items), res)

    def _assert_not_in_chat_messages(self, mock_chat_obj, check_items):
        res = self._check_sent_messages_for(mock_chat_obj, check_items)
        self.assertSetEqual(set(), res)

    def _assert_initialized(self, chatc, mock_chat_obj):
        mock_chat_obj.startup.assert_called_once()
        mock_chat_obj.register_receive.assert_called_with(
            chatc.receive_callback
        )

    def test_correct_init(self, mock_loader):
        chatc, mock_chat_obj = self._startup_controller(mock_loader)
        self._assert_initialized(chatc, mock_chat_obj)

    def test_correct_init_non_default_chat(self, mock_loader):
        chatc, mock_chat_obj = self._startup_controller(
            mock_loader, {'chat': 'xmpp'}
        )
        self._assert_initialized(chatc, mock_chat_obj)

    def test_start_generate_password(self, mock_loader):
        chatc, mock_chat_obj = self._startup_controller(
            mock_loader, {'chat': 'udp', 'generate_password_on_startup': 'yes'}
        )
        self._assert_initialized(chatc, mock_chat_obj)
        self._assert_in_chat_messages(mock_chat_obj, ['Password'])

    def test_start_generate_password_false(self, mock_loader):
        chatc, mock_chat_obj = self._startup_controller(
            mock_loader, {'chat': 'udp', 'generate_password_on_startup': 'no'}
        )
        self._assert_initialized(chatc, mock_chat_obj)
        self._assert_not_in_chat_messages(mock_chat_obj, ['Password'])

    def test_notify_join(self, mock_loader):
        chatc, mock_chat_obj = self._startup_controller(mock_loader)
        # reset calls to ignore potential startup messages
        mock_chat_obj.reset_mock()

        chatc.notify_join(UserIdentifier('fooName', 'barDevice'))

        # device and username should have been sent, possibly in multiple
        # messages.
        self._assert_in_chat_messages(mock_chat_obj, ['fooName', 'barDevice'])

    def test_notify_join_wrong_arg(self, mock_loader):
        chatc, mock_chat_obj = self._startup_controller(mock_loader)
        mock_chat_obj.reset_mock()

        chatc.notify_join(dict())

        mock_chat_obj.send_message.assert_not_called()

    def test_parse_commands(self, mock_loader):
        chatc, mock_chat_obj = self._startup_controller(mock_loader)
        mock_chat_obj.reset_mock()
        # hacky patch of known commands to avoid dependencies of tests to
        # real commands
        command_mock = Mock()
        test_message = 'testcommand executed'
        command_mock.execute.return_value = test_message
        chatc._commands = {'testcommand': command_mock}

        # (1) check unknown command
        chatc.receive_callback('somecommand')
        self._assert_not_in_chat_messages(mock_chat_obj, [test_message])
        command_mock.execute.assert_not_called()

        mock_chat_obj.reset_mock()

        # (2) check command as registered
        chatc.receive_callback('testcommand with args')
        self._assert_in_chat_messages(mock_chat_obj, [test_message])
        command_mock.execute.assert_called_once_with(['with', 'args'])

        mock_chat_obj.reset_mock()
        command_mock.reset_mock()

        # (3) check alternate uppercase command
        chatc.receive_callback('TESTCOMMAND with Args')
        self._assert_in_chat_messages(mock_chat_obj, [test_message])
        command_mock.execute.assert_called_once_with(['with', 'Args'])

    def test_correct_shutdown(self, mock_loader):
        chatc, mock_chat_obj = self._startup_controller(mock_loader)
        mock_chat_obj.reset_mock()

        chatc.stop()

        mock_chat_obj.shutdown.assert_called()
