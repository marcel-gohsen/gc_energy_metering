import datetime

from scipy.signal import find_peaks
from scipy.signal import peak_widths


def naiv(measurements, metric=None):
    return datetime.timedelta()


def peak(measurements, metric="active_power"):
    peak_indices, _ = find_peaks(measurements[metric])
    peak_start_index = 0

    if len(peak_indices) > 0:
        peak_start_index = peak_indices[0]

    return measurements.iloc[peak_start_index]["timestamp"] - measurements.iloc[0]["peak_time"]


def peak_start(measurements, metric="active_power"):
    peak_indices, _ = find_peaks(measurements[metric])
    peak_start_index = 0

    if len(peak_indices) > 0:
        peak_flank = peak_widths(measurements[metric], peak_indices)[2]
        peak_start_index = int(peak_flank[0])

    return measurements.iloc[peak_start_index]["timestamp"] - measurements.iloc[0]["peak_time"]
