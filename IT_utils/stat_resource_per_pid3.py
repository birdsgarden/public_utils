#!/usr/bin/env python3

import sys
import os
import re
import psutil
from datetime import datetime
import time
# from matplotlib import pyplot as plt
import argparse
import subprocess
import multiprocessing as mp
from itertools import chain

KB = 1024
MB = KB * 1024
GB = MB * 1024
NLEN = 7


# KB = MB = GB = 1


def get_proc_info(proc):
    res = [0] * NLEN
    with proc.oneshot():
        cpu_pers = proc.cpu_percent(False)
        cpu_times = proc.cpu_times()
        cpu_times_systems = cpu_times.system
        cpu_times_users = cpu_times.user
        memory_info = proc.memory_info()
        rss_mem_used = memory_info.rss
        vms_mem_used = memory_info.vms
        disk_data = proc.io_counters()
        read_bytes = disk_data.read_bytes
        write_bytes = disk_data.write_bytes
        res = [cpu_pers, cpu_times_systems, cpu_times_users]
        res += [rss_mem_used, vms_mem_used]
        res += [read_bytes, write_bytes]
        # cpu_count system user rss vms ioi ioo
    return res
    pass


def get_info_all(main):
    all = [0] * NLEN
    try:
        for proc in chain((main,), main.children(recursive=True)):
            info = get_proc_info(proc)
            for i in NLEN:
                all[i] += info[i]
    except Exception as e:
        # print(e)
        pass
    return all
    pass


def parse_arguments():
    if len(sys.argv) < 3:
        print("python stat_resource_per_pid.py out.stat -- command")
        sys.exit()
    outfile = sys.argv[1]
    args = sys.argv[2:]
    return outfile, args
    pass


def get_real_info(last_info, info):
    res = [0] * NLEN
    res[0] = info[0]
    for i in range(1, NLEN):
        res[i] = info[i] - last_info[i]
        if res[i] < 0:
            res[i] = 0
    return res
    pass


def norm_info(info):
    # cpu_count system user rss vms ioi ioo
    res = info
    for i in range(3, 5):
        res[i] = info[i] / GB
        pass
    for i in range(5, 7):
        res[i] = info[i] / MB
        pass
    return res
    pass


def get_detail_info(proc):
    last_info = [0] * NLEN
    detail_info = []
    while proc.is_running():
        try:
            # print(proc.status())
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            info = get_proc_info(proc)
            real_info = get_real_info(last_info, info)
            last_info = info
            real_info = norm_info(real_info)
            detail_info.append([time_str, real_info])
            time.sleep(1)
        except Exception as e:
            # print(e)
            pass
        pass
    last_info = norm_info(last_info)
    return last_info, detail_info
    pass


def get_stat_info(pid):
    res = {}
    detail_info = []
    all_info = {}
    try:
        proc = psutil.Process(pid)
        res = {}
        last_info, detail_info = get_detail_info(proc)
        all_info = last_info
    except Exception as e:
        # print(e)
        print("stat info error")
        pass
    res["all"] = all_info
    res["detail"] = detail_info
    return res
    pass


def thread_run(cmd, q):

    process = subprocess.Popen(cmd_str, shell=True, env=os.environ)
    # process = subprocess.Popen(cmd_str, shell=True, env=os.environ, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    q.put(process.pid)
    process.wait()
    pass


def run_command(cmd):
    q = mp.Queue()
    p = mp.Process(target=thread_run, args=(cmd, q))
    p.start()
    pid = q.get()
    info = get_stat_info(pid)
    p.join()
    p.close()
    return info


def format_diff_time(diff):
    diff_int = int(diff)
    s = diff_int % 60
    m_int = diff // 60
    m = m_int % 60
    h_int = m_int // 60
    h = h_int
    res = '{}:{}:{}'.format(h, m, s)
    return res
    pass


def get_max_mean(data, idx):
    nlen = len(data)
    if nlen == 0:
        return 0, 0
    sum_value = 0
    max_value = 0
    for ln in data:
        v = float(ln[1][idx])
        sum_value += v
        if v > max_value:
            max_value = v
    mean_value = sum_value / nlen
    return max_value, mean_value
    pass


def write_stat(start_time, end_time, info, outfile):
    outfile = "out.stat" if outfile is None else outfile
    diff_time = int(end_time - start_time)
    diff_time_format = format_diff_time(diff_time)
    all_info = info.get("all", [0] * NLEN)
    detail_info = info.get("detail", [])
    cpu_time = all_info[0]
    system_time = all_info[1]
    user_time = all_info[2]
    diff_time = system_time + user_time
    diff_time_format = format_diff_time(diff_time)

    mean_load = cpu_time / (1 if diff_time <= 0 else diff_time)
    head_list = [diff_time, diff_time_format, cpu_time, mean_load]
    # cpu_count system user rss vms ioi ioo
    for i in range(NLEN):
        head_list += get_max_mean(detail_info, i)

    # print(head_list)
    head_list2 = [('{}'.format(v) if type(v) == type("") else '{:.4f}'.format(v)) for v in head_list]
    head = "\t".join(head_list2) + "\n\n"
    dirname = os.path.dirname(outfile)
    dirname = "." if dirname == "" else dirname
    os.makedirs(dirname, exist_ok=True)
    out = open(outfile, "w")
    headname_list_all = ["Run Time(s)", "Run Time", "CPU Time", "mean CPU Time"]
    headname_list_all += ["max CPU(N)", "mean CPU(N)", "max System(s)", "mean System(s)", "max User(s)", "mean User(s)"]
    headname_list_all += ["max RSS(G)", "mean RSS(G)", "max VMS(G)", "mean VMS(G)"]
    headname_list_all += ["max IOI(M)", "mean IOI(M)", "max IOO(M)", "mean IOO(M)"]
    headname_all = "\t".join(headname_list_all) + "\n"
    out.write(headname_all)
    out.write(head)
    # print(head)

    headname_list = ["Time", "CPU(N)", "System(s)", "User(s)", "RSS(G)", "VMS(G)", "IOI(M)", "IOO(M)"]
    headname = "\t".join(headname_list) + "\n"
    out.write(headname)
    for di in detail_info:
        info = di[1]
        time_str = di[0]
        info_str_list = [time_str] + ['{:.4f}'.format(v) for v in info]
        info_str = "\t".join(info_str_list)
        out.write(info_str + "\n")
        out.flush()
    out.close()
    pass


def get_cmd(argv):
    if len(argv) < 1:
        print("please give an command to run")
        sys.exit()
    # res = " ".join(["{}".format(v) for v in argv])
    res = " ".join(['"{}"'.format(v) for v in cmd])
    return argv
    pass


def main():
    output, argv = parse_arguments()
    command = get_cmd(argv)
    start_time = time.time()
    info = run_command(command)
    end_time = time.time()
    write_stat(start_time, end_time, info, output)
    pass


if __name__ == "__main__":
    main()
