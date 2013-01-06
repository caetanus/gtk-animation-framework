# -*- coding: utf-8 -*-
"""


  Event Library very similar to gobject/glib/GIO, but pure python
  author: Marcelo Aires Caetano
  date: 15 apr 2012, 27 apr 2012
  email: marcelo@fiveti.com

  this module tryes to implement all gobject functions,
  except the functions concerning to types, because python already has strong
  types, and the gobject types was made to be used in c, not in python


This module must be tread safe, so, the timers must call queues to be executed
in the main thread, ok?
the MPAssyncQueue will be used by sockets and will only work with the main method
"""
import time as _time
import socket as _socket
import Queue as _Queue
import traceback as _traceback
import random as _random
import threading as _threading
from gobject import io_add_watch, IO_IN
import gtk 
from threading import Lock

_timer_lock = Lock()
_main_running = False

class _Timer(object):
    def __init__(self, interval, function, args=()):
        self.interval = interval
        self.function = function
        self.args = args
        self.running = False
        self.queue = _Queue.Queue()
        self.queue_continue = _Queue.Queue()

    def start(self):
        print "timer started."
        def timer(interval, function, args, queue, queue_cont):
            self.running = True
            while 1:
                try:
                    queue.get(timeout=interval)
                    break
                except _Queue.Empty:
                    try:
                        function(*args)
                    except:
                        print _traceback.print_exc()
                    if not queue_cont.get():
                        break
            self.running = False
        t = _threading.Thread(target=timer, name='timer', args=(self.interval,
                                                           self.function,
                                                           self.args,
                                                           self.queue,
                                                           self.queue_continue))
        t.start()
    def cont(self):
        self.queue_continue.put(1)

    def cancel(self):
        if self.running:
            self.queue.put(1)
            self.queue_continue.put(0)

__all__ = ['timeout_add', 'timeout_add_seconds', 'main', 'source_remove' ]
_queue = None
_timeout_add_list = []


_handlers = {}
_handler_id = 0
_io_handlers = {}
_io_handlers_fd = {}
_idle_handlers = {}

def _get_all_timers():
    global _handlers
    for i in _handlers.keys():
        try:
            _handlers[i].join
            assert _handlers[i].isAlive()
            assert not _handlers[i].isFinished()
            yield _handlers[i]
        except:
            pass

    

def _timeout_add(miliseconds, callback, source=None, *args):
    """
    for internal use.
    mock's gobject timeout_add and returns a timer as a handler
    """

    global _handler_id
    global _handlers
    global _queue
    global _timer_lock
    global _main_running

    if source == None:
        _handler_id += 1
        source = _handler_id

    seconds = miliseconds / 1000.
    def cb1(callback, source, *args):
        global _handlers
        with _timer_lock:
            if source in _handlers:
                if callback(*args) == True:
                    _timeout_add(miliseconds, callback, source, *args)

    def cb():
        """
        used queues to the timer be executed into the same thread
        that's hes called.
        """
        print 'cb is called.'

        _queue.put((cb1, callback, source, args))

    if _main_running: 
        try:
            with _timer_lock:
                t = _handlers[source]
                t.cont()
        except:
            with _timer_lock:
                t = _Timer(seconds, cb)
                _handlers[source] = t
                print 'timer started.'
                t.start()

    else:
        global _timeout_add_list
        with _timer_lock:
            _timeout_add_list.append((seconds,cb, source))
            _handlers[source] = -1

    return source

def timeout_add_seconds(interval, callback, *args):

    """
    the same of timeout_add, but interval is specified in seconds/s
    """

    return timeout_add(int(interval * 1000.), callback, *args)

def timeout_add(interval, callback, *args):
    """

    the gobject_fake.timeout_add() function (specified by callback) to be 
    called at regular intervals (specified by interval). Adittional arguments
    to pass to callback canb e specified after callback.
 
    The function is called repeatedly until it returns False, at which point
    the timeout is automatically destroyed and the function will not be
    called again. THe first call to the function will be at the end of the
    first interval. Note that timeout functions may be deleayed, due to the
    processing of other event sources. Thus they should be relied on for
    precise timing. After each call to the timeout function, the time of next
    timeout is recalculated based on the currente time and the given interval
    (it does not try to 'catch up' time lost in delays).

    interval: the time between calls to the function, in milliseconds
    callback: the function to call
    *args:    zero or more arguments that will be passed to callback

    Retruns: an intenger ID of the event source

    """

    return _timeout_add(interval, callback, None, *args)

def source_remove(tag):
    """
    mocks's gobject source_remove

    The gobject_fake.source_remove() function removes the event source 
    specified by tag (as returned by the timeout_add() and io_add_watch())

    handler: an Integer ID
    Returns: True if the event source was removed
    """
    global _handlers
    global _timer_lock

    try:
        with _timer_lock:
            if tag in _handlers:
                if _handlers[tag] != -1:
                    _handlers[tag].cancel()
                del _handlers[tag]
                return True

        return False

    except Exception, e:
        print e, type (e), "<--- source remove"
        print _traceback.print_exc()
        return False


def main():
    global _handlers
    global _queue
    global _timeout_add_list
    global _timer_lock
    global _main_running
    _main_running = True

    if not _queue:
        _queue = _GobjectQueue()
    
    def on_queue_callback(queue):
        print 'queue callback.'
        cb1, callback, source, args = _queue.get()
        cb1(callback, source, *args)
        return True

    _queue.callback.append(on_queue_callback)

    #starting hanged timers
    with _timer_lock:
        for i in _timeout_add_list:
            seconds, cb, source = i
            t = _Timer(seconds, cb)
            t.start()
            _handlers[source] = t
        _timeout_add_list = []


    gtk.main()
    _main_running = False
    _cancel_all_timers(1)

def _cancel_all_timers(command=0):
    global _handlers
    global _timer_lock

    with _timer_lock:
        for source in _handlers:
            try:
                seconds = _handlers[source].interval
                cb = _handlers[source].function
                _handlers[source].cancel()
            except Exception, e:
                pass#print e, type(e)

            if command:
                # if the timer was stopped by a ctrl+c, so when main is called again
                # the timer will reborn.
                global _timeout_add_list
                _timeout_add_list.append((seconds,cb, source))



class _GobjectQueue(_Queue.Queue):


    def __init__(self, *args):
        self.callback = []
        self.sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        while 1:
            try:
                """
                @todo: use pipes instead sockets for every SO that's not windows.
                """
                self.port = _random.randint(1025, 65534)
                self.sock.bind(("127.0.0.1", self.port))
                break
            except Exception, e:
                print e, type(e)
                continue
        io_add_watch(self.sock, IO_IN, self._on_data)
        _Queue.Queue.__init__(self, *args)

    def put(self, data):
        _Queue.Queue.put(self, data)
        self.sock.sendto('\0',self.sock.getsockname())

    def get(self, *args, **kw):
        r = _Queue.Queue.get(self, timeout=0.1)
        return r

    def _on_data(self, *args):
        d, a = self.sock.recvfrom(1)
        if d != '\0' and a != self.sock.getsockname():
            return

        for i in self.callback:
            try:
                i(self)
            except:
                pass
        return True

