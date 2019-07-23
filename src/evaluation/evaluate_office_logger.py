import os
import pandas as pd
import json
import dateutil
import datetime
import re
import time
import sys
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn

import mysql.connector as mysql

etime_pattern = re.compile("[:-]")


def insert_data_to_db(path, connection, cursor):
    for root, dirs, files in os.walk(path):
        for file in files:
            if file == "log.jsonld" and "log.jsonld.idx" not in files:
                with open(os.path.join(root, file)) as file:
                    start = time.time()

                    for line in file:
                        values = json.loads(line)

                        insert_processes(values, cursor, connection)

                        if time.time() - start >= 1:
                            print("\r" + str(values["timestamp"]), end="")
                            start = time.time()

                with open(os.path.join(root, file) + ".idx", "w+"):
                    pass


def insert_processes(values, cursor, connection):
    process_values = values["processes"]

    processes = []
    process_stats = []
    windows = []
    window_titles = []

    for process_value in process_values:
        if process_value["cmd_name"] != "ps":
            try:
                start_time = dateutil.parser.parse(process_value["start"]).isoformat()

                process = (
                    process_value["pid"],
                    start_time,
                    process_value["ppid"],
                    process_value["pgid"],
                    process_value["user"],
                    process_value["cmd_name"],
                    process_value["cmd"]
                )

                elapsed_time = str(parse_timedelta(process_value["etime"])).replace("days, ", "").replace("day, ", "")
                cpu_time = str(parse_timedelta(process_value["ctime"])).replace("days, ", "").replace("day, ", "")

                process_stat = (
                    values["timestamp"],
                    process_value["pid"],
                    start_time,
                    elapsed_time,
                    cpu_time,
                    process_value["%cpu"],
                    process_value["%mem"],
                    str(int(float(process_value["mem"]) * 1024.0)),
                    process_value["psr"]
                )

                for window_value in process_value["windows"]:
                    win_id = str(int(window_value["win_id"], base=16))

                    window = (
                        win_id,
                        process[0],
                        start_time,
                        window_value["wm-class"]
                    )

                    windows.append(window)

                    window_title = (
                        win_id,
                        window_value["title"],
                        values["timestamp"]
                    )

                    window_titles.append(window_title)

            except ValueError:
                process = None
                process_stat = None

            if process is not None:
                processes.append(process)

            if process_stat is not None:
                process_stats.append(process_stat)

    query_process = "INSERT INTO process VALUES " + (",".join([str(x) for x in processes])) + ";"
    query_process_stats = "INSERT INTO process_stats " \
                          "(timestamp, pid, start_time, elapsed_time, cpu_time, cpu_util, mem_util, mem, psr) " \
                          "VALUES " + (",".join([str(x) for x in process_stats])) + ";"

    query_windows = "INSERT IGNORE INTO window VALUES " + (",".join([str(x) for x in windows])) + ";"
    query_window_titles = "INSERT IGNORE INTO window_title VALUES " + (",".join([str(x) for x in window_titles])) + ";"

    focused_window = values["focussed_window"]
    if focused_window is not None:
        focus_win_id = str(int(values["focussed_window"]["win_id"], base=16))
    else:
        focus_win_id = "NULL"

    overall = (
        values["timestamp"],
        focus_win_id,
        values["%cpu"],
        values["mem_total"],
        values["mem_available"],
        values["mem_used"]
    )

    query_overall = ("INSERT INTO overall_stats VALUES " + str(overall) + ";").replace("\'NULL\'", "NULL")

    exec_sql(cursor, connection, query_process)
    exec_sql(cursor, connection, query_windows)
    exec_sql(cursor, connection, query_window_titles)
    exec_sql(cursor, connection, query_overall)
    exec_sql(cursor, connection, query_process_stats)


def exec_sql(cursor, connection, query):
    try:
        cursor.execute(query)
        connection.commit()
    except mysql.errors.IntegrityError as err:
        if "Duplicate entry" not in err.msg:
            print("\n" + query)
            print("\n\n" + err.msg + "\n\n", file=sys.stderr)
            exit(1)


def parse_timedelta(value):
    global etime_pattern

    time = etime_pattern.split(value)
    time = [int(x) for x in time]

    while len(time) != 4:
        time.insert(0, 0)

    return datetime.timedelta(days=time[0], hours=time[1], minutes=time[2], seconds=time[3])


