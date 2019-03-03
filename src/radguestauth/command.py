# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from abc import ABCMeta, abstractmethod


class Command(object):
    """
    Defines a command which can be called by the ChatController
    """
    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def name(self):
        """
        Name of the command as string. Used to determine when the command is
        executed. The general pattern in the ChatController is

        <name> <arg1> ... <argN>

        When <name> matches a command, the execute() of this command is called.
        """
        return NotImplemented

    @abstractmethod
    def execute(self, argv):
        """
        Execute the command.

        :param argv: List of argument strings
        :returns: Result as String to be sent to the user
        """
        return NotImplemented

    def usage(self):
        """
        Get usage information and help for this command.

        :returns: A String containing usage information.
        """
        return 'Usage: %s' % self.name()
