#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# This runs the server, places a few requests and checks if the chat
# behaves as expected.
# Because UdpChat is used, everything can be checked with nc, curl and
# standard unix tools. You only need a "sleep" command which accepts
# fractional arguments (like GNU sleep).
#
# Note that the design of UdpChat (sending to the destination port and
# waiting for a response) requires a message to be sent by the server
# first, that is, a chat
#   <server>: Test
#   <host>: my answer
# would be: echo "my answer" | nc -ul 9999
# Every time a new nc call is placed, a message from the server has to
# arrive before the given response is sent back.

function quittest () {
    # use killall as killing the bg job doesn't shutdown the server
    killall gunicorn;
    wait %1;
    echo "server stopped";
    if [ $1 -ne 0 ]
    then
        echo ""
        echo "==== SERVER LOG OUTPUT ==="
        cat integration_test_server.log
        echo "======== END LOG ========="
    fi;
    rm integration_test_server.log
    rm test_curl.out
    exit $1
}

function do_post () {
    curl -X POST --header 'content-type: application/json' -d "$2" "http://localhost:5000/$1" -w "%{http_code}" >test_curl.out 2>/dev/null
}

function do_get () {
    curl "http://localhost:5000/$1" -w "\n%{http_code}" >test_curl.out 2>/dev/null
}

function authorize_req () {
    do_post "authorize" "$1"
    RETURN_STATUS=$(cat test_curl.out)
    if [ "$RETURN_STATUS" != "204" ]
    then
        echo "call: authorize with $1"
        echo "FAIL: Expected call to return 204 status, but was: $RETURN_STATUS"
        quittest 1
    fi;
}

