from listeners.listener import Listener
import requests
import time
import itertools
import xml.etree.ElementTree as ET
import uuid
import os
import json


class PDUListener(Listener):

    def __init__(self, outlets=[0, 17], sample_rate=4, experiment="debug"):
        super().__init__()

        self.pdu_address = "http://141.54.132.133/cgi/get_param.cgi"

        local_parameter = [
            "outlet.name.dev1",
            "outlet.current.dev1",
            "outlet.voltage.dev1",
            "outlet.apppower.dev1",
            "outlet.power.dev1",
            "outlet.pf.dev1",
            "outlet.energy.dev1",
        ]

        global_parameter = ["sys.time"]

        outlet_ids = itertools.chain.from_iterable(itertools.repeat(x, len(local_parameter)) for x in outlets)

        self.param_string = "&".join([x + "[{}]" for x in local_parameter] * len(outlets)).format(*outlet_ids)
        self.param_string = "&".join(global_parameter) + "&" + self.param_string
        self.param_string = "?xml&" + self.param_string

        self.outlets = outlets
        self.sample_interval = 1 / sample_rate
        self.process_time = float("inf")
        self.data_path = "../data/pdu/" + experiment

        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)

        run_id = str(uuid.uuid1())
        print("Run: " + run_id)
        self.data_path = os.path.join(self.data_path, run_id)
        os.makedirs(self.data_path)

    def __listen__(self):
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
                data["time"] = element.text
            elif element.tag == "sys.passwd":
                pass

        self.write_data(data)
        self.process_time = (time.time() - start)

    def write_data(self, data):
        for key in data.keys():
            if key != "time":
                with open(os.path.join(self.data_path, key.replace(" ", "-") + ".ldjson"), "a+") as out_file:
                    data[key]["time"] = data["time"]
                    out_file.write(json.dumps(data[key]) + "\n")

