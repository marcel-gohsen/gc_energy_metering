import os
import json
import time
import statistics

import ciso8601

from datetime import datetime
from listeners.arduino_power_listener import ArduinoPowerListener
from listeners.pdu_listener import PDUListener
from error_handling.error_handler import ErrorHandler
from utility import path_handler


class DataCollector:
    def __init__(self, db, listeners=None, dry_run=False):
        if listeners is None:
            listeners = []

        self.db = db
        self.dry_run = dry_run
        self.listeners = listeners

    def add_listener(self, listener):
        self.listeners.append(listener)

    def collect(self):
        for listener in self.listeners:
            listener.pause()

        time_schedule = []

        print("[DB] Insert performance measures")
        start_time = time.time()

        for (dirpath, dirnames, filenames) in os.walk(path_handler.slurm_nfs_bench_perf_root):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                eval_data = []

                if filename.endswith(".ldjson"):
                    eval_id = self.db.get_free_index("run_eval")
                    with open(path) as file:
                        for line in file:
                            data = json.loads(line)
                            begin_date = ciso8601.parse_datetime(data["begin"])
                            end_date = ciso8601.parse_datetime(data["end"])

                            completion_time = (end_date - begin_date)

                            sched_id = self.db.get_indices_of(table="run_schedule",
                                                              fields=["client_id", "repetition", "run_spec"],
                                                              values=[
                                                                  str(data["host"]),
                                                                  str(data["repetition"]),
                                                                  str(data["run_spec_id"])
                                                              ])
                            sched_id = sched_id[0]

                            time_schedule.append((sched_id, begin_date, end_date))
                            self.db.update_data(table="run_schedule",
                                                fields=["begin_time", "end_time"],
                                                values=[begin_date.strftime("%Y-%m-%d %H:%M:%S.%f"),
                                                        end_date.strftime("%Y-%m-%d %H:%M:%S.%f")],
                                                where_fields=["id"],
                                                where_values=[str(sched_id)])

                            eval_data.append([str(eval_id), str(sched_id), "OK", str(completion_time)])
                            eval_id += 1

                    self.db.insert_data("run_eval", eval_data,
                                        fields=["id", "run", "status", "completion_time"])

        print("[DB] Done in : " + str(round(time.time() - start_time, 2)) + "s")

        print("[DB] Insert power measurements")
        measurement_id = self.db.get_free_index("measurements")

        for listener in self.listeners:
            if isinstance(listener, ArduinoPowerListener):
                print("[DB] Insert fine-grained measurements")
                power_data = {}
                start_time = time.time()
                for data in listener.get_data():
                    if data is not None:
                        pass
                        # if sched_id_time[0] <= data["timestamp"] <= sched_id_time[1]:
                        #     sched_id = sched_id_time[2]
                        #
                        #     component = listener.translate_component_to_table(data["component"])
                        #
                        #     if component is not None:
                        #         fields = ("id", "timestamp", "run", component)
                        #
                        #         try:
                        #             power_data[fields].append(
                        #                 [str(measurement_id), str(data["timestamp"]),
                        #                  str(sched_id), str(data["power"])])
                        #         except KeyError:
                        #             power_data[fields] = []
                        #             power_data[fields].append(
                        #                 [str(measurement_id), str(data["timestamp"]),
                        #                  str(sched_id), str(data["power"])])
                        #
                        #         measurement_id += 1
                        #
                        #     break

                # print("FOR LOOP TIME " + str(time.time() - start))
                print("[DB] Done in : " + str(round(time.time() - start_time, 2)) + "s")

            if isinstance(listener, PDUListener):
                print("[DB] Insert coarse-grained measurements")
                average_power = {}
                measurements = []
                start_time = time.time()

                for data in listener.get_data():
                    sched_id = self.db.get_run_idx(data[0], data[1])

                    if sched_id is not None:
                        measurements.append([
                            str(measurement_id),
                            str(data[0]),
                            str(sched_id),
                            str(data[2]),
                            str(data[3]),
                            str(data[4]),
                            str(data[5])
                        ])

                        measurement_id += 1

                        if sched_id not in average_power:
                            average_power[sched_id] = []

                        average_power[sched_id].append(data[2])

                self.db.insert_data("measurements", measurements,
                                    ("id", "timestamp", "run", "power_total_active", "power_total_apparent",
                                     "current_total", "voltage_total"))

                average_power = dict(map(lambda x: (x, statistics.mean(average_power[x])), average_power))

                for key, value in average_power.items():
                    self.db.update_data("run_eval", ["power"], [str(value)], ["run"], [str(key)])

                print("[DB] Done in : " + str(round(time.time() - start_time, 2)) + "s")

            listener.resume()

        print("[DB] Done")
