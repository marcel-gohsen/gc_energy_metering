import os

import argparse
import json
import pandas as pd
import seaborn
import matplotlib.pyplot as plt
import numpy as np
import re


def load_data_exp1():
    data = []
    for root, dirs, files in os.walk("../../data/pdu/"):
        for file in files:
            if re.match("(.)*/exp1-bulb[1-2]/(.)*", root):
                with open(os.path.join(root, file)) as in_file:
                    outlet = file.replace(".ldjson", "").replace("-", " ")
                    bulb = None

                    if "bulb1" in root:
                        bulb = "Bulb 1"
                    elif "bulb2" in root:
                        bulb = "Bulb 2"

                    for line in in_file:
                        data_line = json.loads(line)
                        data_line["outlet"] = outlet
                        data_line["bulb"] = bulb

                        data.append(data_line)

    df = pd.DataFrame(data)

    return df


def load_data_exp1_12():
    data = []
    for root, dirs, files in os.walk("../../data/pdu/exp1-bulb1-2"):
        for file in files:
            with open(os.path.join(root, file)) as in_file:
                outlet = file.replace(".ldjson", "").replace("-", " ")

                for line in in_file:
                    data_line = json.loads(line)
                    data_line["outlet"] = outlet

                    data.append(data_line)

    df = pd.DataFrame(data)

    return df


def main(experiment):
    data = load_data_exp1()

    data_attrib = "voltage"

    data[data == 0] = np.nan
    outlets = data.outlet.unique()
    outlets = sorted(outlets, key=lambda out: int(out.split()[1]))

    seaborn.set()

    b_plot = seaborn.catplot(x="outlet", y=data_attrib, hue="bulb", data=data, order=outlets, kind="violin",
                             aspect=2, legend=False)
    [plt.setp(ax.get_xticklabels(), rotation=90) for ax in b_plot.axes.flat]
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    plt.tight_layout()
    plt.savefig("../../data/plots/exp1-" + data_attrib + ".png", transparent=True)
    plt.show()

    # data = data[data.bulb == "Bulb 1"]
    # outlet_means = data.groupby("outlet").mean()
    # outlet_variances = data.groupby("outlet").var()
    # variance = data.var()
    # print(outlet_variances)
    # print(outlet_means)
    # print("\nOverall variance")
    # print(variance)

    data = load_data_exp1_12()

    data[data == 0] = np.nan
    outlets = data.outlet.unique()
    outlets = sorted(outlets, key=lambda out: int(out.split()[1]))

    seaborn.set()

    b_plot = seaborn.catplot(x="outlet", y=data_attrib, data=data, order=outlets, kind="box",
                             aspect=2, legend=False)
    [plt.setp(ax.get_xticklabels(), rotation=90) for ax in b_plot.axes.flat]
    # plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    plt.tight_layout()
    plt.savefig("../../data/plots/exp2-" + data_attrib + ".png", transparent=True)
    plt.show()

    # outlet_means = data.groupby("outlet").mean()
    outlet_variances = data.groupby("outlet").var()
    variance = data.var()
    print(outlet_variances)
    print("\nOverall variance")
    print(variance)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Analyze PDU experiment results")
    parser.add_argument("-exp", type=str, required=True,
                        choices=["exp1-bulb1", "exp1-bulb2", "exp2-bulb1", "exp1-bulb1-2"])

    args = parser.parse_args()
    main(args.exp)
