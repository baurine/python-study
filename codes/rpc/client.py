# coding: utf-8
# server

import json
import time
import struct
import socket


def rpc(sock, in_, params):
    request = json.dumps({"in": in_, "params": params})
    print len(request)
    len_prefix = struct.pack("I", len(request))
    sock.sendall(len_prefix)
    sock.sendall(request)

    len_prefix = sock.recv(4)
    length, = struct.unpack("I", len_prefix)
    body = sock.recv(length)
    response = json.loads(body)
    print "res:", response
    return response["out"], response["params"]


def req():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("localhost", 8080))
    for i in range(10):
        out, result = rpc(s, "ping", "ireader %d" % i)
        print out, result
        time.sleep(1)
    s.close()


if __name__ == "__main__":
    req()
