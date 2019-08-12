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
from utility.utilities import get_size


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

        # time_schedule = []

        print("[DB] Insert performance measures")
        start_time = time.time()

        sched_id = self.db.get_free_index("run_schedule")
        eval_id = self.db.get_free_index("run_eval")

        sched_data = []
        eval_data = []

        for (dirpath, dirnames, filenames) in os.walk(path_handler.slurm_nfs_bench_perf_root):
            for filename in filenames:
                path = os.path.join(dirpath, filename)

                if filename.endswith(".ldjson"):
                    with open(path) as file:
                        for line in file:
                            data = json.loads(line)
                            begin_work = ciso8601.parse_datetime(data["begin"])
                            end_work = ciso8601.parse_datetime(data["end"])

                            completion_time = (end_work - begin_work)

                            begin_job = ciso8601.parse_datetime(data["job_begin"])
                            end_job = ciso8601.parse_datetime(data["job_end"])

                            sched_data.append([
                                str(sched_id),
                                str(data["run_spec_id"]),
                                str(data["repetition"]),
                                str(data["host"]),
                                begin_job.strftime("%Y-%m-%d %H:%M:%S.%f"),
                                end_job.strftime("%Y-%m-%d %H:%M:%S.%f")]
                            )

                            eval_data.append([str(eval_id), str(sched_id), "OK", str(completion_time)])

                            sched_id += 1
                            eval_id += 1

        self.db.insert_data("run_schedule", sched_data)
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
