from listeners.listener import Listener
import requests
import time


class PDUListener(Listener):

    def __listen__(self):
        time.sleep(0.5)
        response = requests.get("http://141.54.132.133/")

        print(response.text)


if __name__ == '__main__':
    listener = PDUListener()
    listener.start()
    time.sleep(5)
    listener.stop()
