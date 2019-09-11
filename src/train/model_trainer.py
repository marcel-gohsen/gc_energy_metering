def warn(*args, **kwargs):
    pass


import warnings

warnings.warn = warn

from sklearn.model_selection import learning_curve
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_validate
from sklearn.metrics import make_scorer
from sklearn.metrics import mean_squared_error
from scipy.signal import find_peaks
from scipy.signal import peak_widths
import numpy as np
import json
import matplotlib.pyplot as plt
from utility import path_handler
import os.path as path
import os
import pandas
import datetime


class ModelTrainer:
    def __init__(self, db):
        self.model_ridge_performance = LinearRegression()
        self.model_dt_performance = DecisionTreeRegressor()
        self.model_rf_performance = RandomForestRegressor(n_estimators=100)

        self.model_ridge_power = LinearRegression()
        self.model_dt_power = DecisionTreeRegressor()
        self.model_rf_power = RandomForestRegressor(n_estimators=100)
        # self.clf = LinearRegression(normalize=True)
        self.db = db
        self.plotted_figures = 0

        os.makedirs(path_handler.plot_root, exist_ok=True)
        os.makedirs(path_handler.model_root, exist_ok=True)

    def filter_measurements(self, measurements, mapping_func):
        offset = mapping_func(measurements)

        work_begin = measurements.iloc[0]["work_begin_time"] + offset
        work_end = measurements.iloc[0]["work_end_time"] + offset

        measurements = measurements[measurements["timestamp"] >= work_begin]
        measurements = measurements[measurements["timestamp"] <= work_end]

        return measurements

    def map_peak_start(self, measurements):
        peak_indices, _ = find_peaks(measurements["active_power"])
        peak_start_index = 0

        if len(peak_indices) > 0:
            peak_flank = peak_widths(measurements["active_power"], peak_indices)[2]


            # power = measurements.iloc[i]["active_power"]
            peak_start_index = int(peak_flank[0])

            # peak_start_index = int(peak_indices[0] - round((peak_flank[0] / 2)))

        return measurements.iloc[peak_start_index]["timestamp"] - measurements.iloc[0]["peak_time"]

    def map_peak(self, measurements):
        peak_indices, _ = find_peaks(measurements["active_power"])
        peak_start_index = 0

        if len(peak_indices) > 0:
            peak_start_index = peak_indices[0]

        return measurements.iloc[peak_start_index]["timestamp"] - measurements.iloc[0]["peak_time"]

    def map_naiv(self, measurements):
        return datetime.timedelta()

    def aggregate_mean(self, measurements):
        return measurements["active_power"].mean()  # W

    def aggregate_mean_over_time(self, measurements):
        mean_power = measurements["active_power"].mean()

        run_time = measurements.iloc[0]["work_end_time"] - measurements.iloc[0]["work_begin_time"]

        return mean_power / run_time.total_seconds()  # W/s

    def train(self, sched_ids, benchmark_name):
        if len(sched_ids) == 0:
            return

        feature_vectors_performance = []
        feature_vectors_power = []
        labels_performance = []
        labels_total_power = []

        feature_names = None

        print("[MODEL] IDS: " + str(sched_ids))

        configs = self.db.execute(
            "SELECT run_schedule.id, conf_sw.binary_features, conf_sw.numeric_features, run_eval.completion_time FROM run_schedule " +
            "INNER JOIN (run_spec, conf_sw, run_eval) ON (run_schedule.run_spec = run_spec.id AND run_spec.sw_conf = conf_sw.id AND run_schedule.id = run_eval.run)" +
            "WHERE run_schedule.id IN (" + ", ".join(str(x) for x in sched_ids) + ");")

        measurements = self.db.execute(
            "SELECT s.id, timestamp, power_total_active, power_total_apparent, work_begin_time, work_end_time, peak_time FROM measurements AS m " +
            "JOIN run_schedule as s ON s.id = m.run WHERE run IN (" + ", ".join(str(x) for x in sched_ids) + ");"
        )

        df = pandas.DataFrame.from_records(measurements,
                                           columns=["id", "timestamp", "active_power", "apparent_power",
                                                    "work_begin_time", "work_end_time", "peak_time"])

        power_per_run = {}
        for run in df.groupby("id"):
            filtered_measurements = self.filter_measurements(run[1], self.map_peak_start)
            power_per_run[run[1].iloc[0]["id"]] = self.aggregate_mean_over_time(filtered_measurements)

        for config in configs:
            bin_features = [x for x in json.loads(config[1]).keys()]
            bin_values = json.loads(config[1]).values()
            conf = np.array([1.0 if x else 0.0 for x in bin_values])

            num_features = [x for x in json.loads(config[2]).keys()]
            num_conf = json.loads(config[2]).values()

            conf = np.append(conf, np.array([x for x in num_conf]))

            feature_vectors_performance.append(conf)

            labels_performance.append(config[3].total_seconds())

            feature_vectors_power.append(conf)
            labels_total_power.append(power_per_run[config[0]])

            if feature_names is None:
                feature_names = []
                feature_names.extend(bin_features)
                feature_names.extend(num_features)

        print("[MODEL] Train performance models")
        print("[Model] Performance examples: " + str(len(labels_performance)))

        # print(feature_vectors)
        # train_features, test_features, train_labels, test_labels = train_test_split(feature_vectors, labels)

        self.model_ridge_performance.fit(
            feature_vectors_performance,
            labels_performance)

        self.model_dt_performance.fit(
            feature_vectors_performance,
            labels_performance
        )

        self.model_rf_performance.fit(
            feature_vectors_performance,
            labels_performance
        )

        perf_estimator = [self.model_ridge_performance, self.model_dt_performance, self.model_rf_performance]
        self.plot_learning_curve(perf_estimator, feature_vectors_performance, labels_performance, benchmark_name,
                                 "performance")
        print("[MODEL] Cross-validate performance")
        self.cross_validate(perf_estimator, feature_vectors_performance, labels_performance)

        print("[MODEL] Train power models")
        print("[MODEL] Power examples: " + str(len(labels_total_power)))

        self.model_ridge_power.fit(
            feature_vectors_power,
            labels_total_power
        )

        self.model_dt_power.fit(
            feature_vectors_power,
            labels_total_power
        )

        self.model_rf_power.fit(
            feature_vectors_power,
            labels_total_power
        )

        power_estimators = [self.model_ridge_power, self.model_dt_power, self.model_rf_power]
        self.plot_learning_curve(power_estimators, feature_vectors_power, labels_total_power, benchmark_name, "power")
        print("[MODEL] Cross-validate power")
        self.cross_validate(power_estimators, feature_vectors_power, labels_total_power)

        perf_infl_model = {}
        print()
        print("PERFORMANCE INFLUENCE MODEL")
        print("---------------------------")
        for feature, coef in zip(feature_names, self.model_ridge_performance.coef_):
            print(feature + ": " + str(coef))
            perf_infl_model[feature] = coef
        print("---------------------------")
        print()

        with open(path.join(path_handler.model_root, benchmark_name + "_perf_infl_model.json"), "w+") as out_file:
            json.dump(perf_infl_model, out_file, indent=4)

        self.plot_infl_model(perf_infl_model, benchmark_name, "performance")

        power_infl_model = {}
        print()
        print("POWER INFLUENCE MODEL")
        print("---------------------------")
        for feature, coef in zip(feature_names, self.model_ridge_power.coef_):
            print(feature + ": " + str(coef))
            power_infl_model[feature] = coef
        print("---------------------------")
        print()

        self.plot_infl_model(power_infl_model, benchmark_name, "power")

        with open(path.join(path_handler.model_root, benchmark_name + "_power_infl_model.json"), "w+") as out_file:
            json.dump(power_infl_model, out_file, indent=4)

    def cross_validate(self, estimators, features, labels):
        scorer = ["neg_mean_absolute_error", "neg_mean_squared_error"]
        print()
        for estimator in estimators:
            scores = cross_validate(estimator, features, labels, cv=3,
                                    scoring=scorer)

            for metric in scorer:
                print(estimator.__class__.__name__ + " | train | " + metric + ": " +
                      str(round(np.mean(scores["train_" + metric]), 4)))

                print(estimator.__class__.__name__ + " | test | " + metric + ": " +
                      str(round(np.mean(scores["test_" + metric]), 4)))

                print()
            # print(metric.__name__ + " of " + estimator.__class__.__name__ + ": " +
            #       str(round(np.mean(scores["test_score"]), 4)))

        print()

    def plot_learning_curve(self, estimators, features, labels, benchmark_name, key_word):
        plt.figure(self.plotted_figures)
        self.plotted_figures += 1

        for estimator in estimators:
            # cv = ShuffleSplit(n_splits=100)
            cv = 3
            train_sizes, train_scores, test_scores = learning_curve(estimator, features, labels, cv=cv,
                                                                    scoring=make_scorer(mean_squared_error))

            # print("Examples: " + str(len(labels)))

            train_scores_mean = np.mean(train_scores, axis=1)
            test_scores_mean = np.mean(test_scores, axis=1)

            plt.grid()
            # plt.plot(ridge_train_sizes, ridge_train_scores_mean, "-", label="Training score")

            plt.plot(train_sizes, test_scores_mean, "-", label=estimator.__class__.__name__)

        plt.xlabel("Training examples")
        plt.ylabel("Mean sqrd error")
        plt.legend()
        plt.savefig(path.join(path_handler.plot_root, benchmark_name + "_" + key_word + "_learning_curve.png"),
                    transparent=True, dpi=200)
        # plt.show()

    def plot_infl_model(self, model, benchmark_name, key_word):
        plt.figure(self.plotted_figures)
        self.plotted_figures += 1
        plt.bar(model.keys(), model.values(), color="#8bc34a")
        plt.xlabel("Features")
        plt.xticks(rotation=90)
        plt.ylabel("Influence weight")
        plt.tight_layout(h_pad=0.2, w_pad=0.2)
        plt.grid()
        plt.savefig(path.join(path_handler.plot_root, benchmark_name + "_" + key_word + "_influence_model.png"),
                    transparent=True, dpi=200)
        # plt.show()
