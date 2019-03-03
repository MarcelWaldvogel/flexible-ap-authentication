# Flexible AP Authentication with FreeRADIUS and XMPP

radguestauth is a software which allows flexible WiFi guest management via chat.
It is connected with a FreeRADIUS server using REST.

Chat backends can be added easily, XMPP is the main chat protocol at the
moment. For testing purposes, there also is an UDP-based chat included.
You can interact with it via `nc -ul 9999`.

This repository provides a development VM based on Vagrant and an all-in-one
system based on OpenWRT and Raspberry Pi 3 B.

## The radguestauth server

The main logic is located in `src`. The Makefile provides some convenient
commands to install dependencies and run tests. You can either use the test
VM described below or run the module locally.

The VM already installs everything which is needed to run and test the module.
You can skip the following sections and proceed with *Development VM* if you
don't want to configure your own environment.

To set up Python dependencies, use ˋmake devsetupˋ.
Unit and integration tests can be run with ˋmake testˋ.

### Server configuration

The REST radguestauth server can be configured via an ini-File.
You can specify a custom path via the environment variable
`RADGUESTAUTH_CONFIG`. See `run_server.sh` for details on running the
server.

As default, a `config.ini` in the `src` directory is used. You can start by
copying `example_config.ini`. It contains all values which can be configured.

All items are located under the `[radguestauth]` key.

* `chat`: xmpp or udp
* `chat_user`, `chat_password`: Chat credentials, ignored for UDP
* `chat_recipient`: The user to whom messages are sent, ignored for UDP
* `xmpp_use_tls`: yes or no
* `generate_password_on_startup`: yes or no; whether the `pass` command should
  be run on startup. The guests will have to enter this password. If this is
  set to no, the password will be empty until `pass` is executed via chat.
  The recommended value is yes.
* `auth_handler`: The class which determines the behavior for authentication.
    - The default config rejects users until they are allowed and should work
  with any AP.
    - The `Vlan` handler uses 802.1q dynamic VLAN assignment.
      *It is currently intended to be used on the Raspberry Pi setup.*

### FreeRADIUS configuration

You can use the config files provided in the `config` directory. Key points:

* Enable `mod_rest` in the default site and the inner tunnel's `authorize`
  sections
* Set `copy_request_to_tunnel = yes` for EAP and TTLS, such that all attributes
  are available in the inner requests

`mod_rest` config (excerpt):

```
connect_uri = "http://127.0.0.1:5000" # where your radguestauth server runs

# -- TLS config and more --

authorize {
  uri = "${..connect_uri}/authorize"
  method = 'post'
  body = 'json'
  tls = ${..tls}
}
```

If you plan to use 802.1q VLAN tagging, you'll also have to enable `post-auth`.

Extend `mod_rest` by

```
post-auth {
  uri = "${..connect_uri}/post-auth"
  method = 'post'
  body = 'json'
  tls = ${..tls}
}
```

* Enable `mod_rest` in the default site's `post-auth` section

### Remove expired users

As guest users stay in the list of known users even after the permissions expired (they
get updated when they want to join again), regularly removing old entries can be helpful.

For this purpose, a REST endpoint `/drop-expired` is available via GET.
You can run a regular cron job, for instance.

Note that there is no security risk from not calling this - your user list will just
get cluttered over time.

## Development VM

Using Vagrant, this sets up an Ubuntu 18.04 VM with FreeRADIUS configured such
that it can be used as if the RADIUS server would run on your machine.

That is, you can use your machine's IP address in an AP config. The
server listens on the default port 1812.
It has been successfully tested with a TP-Link TL-WR841N running the default firmware.

Note that the setup based on Raspberry Pi offers an easier choice to test with
physical devices. Nevertheless, the VM is useful to test all components locally.

### Running the test server

To test the application:

* Start the VM with `vagrant up`
* all dependencies are installed automatically.
* After boot, run `vagrant ssh` in three shells (all commands are interactive)
  to execute commands inside the VM in the following order:
  * `profanity` - XMPP CLI client
    * Inside Profanity: `/connect test@localhost`, password is `test`
    * `/msg guestauth@localhost`
  * `bash /vagrant/src/run_server.sh` - REST server
  * `sudo freeradius -X` - needs the above server running

Now you can either use `eapol_test` (see below) or configure an AP.

Enter `help` in the chat to see available commands. At startup, a password
is generated and sent via chat. This is the password the guests will have to
enter. Use `pass` to generate a new one.

### Test Credentials

The test config given in this setup uses the following settings:

* Any incoming client is allowed (due to VirtualBox NAT)
* The RADIUS secret is `radius`

### Testing within the VM

`./eapol-testfiles` contains test configs for the `eapol_test` utility
(installed in the VM, this folder is mounted to `/vagrant`).
They are based on the files from [Deploying Radius](http://deployingradius.com/scripts/eapol_test/).

You will have to modify the password accordingly.

The `eapol_test` tool allows to run requests against FreeRADIUS like "real devices"
with `wpa_supplicant` place them.

## All-in-one box based on OpenWRT and Raspberry Pi

You can set up your own guest AP using a Raspberry Pi 3B. If you wish to assign guests to VLANs instead of relying on the Firewall, you'll need an additional WiFi USB adapter with a chipset supporting 802.1q VLAN tagging.

### Getting it up and running

Please refer to the instructions in `openwrt_config` for details.

A base image is built using the SDK, which is then configured using Ansible on first boot.

To access the box, you need an RSA SSH keypair (the onboard ˋdropbearˋ server doesn't support ECDSA keys out of the box) in your home directory. The public key is added to the base image at build time.

Additionally, an external XMPP server is necessary. All other components are ready to use and configured accordingly.

### On-board wireless

You need to use the ˋFirewallAuthHandlerˋ, as the on-board wireless adapter isn't capable to assign VLAN tags. New guests are in the same network as allowed guests, but do not have connectivity. As soon as they are allowed, a firewall exception is added.

### Assigning VLANs

More secure than relying on firewall rules is using two separate networks without and with connectivity.

To use the ˋVlanAuthHandlerˋ, an additional USB WiFi dongle is needed. It is important that the chipset's driver supports VLAN tagging. A suitable driver is e.g. [Ralink RT5370](https://www.raspberrypi.org/forums/viewtopic.php?t=175236).

## System Requirements for the Different Variants

### All environments

* Python 3.6 or newer

### FirewallAuthHandler and VlanAuthHandler

* hostapd_cli to disassociate users

### FirewallAuthHandler only

* bash
* UCI/OpenWRT Firewall environment

### Development Environment

* Vagrant

If you like to run the module and tests locally

* Linux system, very likely other *nix systems work as well
* bash
* make
* pip3
* curl
* netcat/nc

### OpenWRT Setup

* Ansible to setup the Raspberry Pi
* bash
* make
* OpenWRT SDK for Raspberry Pi 3 and its Requirements
* OpenWRT imagebuilder for Raspberry Pi 3 and its Requirements