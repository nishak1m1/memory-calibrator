#!/usr/bin/env python
#
# Copyright (c) 2025 Nutanix Inc. All rights reserved.
#
# Author: triyasha.ghosh@nutanix.com
#

VIRTUALENV_PATH = "/home/nutanix/cluster/.venv/bin/bin/python3.9"

import os
if os.path.exists(VIRTUALENV_PATH):
  if os.environ.get("PYTHON_TARGET_VERSION") is None:
    os.environ["PYTHON_TARGET_VERSION"] = "3.9"

  if os.environ.get("PYTHON_TARGET_PATH") is None:
    os.environ["PYTHON_TARGET_PATH"] = VIRTUALENV_PATH

import env
import sys

import gflags
FLAGS = gflags.FLAGS
gflags.FLAGS([])

from cluster.cluster_sync import cluster_sync_utils
from util.base.command import timed_command

import subprocess
import argparse
from datetime import datetime
import time
import urllib.request as urllib2
import util.base.log as log
import json
import requests

CGROUPS = ["cluster_health", "hera"]
BASE_PATH = "/sys/fs/cgroup/memory"
API_ENDPOINT = "http://10.111.48.227:8001/submit"  # This is temporary for trial
# TODO: How to expose this if we are going to add this to cluster? GFlag?

def get_prism_leader_details():
    prism_leader_query_url = "http://localhost:2019/prism/leader"
    try:
        response = urllib2.urlopen(prism_leader_query_url, timeout=15)
        body = response.read()
        log.INFO("Prism leader details : %s" % body)
        json_body = json.loads(body)
        leader = json_body["leader"].split(":")[0]
        is_local = json_body["is_local"]
        return leader, is_local
    except Exception as ex:
        log.ERROR("Failed to fetch prism leader details. %s." % ex)
        return None, None
    
    
def is_leader():
    _, is_leader = get_prism_leader_details()
    return is_leader

def get_first_non_leader():
    nodes = cluster_sync_utils.get_cluster_ips()
    try:
        nodes = cluster_sync_utils.get_cluster_ips()
        log.INFO("Nodes fetched: %s." % nodes)
        leader, _ = get_prism_leader_details() 
        non_leaders = [n for n in nodes if n != leader]
        return non_leaders[0] if non_leaders else None
    except Exception as e:
        log.ERROR(f"Failed to get non-leader node: {e}")
        return None

def read_max_usage(cgroup):
    # Get current memory usage.
    cmd = "sudo_wrapper cat /sys/fs/cgroup/memory/%s/memory.max_usage_in_bytes" % cgroup

    ret, stdout, stderr = timed_command(cmd, timeout_secs=5,ignore_exception=True)
    if ret != 0:
        log.ERROR("Unable to execute cmd: %s,\nret: %s,\n stdout: %s,"
                  "\nstderr: %s" % (cmd, ret, stdout, stderr))
        return None

    stdout = stdout.decode("utf-8")
    stderr = stderr.decode('utf-8')

    try:
        current_consumption_max = int(stdout.split()[0])
        return current_consumption_max
    except Exception as ex:
        log.ERROR("Failed to parse consumption from stdout: %s with exception: "
                  "%s" % (stdout, ex))
        return None

def push_to_api(hostname, cgroup, usage):
    payload = {
        "hostname": hostname,
        "cgroup": cgroup,
        "max_usage": usage,
        "timestamp": datetime.now().isoformat()
    }
    try:
        res = requests.post(API_ENDPOINT, json=payload)
        res.raise_for_status()
        print(f"[OK] Data pushed for {cgroup}")
    except requests.RequestException as e:
        print(f"[ERR] API push failed for {cgroup}: {e}")

def collect_and_push():
    hostname = cluster_sync_utils.get_local_ip()
    elected = is_leader() or hostname == get_first_non_leader()

    if not elected:
        print(f"[SKIP] Node {hostname} is not elected to push.")
        return

    for cgroup in CGROUPS:
        usage = read_max_usage(cgroup)
        if usage is not None:
            push_to_api(hostname, cgroup, usage)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, required=True, help="Total run duration in seconds")
    parser.add_argument("--interval", type=int, required=True, help="Interval between runs in seconds")
    args = parser.parse_args()

    end_time = time.time() + args.duration

    while time.time() < end_time:
        collect_and_push()
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
