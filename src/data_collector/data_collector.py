import os
import json
import time

from datetime import datetime
from listeners.arduino_power_listener import ArduinoPowerListener
from error_handling.error_handler import ErrorHandler


class DataCollector:
    def __init__(self, db, listeners=None, dry_run=False):
        if listeners is None:
            listeners = []
        self.db = db
        self.dry_run = dry_run
        self.sched_id_pool = []
        self.listeners = listeners

    def add_listener(self, listener):
        if self.listeners is None:
            self.listeners = []

        self.listeners.append(listener)

    def collect(self, result_dir):
        assembled_host = None

        if self.listeners is not None:
            for listener in self.listeners:
                listener.pause()

                if isinstance(listener, ArduinoPowerListener):
                    assembled_host = listener.assembled_host

        sched_id_times = []

        print("[DB] Insert performance data")
        for (dirpath, dirnames, filenames) in os.walk(result_dir):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                sched_data = []
                eval_data = []

                if filename.endswith(".ldjson"):
                    eval_id = self.db.get_free_index("run_eval")
                    with open(path) as file:
                        for line in file:
                            data = json.loads(line)

                            begin_date = self.extract_date(data["begin"])
                            end_date = self.extract_date(data["end"])

                            completion_time = (end_date - begin_date)

                            if not self.dry_run:
                                try:
                                    sched_id = self.sched_id_pool.pop(0)
                                except IndexError as err:
                                    sched_id = sched_id_times[len(sched_id_times) - 1][2] + 1
                                    # ErrorHandler.handle("DATA", "No left schedule id", err)

                                if data["host"] == assembled_host:
                                    sched_id_times.append((begin_date, end_date, sched_id))

                                # self.db.insert_data("run_schedule",
                                #                     [sched_id, data["run_spec_id"], data["repetition"], data["host"],
                                #                      str(begin_date)])
                                sched_data.append([str(sched_id), str(data["run_spec_id"]), str(data["repetition"]),
                                                   str(data["host"]), str(begin_date)])

                                eval_data.append([str(eval_id), str(sched_id), "OK", str(completion_time)])
                                eval_id += 1

                                # self.db.insert_data("run_eval",
                                #                     [eval_id, sched_id, "OK", str(completion_time), None, None, None,
                                #                      None])

                    self.db.insert_data("run_schedule", sched_data)
                    self.db.insert_data("run_eval", eval_data,
                                        fields=["id", "run", "status", "completion_time"])

        print("[DB] Insert power data")

        if self.listeners is not None:
            for listener in self.listeners:
                if not self.dry_run:
                    power_data = {}
                    measurement_id = self.db.get_free_index("measurements")

                    if isinstance(listener, ArduinoPowerListener):
                        start = time.time()
                        for data in listener.get_data():
                            if data is not None and len(sched_id_times) > 0:
                                if sched_id_times[0][0] <= data["timestamp"] <= sched_id_times[len(sched_id_times) - 1][1]:
                                    for sched_id_time in sched_id_times:
                                        if sched_id_time[0] <= data["timestamp"] <= sched_id_time[1]:
                                            sched_id = sched_id_time[2]

                                            component = listener.translate_component_to_table(data["component"])

                                            if component is not None:
                                                fields = ("id", "timestamp", "run", component)

                                                try:
                                                    power_data[fields].append(
                                                        [str(measurement_id), str(data["timestamp"]),
                                                         str(sched_id), str(data["power"])])
                                                except KeyError:
                                                    power_data[fields] = []
                                                    power_data[fields].append(
                                                        [str(measurement_id), str(data["timestamp"]),
                                                         str(sched_id), str(data["power"])])

                                                measurement_id += 1

                                            break

                        # print("FOR LOOP TIME " + str(time.time() - start))

                    for fields, values in power_data.items():
                        self.db.insert_data("measurements", values, fields)

                    if isinstance(listener, ArduinoPowerListener):
                        for _, _, sched_id in sched_id_times:
                            total_power = 0
                            for component in listener.component_tanslate.values():
                                results = self.db.execute(
                                    "SELECT AVG(" + component + ") FROM measurements WHERE run = " + str(
                                        sched_id) + ";")

                                if results[0][0] is not None:
                                    total_power += float(results[0][0])

                            self.db.execute(
                                "UPDATE run_eval SET power = " + str(total_power) + " WHERE run = " + str(
                                    sched_id) + ";",
                                result_set=False)

                        self.db.connection.commit()

                listener.resume()

        print("[DB] Done")

    @staticmethod
    def extract_date(date_str):
        date_micros = int(int(date_str.split(" ")[2]) / 1000)
        date_micros = str(date_micros).zfill(6)
        date_str = " ".join(date_str.split(" ")[0:2]) + " " + date_micros

        return datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S %f")
