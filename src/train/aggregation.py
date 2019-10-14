def mean(measurements, metric="active_power"):
    return measurements[metric].mean()  # W


def cumulate(measurements, metric="active_power"):
    return measurements[metric].sum()  # W


def mean_over_time(measurements, metric="active_power"):
    mean_power = measurements[metric].mean()

    run_time = measurements.iloc[0]["work_end_time"] - measurements.iloc[0]["work_begin_time"]

    return mean_power / run_time.total_seconds()  # W/s


def energy_naiv(measurements, metric="active_power"):
    mean_power = measurements[metric].mean()  # W

    begin = measurements.iloc[0]["timestamp"]
    end = measurements.iloc[len(measurements) - 1]["timestamp"]

    duration = (end - begin).total_seconds() / 3600  # h

    return mean_power * duration  # Wh


def energy_integration(measurements, metric="active_power"):
    sum = 0
    for i in range(len(measurements)):
        if i == 0 or i == len(measurements) - 1:
            sum += measurements.iloc[i][metric] / 2
        else:
            sum += measurements.iloc[i][metric]

    begin = measurements.iloc[0]["timestamp"]
    end = measurements.iloc[len(measurements) - 1]["timestamp"]

    duration = (end - begin).total_seconds() / 3600  # h

    return sum * (duration / len(measurements))  # Wh
