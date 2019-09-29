# 《深入理解 RPC : 基于 Python 自建分布式高并发 RPC 服务》Note

掘金小册 - [《深入理解 RPC : 基于 Python 自建分布式高并发 RPC 服务》](https://juejin.im/book/5af56a3c518825426642e004) 一书的笔记。

[示例代码](https://github.com/pyloque/juejin_rpc_py)

其实我觉得这本书重点不是 RPC，而是高并发，一步步讲解 python 如何使用多进程 + 异步 io 模式来处理大量客户端的请求，倒也学习到不少，有点温习《UNIX 环境高级编程》一书的感觉。

PRC vs REST：REST 基于 http + json 的协议，用于服务端和客户端之间通信，而 RPC 一般基于 tcp，自定协议，可以用文本或者二进制，一般用于内网机器之间，同一台机器的进程之间通信。

## 开篇：RPC 要解决的核心问题和在企业服务中的地位

略。

## 基础篇：深入理解 RPC 交互流程

略。

## 协议 1：深入 RPC 消息协议

略。

## 协议 2：Redis 文本协议结构

RESP 协议，一个比较简单直观的文本协议。

Redis 协议将传输的结构数据分为 5 种最小单元类型，单元结束时统一加上回车换行符号 `\r\n`。

- 单行字符串以 `+` 符号开头；
- 多行字符串 以 `$` 符号开头，后跟字符串长度；
- 整数值 以 `:` 符号开头，后跟整数的字符串形式；
- 错误消息 以 `-` 符号开头；
- 数组以 `*` 号开头，后跟数组的长度；

## 协议 3：Protobuf 二进制协议结构

一种二进制协议，提高传输效率。

## 协议 4：Redis 协议的缺陷

略。

## 客户端：深入 RPC 客户端设计

略。

## 服务器 1：【单线程同步】模型

略。最简单的模式，只能同时处理一个连接。

本小册的例子定义了一种非常简单的 RPC 协议，最开头的 4 byte 是内容的长度，后面的内容使用 json 格式编码。

客户端和服务端发送数据时，先将内容 dump 成 json，再计算其长度，然后先发送长度，再发送 json body。

接收时，先接收 4 byte，解析得到后面内容的长度，再接收相应长度的数据并反解析 json。

## 服务器 2：【多线程同步】模型

每来一个连接，生成一个线程处理这个连接。

```python
def loop(sock, handlers):
    while True:
        conn, addr = sock.accept()
        thread.start_new_thread(handle_conn, (conn, addr, handlers))  # 开启新线程进行处理，就这行代码不一样
```

## 服务器 3：【多进程同步】模型

> 但是 Python 里多线程使用的并不常见，因为 Python 的 GIL 致使单个进程只能占满一个 CPU 核心，多线程并不能充分利用多核的优势。所以多数 Python 服务器推荐使用多进程模型。

使用系统调用 os.fork() 复制进程。通过返回值 pid 匹分父进程还是子进程。

```python
pid = os.fork()
if pid > 0:
    # 在父进程中，且 pid 为子进程的进程号
if pid == 0:
    # 在子进程中
if pid < 0:
    # 发生错误
```

核心代码，每来一个连接，fork 一个进程处理。

```python
def loop(sock, handlers):
    while True:
        conn, addr = sock.accept()
        pid = os.fork()  # 好戏在这里，创建子进程处理新连接
        if pid < 0:  # fork error
            return
        if pid > 0:  # parent process
            conn.close()  # 关闭父进程的客户端套接字引用
            continue
        if pid == 0:
            sock.close()  # 关闭子进程的服务器套接字引用
            handle_conn(conn, addr, handlers)
            break  # 处理完后一定要退出循环，不然子进程也会继续去 accept 连接
```

## 服务器 4：【PreForking 同步】模型

为每一个连接都 fork 一个进程是不现实的。只能 fork 出有限个进程。

我们提前 fork 出 10 个进程，然后让这个 10 个进程同时监听连接，如果有新的连接到来，空闲的进程会争抢处理这个连接，但只有一个进程能成功抢到机会。

核心代码：

```python
//...

def loop(sock, handlers):
    while True:
        conn, addr = sock.accept()
        handle_conn(conn, addr, handlers)

def prefork(n):
    for i in range(n):
        pid = os.fork()
        if pid < 0:  # fork error
            return
        if pid > 0:  # parent process
            continue
        if pid == 0:
            break  # child process

if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("localhost", 8080))
    sock.listen(1)
    prefork(10)  # 好戏在这里，开启了 10 个子进程
    handlers = {
        "ping": ping
    }
    loop(sock, handlers)
```

## 服务器 5：【单进程异步】模型

使用单进程加上非阻塞 io，使用封装好的异步库 asyncore。

非阻塞 io 实际还是同步操作。

对于阻塞 io，我们调用 `read(10)` 时，它会从 io 那直到读取 10 个字节才返回，否则就在那一直等 io 就绪；调用 `write("hello")` 时，它会从 io 那直到所有内容都发送完成时才返回，否则就那一直等待。

而对于非阻塞 io，当我们调用 `read(10)` 时，它只会尝试从 io 那读取当前能读取的内容并马上返回，有可能只能读到 1 个字节，那它也直接返回，而不是在那一直等到 10 个字节，所以它的返回值就表示实际读到多少个字节；而调用 `write("hello")`，它也是只尽力发送内容，有可能只能发送一部分，发送完这次后就马上返回了，而不是一直等到所有内容发送完毕。

所以，对于非阻塞式 io，我们一般还需要手动循环去多次读取，直接读到我们想要的长度，或多次发送，直接所有内容都发送完毕。

操作系统提供了 select / epoll 这样的轮循 api。

本节例子看代码，详略。

需要再次总结 同步/异步/阻塞/非阻塞的区别。

我现在的理解，同步/异步是针对 cpu 而言，而阻塞/非阻塞是针对 io 而言。像 js 的异步编程模式，其实和阻塞/非阻塞没有关系。promise 不管你是纯计算还是处理 io，对于 cpu 而言都是异步的。

## 服务器 6：【PreForking 异步】模型

fork 出的每个进程都采用异步模式。

详略。

## 服务器 7：【多进程描述符传递】模型

fork 出多个进程后，让多个进程同时监听 socket 并抢着处理连接，导致的一个问题是，忙的进程会很忙，而闲的进程会很闲，不能平均分配。

另一种方式，则 master 进程统一接收连接，然后将连接平均地交给 worker 进程处理。进程间如何通信，使用 sendmsg 和 recvmsg 系统调用，底层是使用 unix 域套接字，unix 域套接字只能在同一个机器的不同进程之间传递消息。

(本小节的例子采用了 python3，其余都是 python2)

## 分布式 1：深入 RPC 分布式原理

使用 zookeeper 作为服务发器，多个服务端都注册到 zookeeper 中，客户端从 zookeeper 中读取服务器列表，随机或按照某些策略从中选择一个服务器进行 rpc 调用。

## 分布式 2：分布式 RPC 知识基础

(大篇幅是在讲如何设计一个良好的单机多进程服务端程序...)

信号：

- SIGINT：按下 ctrl + c 时，向进程发送 SIGINT 信号，默认是退出，你可以在程序里重写它的处理函数
- SIGTERM：在命令行调用 `kill pid` 时，向进程发送 SIGTERM 信号，默认是退出，你可以在程序里重写它的处理函数
- SIGKILL：在命令行调用 `kill -9 pid` 时，向进程发送 SIGKILL 信号，程序退出，不可重写它的处理函数

其它一些信号：

- SIGCHLD：子进程退出时，父进程会收到这个信号。当子进程退出后，父进程必须通过 waitpid 来收割子进程，否则子进程将成为僵尸进程，直到父进程也退出了，其资源才会彻底释放。

重写信号处理函数，使用 `signal.signal(sig, handler)` 方法，比如重写 SIGINT 的处理函数，用来忽略它。

```python
import time
import signal

def ignore(sig, frame):  # 啥也不干，就忽略信号
    pass

signal.signal(signal.SIGINT, ignore)

while True:
    print "hello"
    time.sleep(1)
```

执行这个函数后，按下 `ctrl + c` 后，程序不会退出，但 `ctrl + c` 会打断 `time.sleep(1)` 的执行。

一个进程可以通过 `os.kill()` 向指定进程发送信号：

```python
os.kill(pid, signal.SIGKILL)
os.kill(pid, signal.SIGTERM)
os.kill(pid, signal.SIGINT)
```

**错误码**

python 的 errono 包定义了很多操作系统调用错误码。比如 errno.EINTR 表示调用被打断，代码遇到此种错误时往往需要进行重试。还有 errno.ECHILD 在 waitpid 收割子进程时，目标进程不存在，就会有这样的错误。

(python 相比 ruby 好的一点在于，它封装了很多 os 层的系统调用，而且和 c 代码很相似，因此能很方便地将一些 c 代码改写成 python，但 ruby 这方面的库比较欠缺)

**收割子进程 (收割？应该就是回收子进程的资源吧)**

收割子进程使用 `os.waitpid(pid, options)` 系统调用，可以提供具体 pid 来收割指定子进程，也可以通过参数 pid=-1 来收割任意子进程。

options 如果是 0，就表示阻塞等待子进程结束才会返回，如果是 WNOHANG 就表示非阻塞，有，就返回指定进程的 pid，没有，就返回 0。

waitpid 有可能抛出异常，如果指定 pid 进程不存在或者没有子进程可以收割，就会抛出 OSError(errno.ECHILD)，如果 waitpid 被其它信号打断，就会抛出 OSError(errno.EINTR)，这个时候可以选择重试。

父进程退出时，要手动关闭所有 fork 出来的子进程，通过使用 `os.kill(pid, sig)` 系统调用，然后之后还要 waitpid 收割子进程。(如果 `os.kill()` 是阻塞式地 kill，还需要 waitpid 吗？)

系统处理函数有可能被其它信号所打断，因此执行到一半时会去执行其它信号处理函数... (有可能产生重入的风险) 然后再回来处理剩下的逻辑。

服务发现：zookeeper，详略。

## 分布式 3：分布式 RPC 实战

加上了服务端处理信号，向 zookeeper 进行注册，以及客户端从 zookeeper 获取服务器列表，从中挑选一个进行 rpc 通信的逻辑。

这一小节需要安装 zookeeper 并运行 zookeeper 服务。使用封装好的 kazoo 库来和 zookeeper 服务通信。

```shell
$ pip install kazoo

$ docker pull zookeeper
$ docker run -p 2181:2181 zookeeper
```

## 拓展 1：gRPC 原理与实践

gRPC 基于 Protobuf 和 http 2.0。

http 2.0，所有请求复用一条连接，流式，请求并行，帧 ...

使用 gRPC 实现计算圆周率的步骤：

1. 编写协议文件 pi.proto
1. 使用 `grpc_tools` 工具将 pi.proto 编译成 `pi_pb2.py` 和 `pi_pb2_grpc.py` 两个文件
1. 使用 `pi_pb2_grpc.py` 文件中的服务器接口类，编写服务器具体逻辑实现
1. 使用 `pi_pb2_grpc.py` 文件中的客户端 Stub，编写客户端交互代码 (直接调用生成的方法即可，超级方便)
1. 分别运行服务器和客户端，观察输出结果

其余略。

## 拓展 2：Thrift 原理与实践

和 gRPC 差不多原理，比 gRPC 支持更多协议，比如支持文本协议，但 gRPC 只支持二进制。
