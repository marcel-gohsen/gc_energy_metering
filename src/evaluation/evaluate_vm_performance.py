import os
import pandas as pd
import seaborn
import matplotlib.pyplot as plt


def load_data(file_dir):
    data = []
    for file_name in os.listdir(file_dir):
        if file_name.endswith("measurements.txt"):
            condition = file_name.replace("-measurements.txt", "")

            if condition == "vm-idle":
                condition = "Idle"
            elif condition == "vm-ol-1hz":
                condition = "Office Logger @ 1Hz"
            elif condition == "vm-ol-max":
                condition = "Office Logger"
            elif condition == "vm-ol-0_5hz":
                condition = "Office Logger @ 0.5Hz"
            elif condition == "vm-ol-0_25hz":
                condition = "Office Logger @ 0.25Hz"

            with open(os.path.join(file_dir, file_name)) as in_file:
                for line in in_file:
                    if line.startswith("TotalSeconds"):
                        duration = float(line.split(": ")[1])

                        data.append({"condition": condition, "duration": duration})

    return pd.DataFrame(data)


def main():
    data = load_data("../../data/vm-performance")

    ax = seaborn.boxplot(x="condition", y="duration", data=data,
                         order=["Idle", "Office Logger @ 0.25Hz", "Office Logger @ 0.5Hz", "Office Logger @ 1Hz", "Office Logger"])

    ax.set(xlabel="Condition", ylabel="Execution time [s]")
    ax.set_xticklabels(labels=ax.get_xticklabels(), rotation=15)
    plt.tight_layout()
    plt.savefig("../../data/plots/vm-ol-performance.png", transparent=True)
    plt.show()


if __name__ == '__main__':
    main()
