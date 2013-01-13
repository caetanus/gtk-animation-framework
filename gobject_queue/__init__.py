# -*- coding: utf-8 -*-

from gobject import io_add_watch, IO_IN, idle_add
import gtk
import gobject
from gtk import main as gtk_main
from threading import Thread, Condition, Event, RLock
import Queue as _Queue 
import socket as _socket
import random as _random

_main_run_event = Event()
_handler_genenartor_instance = None
_handlers = {}
_queue = None

class TimerError(Exception):
    pass

class _Timer(object):
    """
    a new gobject timer replacer, because the gobject timer on python really sux.
    """

    def __init__(self, timeout, callback=None, *user_data):
        self._timeout = timeout 
        self.cancel_event = Event()
        self._callback = None
        self.user_data = user_data

        if callback:
            self.callback = callback

    @property
    def callback(self):
        return self._callback
            
    @callback.setter
    def callback(self, callback):
        assert callable(callback)
        self._callback = callback 

    def start(self):
        
        if not self.callback:
            raise TimerError, 'a callback must be set.'

        def _timer():
            global _main_run_event
            _main_run_event.wait()
            while not self.cancel_event.wait(self._timeout):
                if self.user_data:
                    self.callback(*self.user_data)
                else:
                    self.callback()

        self.thread = Thread(target=_timer)
        self.thread.start()

    def cancel(self):
        print 'timer cancelled.'
        self.cancel_event.set()



def _handler_generator():
    handler_id = 0
    while 1:
        yield handler_id
        handler_id += 1
        handler_id %= 0xFFFFFFFF

def _get_handler():
    global _handler_genenartor_instance
    try:
        return _handler_genenartor_instance.next()
    except AttributeError:
        _handler_genenartor_instance = _handler_generator()
        return _get_handler()



def timeout_add_seconds(timeout, callback, *args):
    """
    works timeout_add from gobject, but timeout must be in seconds
    """

    global _handlers
    
    handler_id = _get_handler()
    timer = _Timer(timeout, None, handler_id, callback, *args)
    def middle_callback(handler_id, callback, *args):
        """
        this callback gets the callback from the timer threaded, then sends it to _GobjectQueue, to be schedulled to the gtk main loop.
        """
        

        global _queue
        if not _queue:
            _queue = _GobjectQueue()
        _queue.put((callback, args))

    timer.callback = middle_callback
    _handlers[handler_id] = timer
    timer.start()
    return handler_id

def timeout_add(timeout, callback, *args):
    """
    works as timeout_add from gobject
    """
    return timeout_add_seconds(timeout/1000, callback, *args)

def source_remove(handler_id):
    try:
        timer = _handlers[handler_id]
        timer.cancel()
        del _handlers[handler_id]
    except KeyError:
        raise TimerError, "timer doesn't exist"

def _cancel_all_timers():
    global _handlers

    for timer in _handlers.itervalues():
        timer.cancel()
    _handlers = {}


def main():
    """
    its actually is a patch to gtk.main, whenever a gtk.main is called, this function will take place
    """
    global _main_run_event
    global _queue 

    def start_queue():
        _queue = _GobjectQueue()
        return False

    def start_timers():
        _main_run_event.set()
        return False

    gobject.idle_add(start_queue)
    gobject.timeout_add(500,  start_timers)
    start_timers()
    gtk.gdk.threads_init()
    gtk.quit_add(0, _cancel_all_timers) 

    _main_run_event.set()
    gtk_main()
    _cancel_all_timers()



gtk.main = main
gtk.gtk_main = gtk_main

class _GobjectQueue(_Queue.Queue):

    def __init__(self, *args):
        self.callback = []
        while 1:
            try:
                """
                @todo: use pipes instead sockets for every SO that's not windows.
                """

                self.sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
                self.port = _random.randint(1025, 65534)
                self.sock.bind(("127.0.0.1", self.port))
                break

            except Exception, e:
                import traceback;
                traceback.print_exc()
                print e, type(e)
                continue
        io_add_watch(self.sock, IO_IN, self._on_data)
        _Queue.Queue.__init__(self, *args)

    def put(self, data):
        _Queue.Queue.put(self, data)
        self.sock.sendto('\0',self.sock.getsockname())
        #_socket.socket().connect(self.sock.getsockname())

    def get(self, *args, **kw):
        r = _Queue.Queue.get(self, timeout=0.01)
        return r

    def _on_data(self, *args):

        d, a = self.sock.recvfrom(1)
        if d != '\0' and a != self.sock.getsockname():
            return

        callback, args = self.get()
        try:
            callback(*args)
        except:
            pass

        return True

