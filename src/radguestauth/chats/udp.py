# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import socket
from threading import Thread, Lock

from radguestauth.chat import Chat


class UdpChat(Chat):
    """
    Simple UDP-based chat adapter.
    """

    NET_HOST_IP = '127.0.0.1'
    NET_HOST_PORT = 9999
    RECV_TIMEOUT = 1

    def __init__(self):
        super(UdpChat, self).__init__()
        self._receive = lambda m: None
        self._quit = False
        self._sendbuf = None
        self._sendbuf_lock = Lock()
        self._thread = Thread(target=self._socket_thread)

    def startup(self, config):
        if not self._thread.is_alive():
            self._thread.start()

    def send_message(self, message):
        self._sendbuf_lock.acquire()
        if not self._sendbuf:
            self._sendbuf = str(message) + '\n'
        else:
            self._sendbuf += '\n' + str(message) + '\n'
        self._sendbuf_lock.release()

    def register_receive(self, receive_hook):
        self._receive = receive_hook

    def shutdown(self):
        self._quit = True
        self._thread.join()

    def _socket_thread(self):
        """
        Worker method running in a separate thread.

        It regularly checks if there is something to send and calls the receive
        hook when data arrives.
        """
        udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udpsocket.settimeout(self.RECV_TIMEOUT)

        while not self._quit:
            try:
                # Send data and clear send buffer afterwards.
                self._sendbuf_lock.acquire()
                if self._sendbuf:
                    udpsocket.sendto(self._sendbuf.encode(),
                                     (self.NET_HOST_IP, self.NET_HOST_PORT))
                    self._sendbuf = None
                self._sendbuf_lock.release()

                host_reply = udpsocket.recv(1024)
                # if nothing was received in the current timeframe, the
                # exception was thrown.
                # Otherwise, call the receive hook.
                if host_reply:
                    self._receive(host_reply.decode())
            except socket.timeout:
                pass
