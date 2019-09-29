# coding: utf-8
# server

import json
import struct
import socket
import asyncore
from cStringIO import StringIO


class RPCHandler(asyncore.dispatcher_with_send):  # 继承自 asyncore.dispatcher_with_send
    def __init__(self, sock, addr):
        asyncore.dispatcher_with_send.__init__(self, sock=sock)
        self.addr = addr
        self.handlers = {
            "ping": self.ping,
            "fab": self.fab
        }
        self.rbuf = StringIO()  # 读缓冲区

    def handle_connect(self):
        print self.addr, "comes"

    def handle_close(self):
        print self.addr, "bye"
        self.close()

    def handle_read(self):
        print "handle_read"
        while True:
            content = self.recv(1024)
            if content:
                self.rbuf.write(content)
            if len(content) < 1024:
                break
        self.handle_rpc()

    def handle_rpc(self):  # 解包，可能一次收到多个请求
        print "handle_rpc"
        while True:
            self.rbuf.seek(0)
            length_prefix = self.rbuf.read(4)
            if len(length_prefix) < 4:
                break
            length, = struct.unpack("I", length_prefix)
            body = self.rbuf.read(length)
            if len(body) < length:
                break
            request = json.loads(body)
            in_ = request['in']
            params = request['params']
            print in_, params
            handler = self.handlers[in_]
            handler(params)
            left = self.rbuf.getvalue()[length + 4:]
            self.rbuf = StringIO()
            self.rbuf.write(left)
        self.rbuf.seek(0, 2)

    def ping(self, params):
        self.send_res("pong", params)

    def fab(self, params):
        self.send_res("fab_res", params)

    def send_res(self, out, params):
        response = {"out": out, "params": params}
        body = json.dumps(response)
        length_prefix = struct.pack("I", len(body))
        self.send(length_prefix)
        self.send(body)


class RPCServer(asyncore.dispatcher):
    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(1)

    def handle_accept(self):
        pair = self.accept()
        print pair
        if pair is not None:
            sock, addr = pair
            RPCHandler(sock, addr)


if __name__ == "__main__":
    RPCServer("localhost", 8080)
    asyncore.loop()
