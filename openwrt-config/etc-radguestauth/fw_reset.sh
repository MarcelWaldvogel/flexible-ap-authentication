#!/bin/sh

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# defaults file is copied from etc/config on setup
uci -f /etc/radguestauth/firewall_default import firewall
/etc/init.d/firewall reload
