def warn(*args, **kwargs):
    pass


import warnings

warnings.warn = warn

from sklearn.linear_model import Ridge
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_validate
from sklearn.metrics import make_scorer
from sklearn.metrics import mean_squared_error
from sklearn.metrics import mean_absolute_error

import numpy as np
import json
import matplotlib.pyplot as plt
from utility import path_handler
import os.path as path
import os
import pandas as pd
import random
import copy

import train.alignment as alignment
import train.aggregation as aggregation
import seaborn as sns


def mean_absolute_percentage_error(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100


class ModelTrainer:
    def __init__(self, db):
        self.model_ridge_performance = Ridge()
        self.model_dt_performance = DecisionTreeRegressor()
        self.model_rf_performance = RandomForestRegressor(n_estimators=1)

        self.model_ridge_power = Ridge()
        self.model_dt_power = DecisionTreeRegressor()
        self.model_rf_power = RandomForestRegressor(n_estimators=100)
        # self.clf = LinearRegression(normalize=True)
        self.db = db
        self.plotted_figures = 0

        os.makedirs(path_handler.plot_root, exist_ok=True)
        os.makedirs(path_handler.model_root, exist_ok=True)

    def filter_measurements(self, measurements, mapping_func):
        offset = mapping_func(measurements)

        work_begin = measurements.iloc[0]["work_begin_time"]
        work_end = measurements.iloc[0]["work_end_time"]

        filtered = measurements[measurements["timestamp"] >= work_begin + offset]
        filtered = filtered[filtered["timestamp"] <= work_end + offset]

        if filtered.empty:
            filtered = measurements[measurements["timestamp"] >= work_begin]
            filtered = filtered[filtered["timestamp"] <= work_end]

        return filtered

    def collect_measurements(self, sched_ids, alignment_strategy, aggregation_strategy):
        measurements = self.db.execute(
            "SELECT s.id, timestamp, power_total_active, power_total_apparent, work_begin_time, work_end_time, peak_time FROM measurements AS m " +
            "JOIN run_schedule as s ON s.id = m.run WHERE run IN (" + ", ".join(str(x) for x in sched_ids) + ");"
        )

        df = pd.DataFrame.from_records(measurements,
                                       columns=["id", "timestamp", "active_power", "apparent_power",
                                                "work_begin_time", "work_end_time", "peak_time"])

        power_per_run = {}
        for run in df.groupby("id"):
            filtered_measurements = self.filter_measurements(run[1], alignment_strategy)
            power_per_run[run[1].iloc[0]["id"]] = aggregation_strategy(filtered_measurements)

        return power_per_run

    def train(self, sched_ids, benchmark_name):
        if len(sched_ids) == 0:
            return

        perf_estimators = [self.model_ridge_performance, self.model_dt_performance, self.model_rf_performance]
        power_estimators = [self.model_ridge_power, self.model_dt_power, self.model_rf_power]

        alignment_strategies = [alignment.naiv, alignment.peak, alignment.peak_start]
        aggregation_strategies = [aggregation.mean, aggregation.cumulate, aggregation.energy_naiv,
                                  aggregation.energy_integration]

        power_cross_val_results = []
        feature_names = None

        print("[MODEL] IDS: " + str(sched_ids))

        configs = self.db.execute(
            "SELECT run_schedule.id, conf_sw.binary_features, conf_sw.numeric_features, run_eval.completion_time FROM run_schedule " +
            "INNER JOIN (run_spec, conf_sw, run_eval) ON (run_schedule.run_spec = run_spec.id AND run_spec.sw_conf = conf_sw.id AND run_schedule.id = run_eval.run)" +
            "WHERE run_schedule.id IN (" + ", ".join(str(x) for x in sched_ids) + ");")

        for alignment_strategy in alignment_strategies:
            for aggregation_strategy in aggregation_strategies:
                feature_vectors_performance = []
                feature_vectors_power = []
                labels_performance = []
                labels_total_power = []

                measurements = self.collect_measurements(sched_ids, alignment_strategy, aggregation_strategy)

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
                    labels_total_power.append(measurements[config[0]])

                    if feature_names is None:
                        feature_names = []
                        feature_names.extend(bin_features)
                        feature_names.extend(num_features)

                print("[MODEL] Train performance models")
                print("[Model] Performance examples: " + str(len(labels_performance)))

                self.plot_learning_curve(
                    perf_estimators,
                    feature_vectors_performance,
                    labels_performance,
                    benchmark_name,
                    "performance_" + alignment_strategy.__name__ + "_" + aggregation_strategy.__name__)

                print("[MODEL] Cross-validate performance")
                self.cross_validate(perf_estimators, feature_vectors_performance, labels_performance)

                print("[MODEL] Train power models")
                print("[MODEL] Power examples: " + str(len(labels_total_power)))

                self.plot_learning_curve(
                    power_estimators,
                    feature_vectors_power,
                    labels_total_power,
                    benchmark_name,
                    "power_" + alignment_strategy.__name__ + "_" + aggregation_strategy.__name__)

                print("[MODEL] Cross-validate power")
                results = self.cross_validate(power_estimators, feature_vectors_power, labels_total_power)

                for result in results:
                    result["alignment"] = alignment_strategy.__name__
                    result["aggregation"] = aggregation_strategy.__name__

                power_cross_val_results.extend(results)

                self.plot_infl_model(self.model_ridge_performance, feature_names, benchmark_name,
                                     "performance_" + alignment_strategy.__name__ + "_" + aggregation_strategy.__name__)

                self.plot_infl_model(self.model_ridge_power, feature_names, benchmark_name,
                                     "power_" + alignment_strategy.__name__ + "_" + aggregation_strategy.__name__)

        for result in power_cross_val_results:
            if result["estimator"] == "DecisionTreeRegressor":
                result["estimator"] = "DT"
            elif result["estimator"] == "RandomForestRegressor":
                result["estimator"] = "RF"

        result_dataframe = pd.DataFrame(power_cross_val_results)
        sns.set(style="whitegrid")

        plotgrid = sns.FacetGrid(result_dataframe, col="alignment", row="aggregation", margin_titles=True)
        plotgrid.map(sns.barplot, "estimator", "mean_absolute_percentage_error", color="#8bc34a")
        plotgrid.set_axis_labels("Estimator", "Test MAPE [%]")
        plotgrid.add_legend()

        self.plotted_figures += 1
        plt.tight_layout()

        plt.savefig(path.join(path_handler.plot_root, benchmark_name + "_cross_validation.png"),
                    transparent=True, dpi=200)


    def cross_validate(self, estimators, features, labels):
        scorer = {
            "mean_absolute_error": make_scorer(mean_absolute_error),
            "mean_absolute_percentage_error": make_scorer(mean_absolute_percentage_error),
            "mean_squared_error": make_scorer(mean_squared_error)}

        print()

        results = []
        for estimator in estimators:
            scores = cross_validate(estimator, features, labels, cv=3,
                                    scoring=scorer)

            result = {"estimator": estimator.__class__.__name__}

            for metric in scorer.keys():
                result[metric] = np.mean(scores["test_" + metric])

                print(estimator.__class__.__name__ + " | " + metric + ": " +
                      str(round(np.mean(scores["test_" + metric]), 4)))

            results.append(result)

            print()

        print()

        return results

    def plot_learning_curve(self, estimators, features, labels, benchmark_name, key_word):
        plt.figure(self.plotted_figures)
        self.plotted_figures += 1

        print()
        print("Error < 5% after ...")
        for estimator in estimators:
            plot_data = []

            test_data = copy.deepcopy(features)
            test_labels = copy.deepcopy(labels)

            train_data = []
            train_labels = []

            threshold_idx = None

            for i in range(1, len(features)):
                data_idx = random.randint(0, len(test_data) - 1)

                train_data.append(test_data[data_idx])
                train_labels.append(test_labels[data_idx])

                test_data.pop(data_idx)
                test_labels.pop(data_idx)

                model = estimator.fit(train_data, train_labels)

                predict_labels = model.predict(test_data)
                error = mean_absolute_percentage_error(test_labels, predict_labels)

                if threshold_idx is None and error < 5:
                    threshold_idx = i

                plot_data.append(error)

            print(estimator.__class__.__name__ + ": " + str(threshold_idx))
            plt.plot(range(1, len(features)), plot_data, label=estimator.__class__.__name__)

        plt.hlines(5, 0, len(features), colors="grey", linestyles="dashed", label="5% threshold")
        plt.grid()
        plt.xlabel("Training examples")
        plt.ylabel("Test MAPE [%]")
        plt.legend()
        plt.savefig(path.join(path_handler.plot_root, benchmark_name + "_" + key_word + "_learning_curve.png"),
                    transparent=True, dpi=200)

        print()

    def plot_infl_model(self, estimator, feature_names, benchmark_name, key_word):
        model = {}
        print()
        print(key_word.upper() + " INFLUENCE MODEL")
        print("---------------------------")
        for feature, coef in zip(feature_names, estimator.coef_):
            print(feature + ": " + str(coef))
            model[feature] = coef
        print("---------------------------")
        print()

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

        with open(path.join(path_handler.model_root, benchmark_name + "_" + key_word + "_infl_model.json"),
                  "w+") as out_file:
            json.dump(model, out_file, indent=4)
