# Running radguestauth on Raspberry Pi using OpenWrt

The `openwrt-config` subfolder contains several config files which will be used for
the OpenWRT image.

Note that the FreeRADIUS config does **not** include settings for the `radguestauth`
module. Instead, they are maintained in the respective Ansible task in `../config` to
avoid duplication. The Ansible task makes it easier to use the module in other setups, such as the
Vagrant development environment.
The changes here only disable some authentication methods, and enable EAP-PWD.

## Build and run an image

Currently, some manual steps are necessary.

1. Cf. `build-freeradius.md` in this directory on how to create
   custom OpenWRT packages for FreeRADIUS. This requires the OpenWRT SDK for
   Raspberry.
2. Use `build.sh` and the imagebuilder (link in script comments) to prepare the
   system image. You will likely need to adjust the WAN IP address in
   `etc-config/network`. Your SSH key is copied into `authorized_keys` automatically.
   Make sure `../src/config.ini` exists and contains the respective XMPP server credentials. You can use
   `../src/example_config.ini` as starting point.
3. Flash the image in `bin/targets/brcm2708/bcm2710/openwrt-18.06.1-brcm2708-bcm2710-rpi-3-ext4-factory.img.gz`
4. Adjust the Ansible inventory in `../config` such that the IP matches the
   WAN IP of your raspberry. Then boot the Raspberry and use `run-ansible.sh`
   to install required python dependencies and to configure FreeRADIUS.
5. The module should boot and you should receive a chat message. It is now ready to use.
6. For development, you can use the `update-radguestauth.sh` script. It builds a new python wheel and uploads it to the Raspberry.