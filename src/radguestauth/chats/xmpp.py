# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sleekxmpp

from radguestauth.chat import Chat, ChatException


class XmppChat(Chat):
    def __init__(self):
        self.receive_hook = lambda m: None
        self.started = False
        # declare members, those are initialized in startup()
        self.client = None
        self._recipient = None
        self._use_tls = True

    def _starthandler(self, _):
        self.client.send_presence()
        self.client.get_roster()

    def _msghandler(self, msg):
        if msg['type'] in ('chat', 'normal'):
            self.receive_hook(msg['body'])

    # chat interface
    def startup(self, config):
        if self.started:
            return

        self.client = sleekxmpp.ClientXMPP(config.get('chat_user'),
                                           config.get('chat_password'))
        self._recipient = config.get('chat_recipient')
        # use TLS by default, but allow to disable it
        if config.get('xmpp_use_tls') == 'no':
            self._use_tls = False

        self.client.add_event_handler("session_start", self._starthandler)
        self.client.add_event_handler("message", self._msghandler)

        if self.client.connect(use_tls=self._use_tls, reattempt=False):
            self.client.process()
        else:
            raise ChatException('Failed to boot XMPP chat')

        self.started = True

    def send_message(self, message):
        self.client.send_message(mto=self._recipient,
                                 mbody=message,
                                 mtype='chat')

    def register_receive(self, receive_hook):
        self.receive_hook = receive_hook

    def shutdown(self):
        if self.started:
            # When using the Flask development server, a deadlock occurs
            # at this point (because of SleekXMPP's threading, see also
            # server.py). Using a server with other workers such as
            # eventlet works fine.
            self.client.disconnect()
            self.started = False
