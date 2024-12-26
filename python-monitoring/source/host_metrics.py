import logging
import logging.config
import time

import psutil

import utils

logger = logging.getLogger(__name__)

disk_io_read_bytes_rate = utils.MetricRate()
disk_io_write_bytes_rate = utils.MetricRate()
net_bytes_sent_rate = utils.MetricRate()
net_bytes_recv_rate = utils.MetricRate()
disk_rates = {}
nic_rates = {}


def getHostMetrics():

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    if not disk:
        logger.error("Disk usage not available.")
        return
    bck_disk = psutil.disk_usage("/mnt/data")
    disk_io = psutil.disk_io_counters()
    if not disk_io:
        logger.error("Disk IO counters not available.")
        return
    net_io = psutil.net_io_counters()

    return {
        "cpu_percent": psutil.cpu_percent(),
        "mem_used": mem.total - mem.available,
        "mem_percent": mem.percent,
        "swap_used": swap.used,
        "swap_percent": swap.percent,
        "disk_used": disk.used,
        "disk_percent": disk.percent,
        "bck_disk_used": bck_disk.used,
        "bck_disk_percent": bck_disk.percent,
        "disk_io_read_bytes": disk_io.read_bytes,
        "disk_io_read_bytes_rate": disk_io_read_bytes_rate.getRate(disk_io.read_bytes),
        "disk_io_write_bytes": disk_io.write_bytes,
        "disk_io_write_bytes_rate": disk_io_write_bytes_rate.getRate(
            disk_io.write_bytes
        ),
        "disk_io_read_time": disk_io.read_time,
        "disk_io_write_time": disk_io.write_time,
        "net_bytes_sent": net_io.bytes_sent,
        "net_bytes_sent_rate": net_bytes_sent_rate.getRate(net_io.bytes_sent),
        "net_bytes_recv": net_io.bytes_recv,
        "net_bytes_recv_rate": net_bytes_recv_rate.getRate(net_io.bytes_recv),
        "up_time": time.time() - psutil.boot_time(),
    }


def getDiskMetrics():
    disk_io_perdisk = psutil.disk_io_counters(perdisk=True)

    disk_io_stats = {}
    for d in disk_io_perdisk.keys():
        if d not in disk_rates:
            disk_rates[d] = {
                "read_bytes_rate": utils.MetricRate(),
                "write_bytes_rate": utils.MetricRate(),
            }

    for d, stats in disk_io_perdisk.items():
        disk_io_stats[d] = {
            "read_bytes": stats.read_bytes,
            "write_bytes": stats.write_bytes,
            "read_time": stats.read_time,
            "write_time": stats.write_time,
            "read_bytes_rate": disk_rates[d]["read_bytes_rate"].getRate(stats.read_bytes),
            "write_bytes_rate": disk_rates[d]["write_bytes_rate"].getRate(stats.write_bytes),
        }

    return disk_io_stats


def getNetMetrics():
    net_io_pernic = psutil.net_io_counters(pernic=True)

    net_io_stats = {}
    for nic in net_io_pernic.keys():
        if nic not in nic_rates:
            nic_rates[nic] = {
                "bytes_sent_rate": utils.MetricRate(),
                "bytes_recv_rate": utils.MetricRate(),
            }

    for nic, stats in net_io_pernic.items():
        net_io_stats[nic] = {
            "bytes_sent": stats.bytes_sent,
            "bytes_recv": stats.bytes_recv,
            "packets_sent": stats.packets_sent,
            "packets_recv": stats.packets_recv,
            "errin": stats.errin,
            "errout": stats.errout,
            "dropin": stats.dropin,
            "dropout": stats.dropout,
            "bytes_sent_rate": nic_rates[nic]["bytes_sent_rate"].getRate(stats.bytes_sent),
            "bytes_recv_rate": nic_rates[nic]["bytes_recv_rate"].getRate(stats.bytes_recv),
        }

    return net_io_stats
