#!/usr/bin/env python

import os
import time
import json
import argparse
import urllib.request as urllib2

from datetime import datetime
from cluster.cluster_sync import cluster_sync_utils
from util.base.command import timed_command
import util.base.log as log

CGROUPS = ["cluster_health", "hera"]
BASE_PATH = "/sys/fs/cgroup/memory"
OUTPUT_FILE = "/var/log/memtrack/cgroup_data.json"

def get_prism_leader_details():
    try:
        url = "http://localhost:2019/prism/leader"
        response = urllib2.urlopen(url, timeout=15)
        body = response.read()
        json_body = json.loads(body)
        return json_body["leader"].split(":")[0], json_body["is_local"]
    except Exception as ex:
        log.ERROR(f"Error fetching Prism leader: {ex}")
        return None, None

def is_elected_node():
    hostname = cluster_sync_utils.get_local_ip()
    leader, is_local = get_prism_leader_details()
    if is_local:
        return True
    try:
        nodes = cluster_sync_utils.get_cluster_ips()
        non_leaders = [n for n in nodes if n != leader]
        return hostname == non_leaders[0] if non_leaders else False
    except Exception as ex:
        log.ERROR(f"Failed to determine node eligibility: {ex}")
        return False

def read_usage(cgroup):
    cmd = f"sudo_wrapper cat {BASE_PATH}/{cgroup}/memory.usage_in_bytes"
    ret, stdout, stderr = timed_command(cmd, timeout_secs=5, ignore_exception=True)
    if ret != 0:
        log.ERROR(f"Cmd failed: {cmd}, stdout: {stdout}, stderr: {stderr}")
        return None
    try:
        return int(stdout.decode("utf-8").strip().split()[0])
    except Exception as ex:
        log.ERROR(f"Parse error: {stdout}, {ex}")
        return None

class MemoryTracker:
    def __init__(self, hostname, cgroup, interval):
        self.hostname = hostname
        self.cgroup = cgroup
        self.interval = interval
        self.start = None
        self.start_usage = None
        self.bitmap = []
        self.deltas = []
        self.last_usage = None

    def add_sample(self, usage, timestamp):
        if self.start is None:
            self.start = int(timestamp)
            self.start_usage = usage
            self.last_usage = usage
            self.bitmap.append(1)
            return

        expected_slot = int((timestamp - self.start) / self.interval)
        current_slot = len(self.bitmap)

        while current_slot < expected_slot:
            self.bitmap.append(0)
            self.deltas.append(-1)
            current_slot += 1

        self.bitmap.append(1)
        self.deltas.append(usage - self.last_usage)
        self.last_usage = usage

    def to_dict(self):
        return {
            "hostname": self.hostname,
            "cgroup": self.cgroup,
            "start": self.start,
            "interval": self.interval,
            "bitmap": ''.join(map(str, self.bitmap)),
            "start_usage": self.start_usage,
            "usage_deltas": self.deltas,
        }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, required=True, help="Total run duration (seconds)")
    parser.add_argument("--interval", type=int, required=True, help="Interval between samples (seconds)")
    args = parser.parse_args()

    if not is_elected_node():
        print("[SKIP] Node not elected to collect.")
        return

    hostname = cluster_sync_utils.get_local_ip()
    trackers = {cg: MemoryTracker(hostname, cg, args.interval) for cg in CGROUPS}
    end_time = time.time() + args.duration

    while time.time() < end_time:
        timestamp = int(time.time())
        for cgroup in CGROUPS:
            usage = read_usage(cgroup)
            if usage is not None:
                trackers[cgroup].add_sample(usage, timestamp)
        time.sleep(args.interval)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    all_data = [tracker.to_dict() for tracker in trackers.values()]
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_data, f, indent=2)
    print(f"[OK] Saved data to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
