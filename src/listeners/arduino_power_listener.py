from listeners.listener import Listener

import serial
import time
import datetime
from itertools import islice


class ArduinoPowerListener(Listener):

    def __init__(self):
        super().__init__()

        self.ports = ["/dev/ttyUSB0", "/dev/ttyUSB1"]
        self.arduinos = [serial.Serial(port, baudrate=1000000) for port in self.ports]

        self.read_start_times = [None for _ in self.arduinos]
        self.out_path = "../data/buffer/arduino_power.csv"  # TODO: Change to actual path

        self.out_file = open(self.out_path, mode="w+")

        self.is_writing = False

        self.constants = \
            {
                "H": 25 * 0.1,
                "I": 25 * 0.1,
                "J": 25 * 0.02,
                "K": 25 * 0.02,
                "A": 25 * 0.013,
                "B": 25 * 0.013,
                "C": 25 * 0.013,
                "D": 25 * 0.013,
                "L": 25 * 0.013,
                "M": 25 * 0.013,
                "E": 25 * 0.013,
                "F": 25 * 0.013
            }

        self.component_tanslate = \
            {
                "H": "power_cpu_12v_1",
                "I": "power_cpu_12v_2",
                "J": "power_ssd_5v",
                "K": "power_ssd_12v",
                "A": "power_mobo_3v_1",
                "B": "power_mobo_3v_2",
                "C": "power_mobo_3v_3",
                "D": "power_mobo_3v_4",
                "L": "power_mobo_5v_1",
                "M": "power_mobo_5v_2",
                "E": "power_mobo_12v_1",
                "F": "power_mobo_12v_2"
            }

        self.assembled_host = "tesla002"

    def start(self):
        super().start()

        time.sleep(1.464975)  # measured time for initial read from port

    def stop(self):
        super().stop()

        while self.thread.is_alive():
            pass

        self.read_start_times = []
        for arduino in self.arduinos:
            arduino.close()
            self.read_start_times.append(None)

        self.out_file.flush()
        self.out_file.close()
        self.out_file = None

    def pause(self):
        super().pause()

        while self.is_writing:
            pass

        self.read_start_times = []
        for arduino in self.arduinos:
            arduino.close()
            self.read_start_times.append(None)

        self.out_file.flush()
        self.out_file.close()
        self.out_file = None

    def resume(self):
        self.out_file = open(self.out_path, mode="w+")
        self.arduinos = [serial.Serial(port, baudrate=1000000) for port in self.ports]

        super().resume()

    def get_data(self):
        with open(self.out_path) as in_file:
            strptime = datetime.datetime.strptime

            for line in in_file:
                attribs = line.replace("\n", "").split(",")

                try:
                    # timestamp = np.datetime64(attribs[1])
                    timestamp = strptime(attribs[1], "%Y-%m-%d %H:%M:%S.%f")
                    # timestamp = None
                    yield {"component": attribs[0], "timestamp": timestamp, "power": float(attribs[2])}
                except ValueError as err:
                    yield None

    def translate_component_to_table(self, component):
        if component in self.component_tanslate:
            return self.component_tanslate[component]

        return None

    def __listen__(self):
        self.is_writing = True

        for i in range(0, len(self.arduinos)):
            if self.read_start_times[i] is None:
                self.read_start_times[i] = datetime.datetime.now()

            data = self.arduinos[i].readline()
            timestamp = datetime.datetime.now()
            result = self.__extract_data(data)

            power = 0

            if result is not None:
                component, power = result

                try:
                    if component in self.constants:
                        power = self.constants[component] * float(power)
                        # timestamp = self.read_start_times[i] + delta_time

                        if power <= 65000:
                            self.out_file.write(component + "," + str(timestamp) + "," + str(power) + "\n")
                except ValueError:
                    pass

        self.is_writing = False

    @staticmethod
    def __extract_data(data):
        if data is not None:
            in_string = None
            try:
                in_string = data.decode("utf-8")

            except UnicodeDecodeError:
                pass

            if in_string is not None:
                attribs = in_string.replace("\n", "").split(",")

                if len(attribs) == 2:
                    component = attribs[0]
                    # delta_time = attribs[1]
                    power = attribs[1]

                    # delta_time = datetime.timedelta(microseconds=float(delta_time))

                    return component, power


if __name__ == '__main__':
    listener = ArduinoPowerListener()
    listener.start()
    time.sleep(5)
    # listener.pause()
    # listener.get_data()
    # listener.resume()
    listener.stop()

    # listener = ArduinoPowerListener()
    # listener.start()
    # time.sleep(5)
    # listener.stop()