function auth_mschap_base () {
    # dumped requests of a full PEAP-MSCHAP request. All of those should result in 204 status.
    authorize_req '{"User-Name": {"type": "string", "value": ["someone1"]}, "NAS-IP-Address": {"type": "ipaddr", "value": ["127.0.0.1"]}, "Service-Type": {"type": "integer", "value": [2]}, "Framed-MTU": {"type": "integer", "value": [1400]}, "Calling-Station-Id": {"type": "string", "value": ["02-00-00-00-00-01"]}, "NAS-Port-Type": {"type": "integer", "value": [19]}, "Event-Timestamp": {"type": "date", "value": ["Feb  4 2019 20:10:43 UTC"]}, "Connect-Info": {"type": "string", "value": ["CONNECT 11Mbps 802.11b"]}, "EAP-Message": {"type": "octets", "value": ["0x0200000c01736f6d656f6e65"]}, "Message-Authenticator": {"type": "octets", "value": ["0xa8e81c45b78baea0bde55b2b0f09aefa"]}}'
    authorize_req '{"User-Name": {"type": "string", "value": ["someone1"]}, "NAS-IP-Address": {"type": "ipaddr", "value": ["127.0.0.1"]}, "Service-Type": {"type": "integer", "value": [2]}, "Framed-MTU": {"type": "integer", "value": [1400]}, "State": {"type": "octets", "value": ["0x7a5c93507a5d97aa9c5cabcc691c9716"]}, "Calling-Station-Id": {"type": "string", "value": ["02-00-00-00-00-01"]}, "NAS-Port-Type": {"type": "integer", "value": [19]}, "Event-Timestamp": {"type": "date", "value": ["Feb  4 2019 20:10:43 UTC"]}, "Connect-Info": {"type": "string", "value": ["CONNECT 11Mbps 802.11b"]}, "EAP-Message": {"type": "octets", "value": ["0x020100060315"]}, "Message-Authenticator": {"type": "octets", "value": ["0x99475759265a3fda39e1afa745ef2540"]}}'
    authorize_req '{"User-Name": {"type": "string", "value": ["someone1"]}, "NAS-IP-Address": {"type": "ipaddr", "value": ["127.0.0.1"]}, "Service-Type": {"type": "integer", "value": [2]}, "Framed-MTU": {"type": "integer", "value": [1400]}, "State": {"type": "octets", "value": ["0x7a5c93507b5e86aa9c5cabcc691c9716"]}, "Calling-Station-Id": {"type": "string", "value": ["02-00-00-00-00-01"]}, "NAS-Port-Type": {"type": "integer", "value": [19]}, "Event-Timestamp": {"type": "date", "value": ["Feb  4 2019 20:10:43 UTC"]}, "Connect-Info": {"type": "string", "value": ["CONNECT 11Mbps 802.11b"]}, "EAP-Message": {"type": "octets", "value": ["0x020200b2150016030100a7010000a30303f46f48ca7175d115308cec903dfe389c0b4af5308635997a5fb7d48499f95ed9000038c02cc030009fcca9cca8ccaac02bc02f009ec024c028006bc023c0270067c00ac0140039c009c0130033009d009c003d003c0035002f00ff01000042000b000403000102000a000a0008001d0017001900180016000000170000000d0020001e060106020603050105020503040104020403030103020303020102020203"]}, "Message-Authenticator": {"type": "octets", "value": ["0xb6f301e952845855017e2873ba2c9ceb"]}}'
    authorize_req '{"User-Name": {"type": "string", "value": ["someone1"]}, "NAS-IP-Address": {"type": "ipaddr", "value": ["127.0.0.1"]}, "Service-Type": {"type": "integer", "value": [2]}, "Framed-MTU": {"type": "integer", "value": [1400]}, "State": {"type": "octets", "value": ["0x7a5c9350785f86aa9c5cabcc691c9716"]}, "Calling-Station-Id": {"type": "string", "value": ["02-00-00-00-00-01"]}, "NAS-Port-Type": {"type": "integer", "value": [19]}, "Event-Timestamp": {"type": "date", "value": ["Feb  4 2019 20:10:43 UTC"]}, "Connect-Info": {"type": "string", "value": ["CONNECT 11Mbps 802.11b"]}, "EAP-Message": {"type": "octets", "value": ["0x020300061500"]}, "Message-Authenticator": {"type": "octets", "value": ["0x760f95346d2bb47d879194c014aec0c3"]}}'
    authorize_req '{"User-Name": {"type": "string", "value": ["someone1"]}, "NAS-IP-Address": {"type": "ipaddr", "value": ["127.0.0.1"]}, "Service-Type": {"type": "integer", "value": [2]}, "Framed-MTU": {"type": "integer", "value": [1400]}, "State": {"type": "octets", "value": ["0x7a5c9350795886aa9c5cabcc691c9716"]}, "Calling-Station-Id": {"type": "string", "value": ["02-00-00-00-00-01"]}, "NAS-Port-Type": {"type": "integer", "value": [19]}, "Event-Timestamp": {"type": "date", "value": ["Feb  4 2019 20:10:43 UTC"]}, "Connect-Info": {"type": "string", "value": ["CONNECT 11Mbps 802.11b"]}, "EAP-Message": {"type": "octets", "value": ["0x0204008415001603030046100000424104b60124b412c9a26da15466632895c0d7d468abf86c52986b6229ba689637d88a07731310b08085cc076f11ff7ea9bcce222d91a74459a66f5044d1123c1b8c27140303000101160303002884b7228b0c5013f5979d037f6face76abf048466770d498cfcdd5b642c4d4b424edb7b2470b678bd"]}, "Message-Authenticator": {"type": "octets", "value": ["0xbe8f8f4333d745b0c867a01988f4dfc9"]}}'
    authorize_req '{"User-Name": {"type": "string", "value": ["someone1"]}, "NAS-IP-Address": {"type": "ipaddr", "value": ["127.0.0.1"]}, "Service-Type": {"type": "integer", "value": [2]}, "Framed-MTU": {"type": "integer", "value": [1400]}, "State": {"type": "octets", "value": ["0x7a5c93507e5986aa9c5cabcc691c9716"]}, "Calling-Station-Id": {"type": "string", "value": ["02-00-00-00-00-01"]}, "NAS-Port-Type": {"type": "integer", "value": [19]}, "Event-Timestamp": {"type": "date", "value": ["Feb  4 2019 20:10:43 UTC"]}, "Connect-Info": {"type": "string", "value": ["CONNECT 11Mbps 802.11b"]}, "EAP-Message": {"type": "octets", "value": ["0x020500371500170303002c84b7228b0c5013f63ea6825a185f84cbd609b6198b3b8bc556acf72a058d144d77ceaf7c57b48980106d6866"]}, "Message-Authenticator": {"type": "octets", "value": ["0xf43711dba158b1d5a8bb0026edd5b9b6"]}}'
    authorize_req '{"User-Name": {"type": "string", "value": ["someone1"]}, "NAS-IP-Address": {"type": "ipaddr", "value": ["127.0.0.1"]}, "Service-Type": {"type": "integer", "value": [2]}, "Framed-MTU": {"type": "integer", "value": [1400]}, "Calling-Station-Id": {"type": "string", "value": ["02-00-00-00-00-01"]}, "NAS-Port-Type": {"type": "integer", "value": [19]}, "Event-Timestamp": {"type": "date", "value": ["Feb  4 2019 20:10:43 UTC"]}, "Connect-Info": {"type": "string", "value": ["CONNECT 11Mbps 802.11b"]}, "EAP-Message": {"type": "octets", "value": ["0x0200000c01736f6d656f6e65"]}, "FreeRADIUS-Proxied-To": {"type": "ipaddr", "value": ["127.0.0.1"]}}'
    authorize_req '{"User-Name": {"type": "string", "value": ["someone1"]}, "NAS-IP-Address": {"type": "ipaddr", "value": ["127.0.0.1"]}, "Service-Type": {"type": "integer", "value": [2]}, "Framed-MTU": {"type": "integer", "value": [1400]}, "State": {"type": "octets", "value": ["0x7a5c93507f5a86aa9c5cabcc691c9716"]}, "Calling-Station-Id": {"type": "string", "value": ["02-00-00-00-00-01"]}, "NAS-Port-Type": {"type": "integer", "value": [19]}, "Event-Timestamp": {"type": "date", "value": ["Feb  4 2019 20:10:43 UTC"]}, "Connect-Info": {"type": "string", "value": ["CONNECT 11Mbps 802.11b"]}, "EAP-Message": {"type": "octets", "value": ["0x020600331500170303002884b7228b0c5013f7ddbf48c18b313a27af2b9ef07dd7a105f3254baad3c607687667b8daaef7fd56"]}, "Message-Authenticator": {"type": "octets", "value": ["0x9dfec08f2984dc86334d09dedd6bbf85"]}}'
    authorize_req '{"User-Name": {"type": "string", "value": ["someone1"]}, "NAS-IP-Address": {"type": "ipaddr", "value": ["127.0.0.1"]}, "Service-Type": {"type": "integer", "value": [2]}, "Framed-MTU": {"type": "integer", "value": [1400]}, "State": {"type": "octets", "value": ["0x6c65c03e6c64c4426854025643e60380"]}, "Calling-Station-Id": {"type": "string", "value": ["02-00-00-00-00-01"]}, "NAS-Port-Type": {"type": "integer", "value": [19]}, "Event-Timestamp": {"type": "date", "value": ["Feb  4 2019 20:10:43 UTC"]}, "Connect-Info": {"type": "string", "value": ["CONNECT 11Mbps 802.11b"]}, "EAP-Message": {"type": "octets", "value": ["0x02010006031a"]}, "FreeRADIUS-Proxied-To": {"type": "ipaddr", "value": ["127.0.0.1"]}}'
    authorize_req '{"User-Name": {"type": "string", "value": ["someone1"]}, "NAS-IP-Address": {"type": "ipaddr", "value": ["127.0.0.1"]}, "Service-Type": {"type": "integer", "value": [2]}, "Framed-MTU": {"type": "integer", "value": [1400]}, "State": {"type": "octets", "value": ["0x7a5c93507c5b86aa9c5cabcc691c9716"]}, "Calling-Station-Id": {"type": "string", "value": ["02-00-00-00-00-01"]}, "NAS-Port-Type": {"type": "integer", "value": [19]}, "Event-Timestamp": {"type": "date", "value": ["Feb  4 2019 20:10:43 UTC"]}, "Connect-Info": {"type": "string", "value": ["CONNECT 11Mbps 802.11b"]}, "EAP-Message": {"type": "octets", "value": ["0x0207006f1500170303006484b7228b0c5013f83ce100bc3a71a303b7c91d1f6b09d2cef63069584495e18886e51d56253dcd7cbf769d1afbe95dd0bba186b324fe6fa2ea2940bbcd85f97aca3aabbd270306ee6c95a8efd67e1cc1fb3166706dcbe7f659bf60ec8fc4849a2e70a05f"]}, "Message-Authenticator": {"type": "octets", "value": ["0xaa3a6a0887b5936c1329ca5d57452980"]}}'
}

