# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import TestCase
from unittest.mock import patch, Mock
from radguestauth.chats.xmpp import XmppChat
from radguestauth.chat import ChatException


@patch('sleekxmpp.ClientXMPP')
class XmppChatTest(TestCase):
    def setUp(self):
        self.chat_config = {
            'chat_user': 'testuser',
            'chat_password': 'pass',
            'chat_recipient': 'someone'
        }
        self.chat = XmppChat()

    def _find_handler(self, mock_client, handler_name):
        msg_handler = None
        # extract handler from add_event_handler calls. Look for call
        # (handler_name, handler)
        for arg, kw_arg in mock_client.add_event_handler.call_args_list:
            if arg[0] == handler_name:
                msg_handler = arg[1]

        self.assertIsNotNone(msg_handler)
        return msg_handler

    def _check_start(self, mock_xmpp, mock_client):
        mock_xmpp.return_value = mock_client

        self.chat.startup(self.chat_config)

        mock_xmpp.assert_called_once_with('testuser', 'pass')
        mock_client.connect.assert_called_once()

    def test_startup_success(self, mock_xmpp):
        mock_client = Mock()
        mock_client.connect.return_value = True

        self._check_start(mock_xmpp, mock_client)
        mock_client.process.assert_called_once()

    def test_startup_fail(self, mock_xmpp):
        mock_client = Mock()
        mock_client.connect.return_value = False

        with self.assertRaises(ChatException):
            self._check_start(mock_xmpp, mock_client)

        mock_client.process.assert_not_called()

    def test_startup_once(self, mock_xmpp):
        mock_client = Mock()
        mock_client.connect.return_value = True

        # connect and process should only be called once, even if startup gets
        # called again
        self._check_start(mock_xmpp, mock_client)
        self.chat.startup({
            'chat_user': 'name',
            'chat_password': '123',
            'chat_recipient': 'foobar'
        })

        mock_client.connect.assert_called_once()
        mock_client.process.assert_called_once()

    def test_receive_handle(self, mock_xmpp):
        mock_client = Mock()
        mock_xmpp.return_value = mock_client
        receive_mock = Mock()

        # initialize and register test receive hook
        self.chat.register_receive(receive_mock)
        self.chat.startup(self.chat_config)

        # extract handler from add_event_handler calls.
        msg_handler = self._find_handler(mock_client, "message")

        # call handler
        msg_handler({
            'type': 'chat',
            'body': 'testmessage'
        })

        receive_mock.assert_called_once_with('testmessage')

    def test_start_handle(self, mock_xmpp):
        mock_client = Mock()
        mock_xmpp.return_value = mock_client

        self.chat.startup(self.chat_config)

        startup_handler = self._find_handler(mock_client, "session_start")

        # call handler with a Mock for the event object passed by sleekxmpp
        startup_handler(Mock())

        # a presence message should be sent on start
        mock_client.send_presence.assert_called_once()

    def test_send(self, mock_xmpp):
        mock_client = Mock()
        mock_xmpp.return_value = mock_client

        self.chat.startup(self.chat_config)

        self.chat.send_message('this is a test')

        mock_client.send_message.assert_called_once_with(
            mtype="chat", mto="someone", mbody="this is a test"
        )

    def test_shutdown(self, mock_xmpp):
        mock_client = Mock()
        mock_xmpp.return_value = mock_client

        self.chat.startup(self.chat_config)

        self.chat.shutdown()

        mock_client.connect.assert_called_once()
        mock_client.disconnect.assert_called_once()
