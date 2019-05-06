from listeners.listener import Listener
import requests
import time
import itertools
import xml.etree.ElementTree as ET


class PDUListener(Listener):

    def __init__(self, outlets=[0, 17]):
        super().__init__()

        self.pdu_address = "http://141.54.132.133/cgi/get_param.cgi"

        parameter = [
            "outlet.name.dev1",
            "sys.time",
            "sys.passwd",
            "outlet.current.dev1",
            "outlet.voltage.dev1",
            "outlet.apppower.dev1",
            "outlet.pf.dev1",
            "outlet.energy.dev1",
        ]

        outlet_ids = itertools.chain.from_iterable(itertools.repeat(x, len(parameter)) for x in outlets)

        self.param_string = "&".join([x + "[{}]" for x in parameter] * len(outlets)).format(*outlet_ids)
        self.param_string = "?xml&" + self.param_string

        self.outlets = outlets

    def __listen__(self):
        time.sleep(0.24)

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
            elif element.tag == "outlet.apppower.dev1":
                data[current_outlet]["power"] = float(element.text)
            elif element.tag == "outlet.pf.dev1":
                data[current_outlet]["power_factor"] = float(element.text)
            elif element.tag == "outlet.energy.dev1":
                data[current_outlet]["energy"] = float(element.text)
            elif element.tag == "sys.time":
                data["time"] = element.text
            elif element.tag == "sys.passwd":
                pass
                # print(element.text)

        print(data)


if __name__ == '__main__':
    listener = PDUListener()
    listener.start()
    time.sleep(20)
    listener.stop()
