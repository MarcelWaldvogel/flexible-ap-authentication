#!/bin/sh

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# exits with code 2 if input is correct but no rule exists.
# Drop stdout, as no message should be printed if a rule doesn't exist.
/etc/radguestauth/fw_check.sh $1 >/dev/null

# only continue if the rule wasn't already added
if [ $? -ne 2 ]
then
  exit
fi;

RULE_NAME=$(uci add firewall rule)
uci set firewall.$RULE_NAME.src='offline'
uci set firewall.$RULE_NAME.dest='wan'
uci set firewall.$RULE_NAME.target='ACCEPT'
uci set firewall.$RULE_NAME.src_mac="$1"
uci commit firewall
/etc/init.d/firewall reload >/dev/null 2>&1
if [ $? -eq 0 ]
then
  echo $RULE_NAME
else
  echo "Error. Resetting firewall..."
  /etc/radguestauth/fw_reset.sh
fi;
