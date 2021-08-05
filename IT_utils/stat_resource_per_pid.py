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
# KB = MB = GB = 1


def cpu(proc):
    cpu_pers = proc.cpu_percent(False)
    cpu_per = cpu_pers / 100
    return cpu_per


# 监控内存信息：
def mem(proc):
    memory_info = proc.memory_info()
    rss_mem_used = memory_info.rss / GB
    vms_mem_used = memory_info.vms / GB
    return rss_mem_used, vms_mem_used


# 监控硬盘使用率：
def disk(proc):
    # disk_data1 = proc.io_counters()
    # time.sleep(1)
    # disk_data2 = proc.io_counters()
    # read_bytes = disk_data2.read_bytes - disk_data1.read_bytes
    # write_bytes = disk_data2.write_bytes - disk_data1.write_bytes
    # read_data = read_bytes / MB  # 每秒接受的Mb
    # write_data = write_bytes / MB  # 每秒接受的Mb
    disk_data = proc.io_counters()
    read_bytes = disk_data.read_bytes
    write_bytes = disk_data.write_bytes
    read_data = read_bytes / MB  # 每秒接受的Mb
    write_data = write_bytes / MB  # 每秒接受的Mb
    return read_data, write_data


# 监控网络流量：
def network(proc):
    a = proc.io_counters()
    print(a)
    network_data1 = proc.net_io_counters()
    time.sleep(1)
    network_data2 = proc.net_io_counters()
    sent = network_data2[0] - network_data1[0]
    recv = network_data2[1] - network_data1[1]
    network_sent = sent / MB  # 每秒接受的Mb
    network_recv = recv / MB  # 每秒接受的Mb
    return network_sent, network_recv


def get_info(proc):
    # cpu mem.rss mem.vms ioi ioo nioi nioo
    res = [0, 0, 0, 0, 0]
    try:
        res[0] = cpu(proc)  # CPU
        res[1], res[2] = mem(proc)  # mem
        res[3], res[4] = disk(proc)  # ioi ioo
        pass
    except:
        print("info error")
        pass

    return res
    pass


def get_info_all(main):
    all = [0, 0, 0, 0, 0]
    for proc in chain((main, ), main.children(recursive=True)):
        info = get_info(proc)
        all[0] += info[0]
        all[1] += info[1]
        all[2] += info[2]
        all[3] += info[3]
        all[4] += info[4]
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


def get_detail_info(proc):
    res = []
    while proc.is_running():
        info = get_info_all(proc)
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        res.append([time_str, info])
        info_str_list = [time_str] + ['{:.4f}'.format(v) for v in info]
        info_str = "\t".join(info_str_list)
        print(info_str)
        if proc.is_running():
            time.sleep(1)
        pass
    return res
    pass


def get_all_info(proc):
    res = {}
    cpu_times = proc.cpu_times()
    all_times = cpu_times.system + cpu_times.user
    res["cpu_time"] = all_times
    return res
    pass


def get_stat_info(pid):
    res = {}
    detail_info = []
    all_info = {}
    try:
        proc = psutil.Process(pid)
        res = {}
        detail_info = get_detail_info(proc)
        all_info = get_all_info(proc)
    except:
        print("stat info error")
        pass
    res["all"] = all_info
    res["detail"] = detail_info
    return res
    pass


def thread_run(cmd, q):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
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
    all_info = info.get("all", {})
    detail_info = info.get("detail", [])
    cpu_time = all_info.get("cpu_time", 0)
    mean_load = cpu_time / (1 if diff_time == 0 else diff_time)
    head_list = [diff_time, diff_time_format, cpu_time, mean_load]
    head_list += get_max_mean(detail_info, 0)  # cpu
    head_list += get_max_mean(detail_info, 1)  # rss
    head_list += get_max_mean(detail_info, 2)  # vms
    head_list += get_max_mean(detail_info, 3)  # ioi
    head_list += get_max_mean(detail_info, 4)  # ioo

    # print(head_list)
    head_list2 = [('{}'.format(v) if type(v) == type("") else '{:.4f}'.format(v)) for v in head_list]
    head = "\t".join(head_list2) + "\n\n"
    dirname = os.path.dirname(outfile)
    dirname = "." if dirname == "" else dirname
    os.makedirs(dirname, exist_ok=True)
    out = open(outfile, "w")
    headname_list_all = ["Run Time(s)", "Run Time", "CPU Time", "mean CPU Time"]
    headname_list_all += ["max CPU(N)", "mean CPU(N)", "max RSS(G)", "mean RSS(G)", "max VMS(N)", "mean VMS(N)"]
    headname_list_all += ["max IOI(N)", "mean IOI(N)", "max IOO(G)", "mean IOO(G)"]
    headname_all = "\t".join(headname_list_all) + "\n"
    out.write(headname_all)
    out.write(head)
    print(head)

    headname_list = ["Time", "CPU(N)", "RSS(G)", "VMS(G)", "IOI(M)", "IOO(M)"]
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

