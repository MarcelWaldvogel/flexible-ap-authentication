# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from radguestauth.command import Command


class HelpCommand(Command):
    """
    Show help for the available commands.
    """

    def __init__(self, cmdDict):
        self._commands = cmdDict

    @staticmethod
    def _fmt(cmd):
        return '%s: %s\n' % (cmd.name(), cmd.__doc__)

    def name(self):
        return 'HELP'

    def execute(self, argv):
        output = self.usage()
        arglen = len(argv)

        if arglen == 0:
            output = 'Available commands:\n\n'

            for cmd in self._commands.values():
                output += '* %s' % HelpCommand._fmt(cmd)

            output += '\nUse help followed by the command name for details.'
        elif arglen == 1:
            cmd = self._commands.get(argv[0].lower())
            if cmd:
                output = HelpCommand._fmt(cmd) + cmd.usage()
            else:
                output = 'Unknown command.'

        return output

    def usage(self):
        base = super(HelpCommand, self).usage()
        return (base + ' [[ command_name ]]\n\n'
                + 'when the optional command name is given, show its usage.')
