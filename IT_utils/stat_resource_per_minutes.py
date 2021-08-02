# psutil 模块 用于监控：
# 安装 pip install psutil
import psutil
import time
from datetime import datetime
import os


# 监控cpu信息：
def cpu():
    #	cpu = psutil.cpu_count(False) cpu核数 默认逻辑cpu核数，False查看真实cpu核数；
    cpu_pers = psutil.cpu_percent(1, True)  # 每秒cpu使用率，（1，True） 每一核cpu的每秒使用率；
    cpu_per = sum(cpu_pers) / 100
    #	print(cpu_per)
    return cpu_per


# 监控内存信息：
def mem():
    #	mem = psutil.virtual_memory()   查看内存信息；
    # mem_total = int(psutil.virtual_memory()[0] / 1024 / 1024)
    mem_used = psutil.virtual_memory()[3] / 1024 / 1024 / 1024
    # mem_per = int(psutil.virtual_memory()[2])
    # mem_info = {
    #     'mem_total': mem_total,
    #     'mem_used': mem_used,
    #     'mem_per': mem_per
    # }
    return mem_used


# 监控硬盘使用率：
def disk():
    disk_data1 = psutil.disk_io_counters()
    time.sleep(1)
    disk_data2 = psutil.disk_io_counters()
    read_bytes =  disk_data2.read_bytes - disk_data1.read_bytes
    write_bytes =  disk_data2.write_bytes - disk_data1.write_bytes
    read_data = read_bytes / 1024 / 1024    # 每秒接受的Mb
    write_data = write_bytes / 1024 / 1024  # 每秒接受的Mb
    return read_data, write_data


# 监控网络流量：
def network():
    #	network = psutil.net_io_counters() #查看网络流量的信息；
    network_data1 = psutil.net_io_counters()
    time.sleep(1)
    network_data2 = psutil.net_io_counters()
    sent = network_data2[0] - network_data1[0]
    recv = network_data2[1] - network_data1[1]
    network_sent = sent / 1024 / 1024  # 每秒接受的Mb
    network_recv = recv / 1024 / 1024  # 每秒接受的Mb
    return network_sent,network_recv


def get_info():
    # cpu mem ioi ioo nioi nioo
    res = [0, 0, 0, 0, 0, 0]
    try:
        res[0] = cpu()              # CPU
        res[1] = mem()              # mem
        res[2], res[3] = disk()     # ioi ioo
        res[4], res[5] = network()  # nioi nioo
        pass
    except:
        pass

    return res
    pass


# 主函数，调用其他函数；
def main():
    out = open("info.txt", mode="w", encoding="UTF-8")
    head = 'cpu(N) mem(G) ioi(M) ioo(M) nioi(M) nioo(M)'.replace(" ", "\t")
    print(head)
    out.write(head + "\n")
    while True:
        info = get_info()
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        info_str_list =  [time_str] + ['{:.4f}'.format(v) for v in info]
        info_str = "\t".join(info_str_list)
        print(info_str)
        out.write(info_str + "\n")
        out.flush()
        # break
        time.sleep(60)
        pass
    pass


if __name__ == "__main__":
    main()
