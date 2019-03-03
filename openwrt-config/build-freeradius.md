# Building FreeRADIUS packages

1. Get the OpenWRT SDK for raspberry
    * https://openwrt.org/docs/guide-developer/using_the_sdk
    * https://downloads.openwrt.org/releases/18.06.1/targets/brcm2708/bcm2710/
2. make sure LC_ALL is set, otherwise the SDK won't work (tested Ubuntu 18.04), cf. https://github.com/mikma/lxd-openwrt/issues/2
3. Follow the instructions in the OpenWRT wiki to update package feeds and obtain freeRADIUS sources
4. modify the `freeradius3` package Makefile (located in `feeds/packages/net/freeradius3`) by copying the `freeradius-Makefile` there. The following changes were made:
    * Make EAP-PWD available, so applied <https://github.com/openwrt/packages/commit/bb7b3204e05fa1e3d0505ad039e53b2a385a11ad> as it was included after the 18.06 release.
    * Provide new package for `rlm_rest`
5. In `make menuconfig`, select the new rest package and disable package index signing
6. `make package/freeradius3/compile`
7. `make package/index`
8. Add full path to `openwrt-sdk/bin/packages/aarch64_cortex-a53/packages` to `repositories.conf` in the imagebuilder directory
