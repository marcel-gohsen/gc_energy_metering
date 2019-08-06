import abc
import threading
import time


class Listener(metaclass=abc.ABCMeta):
    def __init__(self):
        self.is_paused = False
        self.thread = ListeningThread(self)
        self.is_listening = False

    def start(self):
        self.is_listening = True
        self.thread.start()

    @abc.abstractmethod
    def __listen__(self):
        pass

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.is_listening = False

    @abc.abstractmethod
    def get_data(self):
        pass


class ListeningThread(threading.Thread):
    def __init__(self, listener):
        super().__init__()
        self.listener = listener

    def run(self):
        while self.listener.is_listening:
            while self.listener.is_paused:
                pass
            self.listener.__listen__()
