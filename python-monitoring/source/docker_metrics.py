import logging
import logging.config
from collections import defaultdict

import docker

import utils

logger = logging.getLogger(__name__)

containerNetRate = defaultdict(utils.MetricRate)


def getContainerName(container):
    return container.name.split(".")[0]


def getContainerCpu(data):
    """Calculates the percentage of CPU usage.
    :param data: docker statistics coded as a dictionary.
    :return: percentage of cpu usage.
    """
    cpu_percent = 0.0

    cpu_count = len(data["cpu_stats"]["cpu_usage"]["percpu_usage"])

    cpu_delta = float(data["cpu_stats"]["cpu_usage"]["total_usage"]) - float(
        data["precpu_stats"]["cpu_usage"]["total_usage"]
    )

    system_delta = float(data["cpu_stats"]["system_cpu_usage"]) - float(
        data["precpu_stats"]["system_cpu_usage"]
    )

    if system_delta > 0.0:
        cpu_percent = cpu_delta / system_delta * 100.0 * cpu_count

    return cpu_percent


def getContainerMem(data):
    """Calculates the percentage of memory usage.
    :param data: docker statistics coded as a dictionary.
    :return: percentage of memory usage.
    """
    mem_percent = 0.0

    mem_usage = float(data["memory_stats"]["usage"])

    mem_limit = float(data["memory_stats"]["limit"])

    if mem_limit > 0.0:
        mem_percent = mem_usage / mem_limit * 100

    return mem_percent


def getContainerNet(data):
    """Calculates the net usage of a container
    :param data: docker statistics coded as a dictionary.
    :return: tx and rx network transfered bytes
    """
    tx_bytes = 0
    rx_bytes = 0

    for interfaceData in data["networks"].values():
        tx_bytes += interfaceData["tx_bytes"]
        rx_bytes += interfaceData["rx_bytes"]

    return tx_bytes, rx_bytes


def getContainerMetrics(container):
    metrics = {}
    containerName = getContainerName(container)
    data = container.stats(stream=False)
    metrics["cpu"] = getContainerCpu(data)
    metrics["mem"] = getContainerMem(data)
    tx_bytes, rx_bytes = getContainerNet(data)
    metrics["tx_bytes"] = tx_bytes
    metrics["rx_bytes"] = rx_bytes
    metrics["tx_bytes_rate"] = containerNetRate[f"{containerName}_tx_bytes"].getRate(
        tx_bytes
    )
    metrics["rx_bytes_rate"] = containerNetRate[f"{containerName}_rx_bytes"].getRate(
        rx_bytes
    )

    return metrics


def getContainersMetrics():

    containersMetrics = {}
    for container in dockerClient.containers.list():
        containerName = getContainerName(container)
        containersMetrics[containerName] = {}
        containersMetrics[containerName]["status"] = container.status
        if container.status == "running":
            try:
                containersMetrics[containerName] = getContainerMetrics(container)
            except KeyError:
                # If a container is booting up, some of the metrics could not be available
                pass
    return containersMetrics


dockerClient = docker.from_env()
