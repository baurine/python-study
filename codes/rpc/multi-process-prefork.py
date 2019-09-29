# coding: utf-8
# server

import json
import struct
import socket
import thread
import os


def prefork(n):
    for _ in range(n):
        pid = os.fork()
        if pid < 0:
            return
        elif pid > 0: # 父进程
            continue  # 父进程继续循环，创建剩余的子进程
        else: # pid == 0，子进程
            break # 子进程退出循环，否则会继续创建更多子进程，直到系统资源耗尽


def loop(sock, handlers):
    while True:
        conn, addr = sock.accept()
        handle_conn(conn, addr, handlers)


def handle_conn(conn, addr, handlers):
    print addr, "comes"
    while True:
        len_prefix = conn.recv(4)
        if not len_prefix:
            print addr, "bye"
            conn.close()
            break
        length, = struct.unpack("I", len_prefix)
        print length
        body = conn.recv(length)
        request = json.loads(body)
        in_ = request["in"]
        params = request["params"]
        print in_, params
        handler = handlers[in_]
        handler(conn, params)


def ping(conn, params):
    send_result(conn, "pong", params)


def cal_fab(times):
    a, b = 1, 2
    i = 0
    while i < times:
        i = i + 1
        a = a + b
        tmp = b
        b = a
        a = tmp
    return a


def fab(conn, params):
    send_result(conn, "fab_res", cal_fab(params))


def send_result(conn, out, params):
    body = json.dumps({"out": out, "params": params})
    len_prefix = struct.pack("I", len(body))
    conn.sendall(len_prefix)
    conn.sendall(body)


def start():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET,
                    socket.SO_REUSEADDR,
                    1)  # 打开 reuse addr 选项
    sock.bind(("localhost", 8080))
    sock.listen(1)
    prefork(10)
    handlers = {
        "ping": ping,
        "fab": fab
    }
    loop(sock, handlers)


if __name__ == "__main__":
    start()