'''
运行时间
运行时间-格式化
CPU时间
平均CPU时间

最大cpu使用
平均cpu使用
最大常驻内存
平均常驻内存
最大虚拟内存
平均虚拟内存
最大读取IO
平均读取IO
最大写入IO
平均写入IO
最大发送网络
平均发送网络
最大接收网络
平均接收网络
'''


def test():
    pid = 4
    proc = psutil.Process(pid)
    # detail_info = get_detail_info(proc)
    # all_info = get_all_info(proc)
    res = [0, 0, 0, 0, 0, 0, 0]
    res[0] = cpu(proc)  # CPU
    res[1], res[2] = mem(proc)  # mem
    res[3], res[4] = disk(proc)  # ioi ioo
    proc.connections()
    # res[5], res[6] = network(proc)  # nioi nioo
    # print(detail_info)
    # print(all_info)
    print(res)
    pass

#
# def get_record(main):
#     # Memory measurements
#     rss, vms, uss, pss = 0, 0, 0, 0
#     # I/O measurements
#     io_in, io_out = 0, 0
#     check_io = True
#     # CPU seconds
#     cpu_usages = 0
#     # CPU usage time
#     cpu_time = 0
#     procs = {}
#     bench_record = {}
#     # Iterate over process and all children
#     # try:
#     this_time = time.time()
#     for proc in chain((main,), main.children(recursive=True)):
#         proc = procs.setdefault(proc.pid, proc)
#         with proc.oneshot():
#             if bench_record.get("prev_time"):
#                 cpu_usages += proc.cpu_percent() * (
#                         this_time - bench_record.get("prev_time")
#                 )
#             meminfo = proc.memory_full_info()
#             rss += meminfo.rss
#             vms += meminfo.vms
#             # uss += meminfo.uss
#             # pss += meminfo.pss
#
#             if check_io:
#                 try:
#                     ioinfo = proc.io_counters()
#                     io_in += ioinfo.read_bytes
#                     io_out += ioinfo.write_bytes
#                 except NotImplementedError as nie:
#                     # OS doesn't track IO
#                     check_io = False
#
#             cpu_times = proc.cpu_times()
#             cpu_time += cpu_times.user + cpu_times.system
#
#     bench_record.setdefault("prev_time", this_time)
#     if not bench_record.get("first_time"):
#         bench_record.setdefault("prev_time", this_time)
#
#     rss /= 1024 * 1024
#     vms /= 1024 * 1024
#     uss /= 1024 * 1024
#     pss /= 1024 * 1024
#
#     if check_io:
#         io_in /= 1024 * 1024
#         io_out /= 1024 * 1024
#     else:
#         io_in = None
#         io_out = None
#
#     # except psutil.Error as e:
#     #     return
#
#     # Update benchmark record's RSS and VMS
#     bench_record.setdefault("max_rss", max(bench_record.get("max_rss") or 0, rss))
#     bench_record.setdefault("max_vms", max(bench_record.get("max_vms") or 0, vms))
#     bench_record.setdefault("max_uss", max(bench_record.get("max_uss") or 0, uss))
#     bench_record.setdefault("max_pss", max(bench_record.get("max_pss") or 0, pss))
#
#     bench_record.setdefault("io_in", io_in)
#     bench_record.setdefault("io_out", io_out)
#
#     bench_record.setdefault("cpu_usages", cpu_usages)
#     bench_record.setdefault("cpu_time", cpu_time)
#
#     return bench_record


def test2():
    pid = 65440
    proc = psutil.Process(pid)
    out = get_record(proc)
    print(out)
    pass


if __name__ == "__main__":
    # test2()
    main()