function expect_return_status () {
    # first arg: status, second arg: additional message
    RCODE=$(tail -n 1 test_curl.out)
    if [ "$RCODE" != "$1" ]
    then
        echo "FAIL: Expected status $1, but was $RCODE $2"
        quittest 1
    fi;
}

# -- begin tests --

# start server in background.
bash ./run_server.sh integration_config.ini >integration_test_server.log 2>&1 &
echo "server started"

# wait up to 2 seconds for startup message
echo -n "Check if module started correctly... "
REPLY=$(nc -ul 9999 -w 2)
echo "$REPLY" | grep -i "module started" >/dev/null
if [ $? -ne 0 ]
then
    echo "FAIL: No startup message found."
    quittest 1
fi;
echo "OK"

# extract password
echo -n "Check if password was generated at startup... "
PW=$(echo $REPLY | sed -r "s/^.*Password: ([0-9]+).*$/\1/g")
echo $PW | grep -E "^[0-9]+$" >/dev/null
if [ $? -ne 0 ]
then
    echo "FAIL"
    quittest 1
fi;
echo "OK"

echo -n "Sending requests and allow test user via chat... "
# place requests which should be skipped
auth_mschap_base
# The last inner request has to be placed *after* nc listens for incoming messages.
# So run as bg job and add some delay.
JOIN_REQ='{"User-Name": {"type": "string", "value": ["someone1"]}, "NAS-IP-Address": {"type": "ipaddr", "value": ["127.0.0.1"]}, "Service-Type": {"type": "integer", "value": [2]}, "Framed-MTU": {"type": "integer", "value": [1400]}, "State": {"type": "octets", "value": ["0x6c65c03e6d67da426854025643e60380"]}, "Calling-Station-Id": {"type": "string", "value": ["02-00-00-00-00-01"]}, "NAS-Port-Type": {"type": "integer", "value": [19]}, "Event-Timestamp": {"type": "date", "value": ["Feb  4 2019 20:10:43 UTC"]}, "Connect-Info": {"type": "string", "value": ["CONNECT 11Mbps 802.11b"]}, "EAP-Message": {"type": "octets", "value": ["0x020200421a0202003d31d4be0420e5dccf090c848b3352323a9800000000000000000a3f830231cd77f8a28c98aae12d2e06c2856ddca1554c8600736f6d656f6e65"]}, "FreeRADIUS-Proxied-To": {"type": "ipaddr", "value": ["127.0.0.1"]}}'
(sleep 0.1 && do_post "authorize" "$JOIN_REQ") &

