import datetime

from scipy.signal import find_peaks
from scipy.signal import peak_widths


def naiv(measurements):
    return datetime.timedelta()


def peak(measurements):
    peak_indices, _ = find_peaks(measurements["active_power"])
    peak_start_index = 0

    if len(peak_indices) > 0:
        peak_start_index = peak_indices[0]

    return measurements.iloc[peak_start_index]["timestamp"] - measurements.iloc[0]["peak_time"]


def peak_start(measurements):
    peak_indices, _ = find_peaks(measurements["active_power"])
    peak_start_index = 0

    if len(peak_indices) > 0:
        peak_flank = peak_widths(measurements["active_power"], peak_indices)[2]
        peak_start_index = int(peak_flank[0])

    return measurements.iloc[peak_start_index]["timestamp"] - measurements.iloc[0]["peak_time"]
