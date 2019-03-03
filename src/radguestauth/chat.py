# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from abc import ABCMeta, abstractmethod


class Chat(object):
    """
    Interface used to integrate a chat protocol/server into the guest auth
    module.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def startup(self, config):
        """
        Called when the guest auth module starts.

        :param config: config dict from core module
        """
        return NotImplemented

    @abstractmethod
    def send_message(self, message):
        """
        Send the string via chat without a callback.

        :param message: the string to transmit
        """
        return NotImplemented

    @abstractmethod
    def register_receive(self, receive_hook):
        """
        Receiving messages is done via a hook method taking one argument
        (the message). This method tells the chat controller which method
        to call.

        :param receive_hook: function taking one string argument and which is
            called when a new message arrives.
        """
        return NotImplemented

    @abstractmethod
    def shutdown(self):
        """
        Called before the guest auth module exits.
        """
        return NotImplemented


class ChatException(Exception):
    """
    Exception which should be used for errors in classes implementing Chat.
    """
    def __init__(self, message):
        self.message = message
