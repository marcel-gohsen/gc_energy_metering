import matplotlib.pyplot as plt
import numpy as np


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

    def plot_energy_performance_tradeoff(self, sched_ids, benchmark_name, plot_id):
        plt.figure(plot_id)
        results = \
            self.db.execute("SELECT completion_time, power FROM run_eval where run in (" + (
                ",".join(str(x) for x in sched_ids)) + ") and power is not null;")

        completion_times = []
        power = []

        for row in results:
            if row[1] > 0:
                completion_times.append(row[0].total_seconds())
                power.append(row[1])

        fit = np.polyfit(completion_times, power, 1)
        fit_fn = np.poly1d(fit)

        r = np.corrcoef(completion_times, power)[0, 1]
        print()
        print("PEARSON CORRELATION COEFFICIENT")
        print("----------------------------")
        print(np.corrcoef(completion_times, power))
        print("----------------------------")
        print()

        plt.plot(completion_times, power, "o", color="#8bc34a")
        plt.plot(completion_times, fit_fn(completion_times), "-", linewidth=2, alpha=0.7, color="black",
                 label="Linear regression")
        plt.xlabel("Completion time [s]")
        plt.ylabel("Mean power [mW]")
        # plt.xlim(0)
        # plt.ylim(0)
        plt.grid()
        plt.legend()
        plt.savefig("../data/plots/" + benchmark_name + "_performance-power-tradeoff.png", dpi=200, transparent=True)
        # plt.show()

    def plot_performance_by_host(self, sched_ids, benchmark_name, plot_id):
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
        plt.savefig("../data/plots/" + benchmark_name + "_performance_by_host.png", transparent=True, dpi=200)
        # plt.show()

    def plot_power_curve(self, run_id):
        results = self.db.execute(
            "SELECT timestamp, power_total_active, power_total_apparent, current_total, voltage_total FROM measurements WHERE run = " + str(run_id) + ";")

        x_values = []
        y_values = []
        for row in results:
            x_values.append(row[0])
            y_values.append(row[2])

        plt.figure()
        plt.plot(x_values, y_values)
        plt.xlabel("Time")
        plt.ylabel("Power [VA]")
        plt.show()