def plot_performance(cursor):
    # cursor.execute("SELECT process.pid, timestamp, cpu_util, mem FROM process " +
    #                "JOIN process_stats ON process.pid = process_stats.pid " +
    #                "JOIN overall_stats ON process_stats.timestamp = overall_stats.timestamp " +
    #                "WHERE process.pid = " + str(pid) + ";")
    # rows = cursor.fetchall()

    cursor.execute("SELECT timestamp, cpu_util, (mem_used / 1024 / 1024 / 1024) FROM overall_stats;")
    rows = cursor.fetchall()

    data = pd.DataFrame.from_records(rows, columns=["timestamp", "cpu_util", "mem_used"], coerce_float=True)

    f, axes = plt.subplots(2, 1)

    seaborn.lineplot(x="timestamp", y="cpu_util", data=data, ax=axes[0])
    axes[0].set_xlabel("time")
    axes[0].set_ylabel("CPU utilization [%]")
    axes[0].xaxis.set_major_locator(mdates.AutoDateLocator())
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%H:%Mh"))

    seaborn.lineplot(x="timestamp", y="mem_used", data=data, ax=axes[1])
    axes[1].set_xlabel("time")
    axes[1].set_ylabel("Mem usage [GB]")
    axes[1].xaxis.set_major_locator(mdates.AutoDateLocator())
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%Mh"))

    # data = pd.DataFrame.from_records(rows, columns=["pid", "timestamp", "cpu_util", "mem"])
    # seaborn.lineplot(x="timestamp", y="mem", data=data)
    plt.tight_layout()
    plt.savefig("../../data/plots/ol_overall_performance.png", transparent=True)
    plt.show()


def focus_correlation(cursor):
    # firefox
    pid = 20831

    # intellij
    # pid = 15353

    # pycharm
    # pid = 14035

    # thunderbird
    # pid = 10995

    # libreoffice
    # pid = 14845

    # terminal
    # pid = 7000

    # nautilus
    # pid = 7159

    cursor.execute("SELECT os.timestamp, ps.cpu_util, os.cpu_util as o_cpu FROM overall_stats AS os " +
                   "JOIN `window` AS w ON os.focus_win_id = w.id " +
                   "JOIN process_stats AS ps ON ps.timestamp = os.timestamp AND ps.pid = w.pid " +
                   "WHERE w.pid = " + str(pid) + ";")

    cpu_focus = pd.DataFrame.from_records(cursor.fetchall(), columns=["timestamp", "cpu_util", "o_cpu_util"])

    cursor.execute("SELECT ps.timestamp, ps.cpu_util, os.cpu_util as o_cpu FROM process_stats AS ps " +
                   "JOIN overall_stats as os ON os.timestamp = ps.timestamp WHERE pid = " + str(pid) + ";")
    cpu_all = pd.DataFrame.from_records(cursor.fetchall(), columns=["timestamp", "cpu_util", "o_cpu_util"])
    cpu_all["in_focus"] = cpu_all["timestamp"].isin(cpu_focus["timestamp"])
    cpu_all["in_focus"] = pd.to_numeric(cpu_all["in_focus"])

    cpu_not_focus = cpu_all[cpu_all["timestamp"].isin(cpu_focus["timestamp"]) == False]

    f, axes = plt.subplots(1, 1)

    boxplot = seaborn.boxplot(x="in_focus", y="o_cpu_util", data=cpu_all)
    boxplot.set_xlabel("Is in focus?")
    boxplot.set_ylabel("Overall CPU utilization [%]")
    boxplot.set_xticklabels(["No", "yes"])


    print("In focus: " + str(len(cpu_focus)) + "s")
    print("Not in focus: " + str(len(cpu_not_focus)) + "s")
    print(cpu_all.corr("pearson"))

    plt.tight_layout()
    plt.savefig("../../data/plots/ol_firefox_correlation.png", transparent=True)
    plt.show()


def main():
    connection = mysql.connect(
        user="root",
        password="amneziaHAZE",
        database="gc2_office_logger",
        host="localhost"
    )

    cursor = connection.cursor()
    insert_data_to_db("../../data/office-logger-logs", connection, cursor)

    # plot_performance(cursor)
    focus_correlation(cursor)


if __name__ == '__main__':
    main()
