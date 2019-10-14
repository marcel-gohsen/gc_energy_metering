import os.path as path

import matplotlib.pyplot as plt
import numpy as np
import pandas
import seaborn as sns
from scipy.signal import find_peaks
from scipy.signal import peak_widths

import train.aggregation as aggregation
from settings import settings
from utility import path_handler


class Plotter:
    def __init__(self, db):
        self.db = db

    def plot_performance_by_config(self, config_ids, sched_ids=None):
        print("[Plot] Plot performance grouped by config")
        data = []

        for id in config_ids:
            spec_ids = self.db.get_indices_of("run_spec", "sw_conf", id)
            sched_ids = self.db.get_indices_of("run_schedule", ["run_spec"] * len(spec_ids), spec_ids, conjunction="OR")

            conditions = " OR ".join(["run={}"] * len(sched_ids)).format(*sched_ids)
            data.append([x[0].total_seconds() * 1000 for x in
                         self.db.get_data("run_eval", fields=["completion_time"], condition=conditions)])

        fig = plt.figure()
        plt.title("Performance of software configurations")
        plt.xlabel("Configuration id")
        plt.ylabel("Completion time [ms]")

        plt.boxplot(data, labels=config_ids)
        plt.savefig("../data/plots/performance_sw_confs.png")
        # plt.show()

        # if sched_ids is None:
        #     spec_ids = self.db.get_indices_of("run_spec", ["sw_conf"] * len(config_ids), config_ids, conjunction="OR")
        #     sched_ids = self.db.get_indices_of("run_schedule", ["run_spec"] * len(spec_ids), spec_ids, conjunction="OR")
        #
        # conditions = " OR ".join(["run={}"] * len(sched_ids)).format(*sched_ids)

    def plot_energy_performance_tradeoff(self, sched_ids, plot_id, metric="energy"):
        plt.figure(plot_id)

        results = self.db.execute("SELECT s.id, e.completion_time, m.power_total_active, m.power_total_apparent," +
                                  " m.timestamp, s.work_begin_time, s.work_end_time" +
                                  " FROM run_schedule as s" +
                                  " JOIN run_eval AS e ON e.run = s.id"
                                  " JOIN measurements AS m ON m.run = s.id" +
                                  " WHERE s.id IN (" + (",".join(str(x) for x in sched_ids)) + ");")

        results = pandas.DataFrame.from_records(results,
                                                columns=["id", "completion_time", "active_power", "apparent_power",
                                                         "timestamp", "work_begin", "work_end"])

        plot_data = []
        for group in results.groupby("id"):
            rep_measurements = group[1]
            rep_measurements = rep_measurements[rep_measurements["timestamp"] >= rep_measurements.iloc[0]["work_begin"]]
            rep_measurements = rep_measurements[rep_measurements["timestamp"] <= rep_measurements.iloc[0]["work_end"]]

            plot_data.append({"id": rep_measurements.iloc[0]["id"],
                              "completion_time": rep_measurements.iloc[0]["completion_time"].total_seconds(),
                              "energy": aggregation.energy_integration(rep_measurements),
                              "power": aggregation.mean(rep_measurements)})

        plot_data = pandas.DataFrame(plot_data)

        sns.regplot("completion_time", metric, data=plot_data,
                    scatter_kws={"color": "#8bc34a", "alpha": 0.3, "s": 10.0}, line_kws={"color": "k"},
                    marker="o", scatter=True)

        plt.xlabel("Completion time [s]")
        if metric == "energy":
            plt.ylabel("Energy [Wh]")
        elif metric == "power":
            plt.ylabel("Mean power [W]")

        plt.grid()
        plt.savefig(
                path.join(path_handler.plot_root, settings.BENCHMARK["name"] + "_performance-" + metric + "-tradeoff.png"),
                dpi=200,
                transparent=True)

        print()
        print("PEARSON CORRELATION COEFFICIENT")
        print("----------------------------")
        print(np.corrcoef(plot_data["completion_time"], plot_data[metric]))
        print("----------------------------")
        print()

    def plot_performance_by_host(self, sched_ids, plot_id):
        plt.figure(plot_id)
        results = \
            self.db.execute("SELECT completion_time, client_id FROM run_eval"
                            " INNER JOIN run_schedule ON run_eval.run = run_schedule.id WHERE run IN (" +
                            (",".join(str(x) for x in sched_ids)) + ");")

        completion_times = {}
        for result in results:
            try:
                completion_times[result[1]].append(result[0].total_seconds())
            except KeyError:
                completion_times[result[1]] = []
                completion_times[result[1]].append(result[0].total_seconds())

        sorted_list = sorted(completion_times.items(), key=lambda x: x[0])
        labels = [x[0] for x in sorted_list]
        data = [x[1] for x in sorted_list]
        plt.boxplot(data, labels=labels)
        plt.xlabel("Hosts")
        plt.ylabel("Completion time [s]")
        plt.xticks(rotation=90)
        plt.tight_layout(h_pad=0.2, w_pad=0.2)
        plt.savefig(
            path.join(path_handler.plot_root, settings.BENCHMARK["name"] + "_performance_by_host.png"),
            transparent=True,
            dpi=200)
        # plt.show()

    def plot_power_curve(self, run_id):
        results = self.db.execute(
            "SELECT timestamp, power_total_active, power_total_apparent, current_total, voltage_total, work_begin_time, work_end_time, peak_time FROM measurements AS m " +
            "JOIN run_schedule as s ON s.id = m.run WHERE run = " + str(run_id) + ";")

        df = pandas.DataFrame.from_records(results,
                                           columns=["timestamp", "active_power", "apparent_power", "current", "voltage",
                                                    "work_begin_time", "work_end_time", "peak_time"])

        peak_indices, _ = find_peaks(df["apparent_power"])
        peak_start_index = 0

        if len(peak_indices) > 0:
            peak_ws = peak_widths(df["apparent_power"], peak_indices)[2]
            peak_start_index = int(peak_ws[0])

        # df = df[df["timestamp"] >= df.iloc[0]["work_begin_time"]]
        # df = df[df["timestamp"] <= df.iloc[0]["work_end_time"]]

        plt.figure()
        plt.plot(df["timestamp"], df["apparent_power"],
                 markevery=[peak_start_index],
                 marker="x",
                 markeredgecolor="k",
                 color="#8bc34a")

        # plt.scatter(list(pandas.to_timedelta(df['timestamp'], errors="coerce").dt.total_seconds()), df["active_power"],
        #             # markevery=[peak_start_index],
        #             marker="x",
        #             # markeredgecolor="k",
        #             s=0.1,
        #             color="#8bc34a")

        offset = df["timestamp"][peak_start_index] - df["peak_time"][0]

        # offset = datetime.timedelta()

        plt.axvline(df["work_begin_time"][0] + offset, color="k")
        plt.axvline(df["work_end_time"][0] + offset, color="k")

        plt.xlabel("Time")
        plt.ylabel("Power [W]")
        plt.ylim((0, 70))
        plt.xticks(rotation=35)
        plt.tight_layout()
        plt.savefig(
            path.join(path_handler.plot_root,
                      settings.BENCHMARK["name"] + "_measurement_curve_" + str(run_id) + ".png"),
            dpi=200,
            transparent=True
        )
        # plt.show()

    def plot_config_variance(self, sched_ids):
        measurements = self.db.execute(
            "SELECT s.id, timestamp, power_total_active, power_total_apparent, work_begin_time, work_end_time, spec.sw_conf FROM measurements AS m " +
            "JOIN run_schedule as s ON s.id = m.run JOIN run_spec as spec ON spec.id = s.run_spec " +
            "WHERE run IN (" + ", ".join(str(x) for x in sched_ids) + ");"
        )

        measurements = pandas.DataFrame.from_records(measurements,
                                                     columns=["id", "timestamp", "active_power", "apparent_power",
                                                              "work_begin", "work_end", "conf_id"])

        configs = []
        for group in measurements.groupby("id"):
            rep_measurements = group[1]
            rep_measurements = rep_measurements[rep_measurements["timestamp"] >= rep_measurements.iloc[0]["work_begin"]]
            rep_measurements = rep_measurements[rep_measurements["timestamp"] <= rep_measurements.iloc[0]["work_end"]]

            configs.append({"config": rep_measurements.iloc[0]["conf_id"],
                            "mean_power": rep_measurements["active_power"].mean()})

        plot_data = pandas.DataFrame(configs)
        plot_data = plot_data.sort_values(by=["mean_power"])
        plot_data["config"] = plot_data["config"].astype(str)
        # print(plot_data)

        fig = plt.figure()
        ax = fig.subplots()
        sns.lineplot(x="config", y="mean_power", data=plot_data, ax=ax, sort=False, color="#8bc34a")
        ax.set_xticklabels([])

        plt.xlabel("Config")
        plt.ylabel("Mean power [W]")
        plt.savefig(
            path.join(path_handler.plot_root,
                      settings.BENCHMARK["name"] + "_power_config_variance.png"),
            dpi=200,
            transparent=True
        )
