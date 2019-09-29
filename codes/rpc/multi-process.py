# coding: utf-8
# server

import json
import struct
import socket
import thread
import os


def loop(sock, handlers):
    while True:
        conn, addr = sock.accept()
        # handle_conn(conn, addr, handlers)
        # thread.start_new_thread(handle_conn, (conn, addr, handlers))
        pid = os.fork()
        if pid < 0:  # fork error
            return
        elif pid > 0:  # parent process
            conn.close()  # close it
            continue
        else:  # pid == 0
            sock.close()  # 子进程必须关闭 sock
            handle_conn(conn, addr, handlers)
            break  # 子进程处理完 conn 后必须退出，否则它也会去 accept()，注意，虽然前面 close 了 sock，但 sock 只是减少了引用，并没有真正关掉


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
    handlers = {
        "ping": ping,
        "fab": fab
    }
    loop(sock, handlers)


if __name__ == "__main__":
    start()
