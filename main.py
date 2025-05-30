import json
import threading
from parse_cgroups import *
import logging
from logging_config import setup_logging

# Set up logging. Only single instance of calibration_logger.log for every module
setup_logging()
logging = logging.getLogger(__name__)

import os
import struct
import sys
import ctypes

CGROUP_PATH = "/sys/fs/cgroup/memory/cluster_sync/"
MEMORY_OOM_CONTROL = os.path.join(CGROUP_PATH, "memory.oom_control")
CGROUP_EVENT_CONTROL = os.path.join(CGROUP_PATH, "cgroup.event_control")
libc = ctypes.CDLL("libc.so.6")

# In future i think we should have a function to check system load first. In case
# system under test is inder stress or OOM then our tool will cause further issues
# on the system.
#
# I will implement full functionality of this module later.
def load_checker():
    return True

def collect_data(cgroups, sampling_interval, sampling_time):
    """Thread function to collect data when system load is fine."""

    try:
        if load_checker():
            logging.info("Starting data collection")
            cgroup_parser(cgroups, sampling_interval, sampling_time)
            create_stats_from_sample()
            logging.info("Data collection completed")

    except Exception as e:
        logging.error("Exception in thread:", exc_info=True)

def main():
    sampling_interval = 6
    sampling_time = 60
    cgroups = ["cluster_sync", "cluster_health", "prism", "sys_stat_collector"]

    logging.info("Starting memTracker...\n")
    logging.info(f"Logging for total {sampling_time} seconds. Every {sampling_interval} interval")
    collect_data(cgroups, sampling_interval, sampling_time)

if __name__ == "__main__":
    main()