# expected chat:
#  server: someone wants to join ...
#  host: OK for 1 h
#  server: OK
REPLY=$(echo "OK for 1 h" | nc -ul 9999 -w 1)

# look for device ID and name
echo "$REPLY" | grep -i "someone1.*02-00-00-00-00-01.*" >/dev/null
if [ $? -ne 0 ]
then
    echo "FAIL: Host wasn't notified about join."
    quittest 1
fi;
# check if last "OK" is present
echo "$REPLY" | grep -i "^OK$" >/dev/null
if [ $? -ne 0 ]
then
    echo "FAIL: OK for 1 h reply wasn't accepted."
    quittest 1
fi;

# check response of HTTP request
expect_return_status 401 "after first request"
# end "Sending requests and allow ..."
echo "OK"

echo -n "Check if user gets accepted now... "
# place same requests again, but now the user should be allowed
auth_mschap_base
do_post "authorize" "$JOIN_REQ"

expect_return_status 200 "after accepting user"
grep "control:Cleartext-Password.*$PW" test_curl.out >/dev/null
if [ $? -ne 0 ]
then
    echo "FAIL: No password was returned after guest got allowed."
    quittest 1
fi;
echo "OK"

echo -n "Check if post-auth contains timeout... "
# check post-auth timeout attribute setting
do_post "post-auth" '{"User-Name": {"type": "string", "value": ["someone1"]}, "NAS-IP-Address": {"type": "ipaddr", "value": ["127.0.0.1"]}, "Service-Type": {"type": "integer", "value": [2]}, "Framed-MTU": {"type": "integer", "value": [1400]}, "State": {"type": "octets", "value": ["0x7a5c93507c5b86aa9c5cabcc691c9716"]}, "Calling-Station-Id": {"type": "string", "value": ["02-00-00-00-00-01"]}, "NAS-Port-Type": {"type": "integer", "value": [19]}, "Event-Timestamp": {"type": "date", "value": ["Feb  4 2019 20:10:43 UTC"]}, "Connect-Info": {"type": "string", "value": ["CONNECT 11Mbps 802.11b"]}, "EAP-Message": {"type": "octets", "value": ["0x0207006f1500170303006484b7228b0c5013f83ce100bc3a71a303b7c91d1f6b09d2cef63069584495e18886e51d56253dcd7cbf769d1afbe95dd0bba186b324fe6fa2ea2940bbcd85f97aca3aabbd270306ee6c95a8efd67e1cc1fb3166706dcbe7f659bf60ec8fc4849a2e70a05f"]}, "Message-Authenticator": {"type": "octets", "value": ["0xaa3a6a0887b5936c1329ca5d57452980"]}}'

grep "reply:Session-Timeout" test_curl.out >/dev/null
if [ $? -ne 0 ]
then
    echo "FAIL"
    quittest 1
fi;
echo "OK"

echo -n "Check if drop-expired is available... "
do_get "drop-expired"
expect_return_status 200 "for GET /drop-expired"
echo "OK"

echo "---"
echo "OK: Integration test passed"
quittest 0
