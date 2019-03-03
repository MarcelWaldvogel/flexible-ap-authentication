#!/bin/sh

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

if [ $# -ne 1 ]
then
  echo "This command needs a MAC address as argument." >&2
  exit 1
fi;

if [ -z $(echo "$1" | grep -E "^(([0-9a-e]{2}):){5}[0-9a-e]{2}\$") ]
then
  echo "Invalid MAC" >&2
  exit 1
fi;

# query uci config for the MAC. -X prints rule names instead of indices.
# if found, the line looks like firewall.cfg1892bd.src_mac=...
# use sed to extract the cfg part.
RULE_NAME=$(uci -X show firewall | grep "$1" | sed "s/^firewall\.\(.*\)\.src_mac.*\$/\1/g")
# currently the name cfg... is 9 characters long, so 10 including \0
NAME_LEN=10

if [ $(echo "$RULE_NAME" | wc -c) -ne $NAME_LEN ]
then
  echo "no matching rule found."
  exit 2
fi;

echo $RULE_NAME
