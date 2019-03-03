#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

if [ -e /vagrant/src ]
then
  cd /vagrant/src
elif [ -e /etc/radguestauth ]
then
  cd /etc/radguestauth
fi;

# start by copying example_config.ini to config.ini in this directory (src).
# It will work in the Vagrant env.
# You can also give the config file name as argument to this script.
RADGUESTAUTH_CONFIG=${1:-config.ini} gunicorn --log-level debug -b 127.0.0.1:5000 \
"radguestauth.server:create_app()" -c python:radguestauth.server
