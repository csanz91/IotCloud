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


def getHostMetrics():

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    disk_io = psutil.disk_io_counters()
    net_io = psutil.net_io_counters()

    hostMetrics = {
        "cpu_percent": psutil.cpu_percent(),
        "mem_used": mem.total - mem.available,
        "mem_percent": mem.percent,
        "swap_used": swap.used,
        "swap_percent": swap.percent,
        "disk_used": disk.used,
        "disk_percent": disk.percent,
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

    return hostMetrics
