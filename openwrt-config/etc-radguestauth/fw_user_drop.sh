#!/bin/sh

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

RULE_NAME=$(/etc/radguestauth/fw_check.sh $1)

if [ $? -ne 0 ]
then
  exit
fi;

uci delete firewall.$RULE_NAME
uci commit firewall
/etc/init.d/firewall reload >/dev/null 2>&1
if [ $? -eq 0 ]
then
  echo "Dropped user."
else
  echo "Error. Resetting firewall..."
  /etc/radguestauth/fw_reset.sh
fi;
