import datetime
import itertools
import json
import os
import os.path as path
import time
import xml.etree.ElementTree as ET

import requests

from listeners.listener import Listener
from utility import path_handler


class PDUListener(Listener):
    def __init__(self, outlets=range(9, 18), sample_rate=4):
        super().__init__()

        self.pdu_address = "http://pdu001.medien.uni-weimar.de/cgi/get_param.cgi"

        local_parameter = [
            "outlet.name.dev1",
            "outlet.current.dev1",
            "outlet.voltage.dev1",
            "outlet.apppower.dev1",
            "outlet.power.dev1",
            "outlet.pf.dev1",
            "outlet.energy.dev1",
            "noexport.state.dev1"
        ]

        global_parameter = ["sys.time"]

        outlet_ids = itertools.chain.from_iterable(
            itertools.repeat(x, len(local_parameter)) for x in outlets)

        self.param_string = "&".join([x + "[{}]" for x in local_parameter] * len(outlets)).format(*outlet_ids)
        self.param_string = "&".join(global_parameter) + "&" + self.param_string
        self.param_string = "?xml&" + self.param_string

        self.outlets = outlets
        self.sample_interval = 1 / sample_rate
        self.process_time = float("inf")
        self.out_path = path_handler.buffer_root

        if not os.path.exists(self.out_path):
            os.makedirs(self.out_path)

        self.out_path = path.join(self.out_path, "pdu.jsonld")
        self.out_file = open(self.out_path, "w+")

        self.is_writing = False

    def __listen__(self):
        self.is_writing = True
        if self.process_time < self.sample_interval:
            time.sleep(self.sample_interval - self.process_time)

        start = time.time()
        response = requests.get(self.pdu_address + self.param_string)

        tree = ET.fromstring(response.text)

        data = {}
        current_outlet = None
        for element in tree.iter():
            if element.tag == "outlet.name.dev1":
                data[element.text] = {}
                current_outlet = element.text
            elif element.tag == "outlet.current.dev1":
                data[current_outlet]["current"] = float(element.text)
            elif element.tag == "outlet.voltage.dev1":
                data[current_outlet]["voltage"] = float(element.text)
            elif element.tag == "outlet.power.dev1":
                data[current_outlet]["power-active"] = float(element.text)
            elif element.tag == "outlet.apppower.dev1":
                data[current_outlet]["power-apparent"] = float(element.text)
            elif element.tag == "outlet.pf.dev1":
                data[current_outlet]["power_factor"] = float(element.text)
            elif element.tag == "outlet.energy.dev1":
                data[current_outlet]["energy"] = float(element.text)
            elif element.tag == "sys.time":
                data["time"] = datetime.datetime.now().isoformat()
            elif element.tag == "sys.passwd":
                pass

        self.write_data(data)
        self.process_time = (time.time() - start)
        self.is_writing = False

    def write_data(self, data):
        try:
            self.out_file.write(json.dumps(data, default=str) + "\n")
        except ValueError:
            pass

    def get_data(self):
        with open(self.out_path, "r") as self.out_file:
            for line in self.out_file:
                data = json.loads(line)
                timestamp = ""

                for key in data:
                    if key == "time":
                        timestamp = data[key]
                    else:
                        yield (
                            timestamp,
                            key,
                            data[key]["power-active"],
                            data[key]["power-apparent"],
                            data[key]["current"],
                            data[key]["voltage"]
                        )

    def stop(self):
        super().stop()

        while self.is_writing:
            pass

        self.out_file.close()

    def pause(self):
        super().pause()

        while self.is_writing:
            pass

        self.out_file.flush()
        self.out_file.close()

    def resume(self):
        self.out_file = open(self.out_path, "w+")

        super().resume()


def main():
    listener = PDUListener()
    listener.start()
    time.sleep(2)
    listener.pause()
    listener.get_data()
    listener.resume()
    time.sleep(2)
    listener.stop()


if __name__ == '__main__':
    main()

