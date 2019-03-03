#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Download and unzip imagebuilder for raspberry in the subdirectory
# given below (openwrt-imagebuilder).
# https://downloads.openwrt.org/releases/18.06.1/targets/brcm2708/bcm2710/
cd ../openwrt-imagebuilder
rm -rf files

mkdir -p files/etc/dropbear
cat ~/.ssh/id_rsa.pub >files/etc/dropbear/authorized_keys
chmod 0700 files/etc/dropbear
chmod 0600 files/etc/dropbear/authorized_keys

mkdir -p files/etc/config
cp ../openwrt-config/etc-config/* files/etc/config

mkdir -p files/etc/crontabs
cp ../openwrt-config/etc-crontabs/root files/etc/crontabs

mkdir -p files/etc/freeradius3
cp -r ../openwrt-config/etc-freeradius3/* files/etc/freeradius3

mkdir -p files/etc/radguestauth/pkg
cp ../openwrt-config/etc-radguestauth/* files/etc/radguestauth
cp ../openwrt-config/etc-config/firewall files/etc/radguestauth/firewall_default
chmod +x files/etc/radguestauth/*.sh

mkdir -p files/etc/init.d
cp ../openwrt-config/services/radguestauth files/etc/init.d
chmod +x files/etc/init.d/radguestauth

cp ../openwrt-config/sudo-cfg/sudoers files/etc/sudoers
chmod 0440 files/etc/sudoers

cd ../src
make dist
cd -
cp ../src/dist/radguestauth-$(cat ../src/dist/radguestauth-ver)-py3-none-any.whl files/etc/radguestauth/pkg
cp ../src/config.ini files/etc/radguestauth/
cp ../src/run_server.sh files/etc/radguestauth/
cp ../src/requirements.txt files/etc/radguestauth/
# --- Package list ----
# As freeradius3-default is not installable, list the packages explicitly
FR3_BASE_PKGS="freeradius3 freeradius3-democerts freeradius3-mod-always freeradius3-mod-attr-filter freeradius3-mod-chap freeradius3-mod-detail freeradius3-mod-digest freeradius3-mod-eap freeradius3-mod-eap-gtc freeradius3-mod-eap-leap freeradius3-mod-eap-md5 freeradius3-mod-eap-mschapv2 freeradius3-mod-eap-peap freeradius3-mod-eap-tls freeradius3-mod-eap-ttls freeradius3-mod-eap-pwd freeradius3-mod-exec freeradius3-mod-expiration freeradius3-mod-expr freeradius3-mod-files freeradius3-mod-logintime freeradius3-mod-mschap freeradius3-mod-pap freeradius3-mod-preprocess freeradius3-mod-radutmp freeradius3-mod-realm freeradius3-mod-unix"
# in addition to the default packages, mod_rest is needed.
PKGLIST="$FR3_BASE_PKGS freeradius3-mod-rest"
# eventlet/greenlet requires python headers and gcc
PKGLIST="$PKGLIST python3 python3-pip python3-dev gcc"
# drop wpad-mini and use full wpad for enterprise WPA (https://medium.com/openwrt-iot/openwrt-setting-up-wpa-enterprise-3102a4ababec)
PKGLIST="$PKGLIST -wpad-mini wpad"
# for user disassociation support, use hostapd-utils (hostapd_cli).
# sudo isn't available by default, but needed to control which commands the module may run
# curl is needed to remove expired users via cronjob
PKGLIST="$PKGLIST hostapd-utils sudo curl"
# drivers for Ralink chipset supporting VLAN tagging (optional)
PKGLIST="$PKGLIST kmod-rt2800-usb"
# enlarge filesystem, cf. https://forum.openwrt.org/t/how-to-set-root-filesystem-partition-size-on-x86-imabebuilder/4765
make image PACKAGES="$PKGLIST" FILES=files/ CONFIG_TARGET_ROOTFS_PARTSIZE=512
