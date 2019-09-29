import time
import signal


def ignore(sig, frame):
    pass


signal.signal(signal.SIGINT, ignore)

while True:
    print "hello"
    time.sleep(1)
