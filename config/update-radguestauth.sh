#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# helper script which builds the python module and upgrades it on the raspberry
cd ../src
make dist
cd -
ANSIBLE_SCP_IF_SSH=1 ansible-playbook -i openwrt-inventory.ini -u root playbook.yml --skip-tags "firstrun"
