def mean(measurements):
    return measurements["active_power"].mean()  # W


def cumulate(measurements):
    return measurements["active_power"].sum()  # W


def mean_over_time(measurements):
    mean_power = measurements["active_power"].mean()

    run_time = measurements.iloc[0]["work_end_time"] - measurements.iloc[0]["work_begin_time"]

    return mean_power / run_time.total_seconds()  # W/s


def energy_naiv(measurements):
    mean_power = measurements["active_power"].mean()  # W

    begin = measurements.iloc[0]["timestamp"]
    end = measurements.iloc[len(measurements) - 1]["timestamp"]

    duration = (end - begin).total_seconds() / 3600  # h

    return mean_power * duration  # Wh


def energy_integration(measurements):
    sum = 0
    for i in range(len(measurements)):
        if i == 0 or i == len(measurements) - 1:
            sum += measurements.iloc[i]["active_power"] / 2
        else:
            sum += measurements.iloc[i]["active_power"]

    begin = measurements.iloc[0]["timestamp"]
    end = measurements.iloc[len(measurements) - 1]["timestamp"]

    duration = (end - begin).total_seconds() / 3600  # h

    return sum * (duration / len(measurements))  # Wh
