#!/usr/bin/env python
import time
import copy
import json
import os
import sys
import re
import string

import multiprocessing
import commands

from subprocess import Popen, PIPE
from random import random
from os import path


from copy import copy


# http://www.linuxatemyram.com/
def memory():
    "Total and free mem in bytes"

    with open('/proc/meminfo') as f:
        lines = f.readlines()

    # in kB
    info = {}

    for line in lines:
        m = re.search('(\w+):\s*(\d+)', line)
        if m:
            info[m.group(1)] = int(m.group(2))

    used = info['MemTotal'] - info['MemFree'] - \
        info['Buffers'] - info['Cached']

    # http://www.linuxatemyram.com/
    return {
        "total": info['MemTotal'] * 1024,
        # used by applications, not cache
        "used": used * 1024,
        "percent": int((100 * used) / info['MemTotal']),
    }


def uptime():
    "Uptime in seconds"

    with open('/proc/uptime', 'r') as f:
        line = f.readline()

    seconds = line.partition(' ')[0]
    seconds = float(seconds)

    return int(seconds)


def started():
    "Unix time when the server was started"
    return int(time.time() - uptime())


def cpu_load():
    "return normalised % load (avg num of processes waiting per processor)"

    load = os.getloadavg()[0]
    load = load / multiprocessing.cpu_count()
    return int(load * 100)


def storage():
    "Return used and total disk space in bytes"
    df = commands.getstatusoutput('df --total | grep total')

    if df[0]:
        raise Exception('Failed to run df command')

    bits = re.findall(r"(\d+)", df[1], re.M)

    if not bits:
        raise Exception('Invalid output from df command')

    total = int(bits[0]) * 1024
    used = int(bits[1]) * 1024

    return {
        "total": total,
        "used": used,
        "percent": int((100 * used) / total)
    }


def ups():
    "Get UPS stats from apcupsd via apcaccess"

    if not path.exists('/sbin/apcaccess'):
        raise Exception('/sbin/apcaccess not found')

    dump = commands.getstatusoutput('/sbin/apcaccess')

    if dump[0]:
        raise Exception('Failed to run apcaccess command')

    lines = string.split(dump[1], "\n")

    info = {}
    for line in lines:
        m = re.search('(\w+)\s*:\s*(\d+)', line)
        if m:
            info[m.group(1)] = int(m.group(2))

    return {
        'battery_percent': info['BCHARGE'],
        'battery_minutes': info['TIMELEFT'],
        'line_voltage': info['LINEV'],
        'ups_load_percent': info['LOADPCT'],
    }


class Traffic:

    """Calculates traffic for given device in bytes per second. Call update()
    regularly, read tx and rx"""
    last_time = 0
    last_tx_bytes = 0
    last_rx_bytes = 0

    # scales, automatically set to max-ever-recorded
    tx_max = 0
    rx_max = 0

    def __init__(self, dev='eth0'):
        self.tx_file = "/sys/class/net/%s/statistics/tx_bytes" % dev
        self.rx_file = "/sys/class/net/%s/statistics/rx_bytes" % dev

        if not path.exists(self.tx_file):
            raise IOError("Could not find stats files for %s." % dev)

        # read these for tx/rx in Mbps
        self.tx = 0
        self.rx = 0

        self.last_time = time.time()
        self.update()

    def update(self):
        "Call regularly to get rx and tx in bytes per second"
        current_time = time.time()

        current_tx_bytes = self._get_bytes('tx')
        current_rx_bytes = self._get_bytes('rx')

        delta_time = current_time - self.last_time
        delta_tx_bytes = current_tx_bytes - self.last_tx_bytes
        delta_rx_bytes = current_rx_bytes - self.last_rx_bytes

        self.last_time = current_time
        self.last_tx_bytes = current_tx_bytes
        self.last_rx_bytes = current_rx_bytes

        self.tx = delta_tx_bytes / delta_time
        self.rx = delta_rx_bytes / delta_time

        self.tx = int(self.tx)
        self.rx = int(self.rx)

        self.tx_max = max(self.tx, self.tx_max)
        self.rx_max = max(self.rx, self.rx_max)

    def _get_bytes(self, direction):
        "get bytes for direction: tx/rx"

        if direction == 'tx':
            f = open(self.tx_file, 'r')
        elif direction == 'rx':
            f = open(self.rx_file, 'r')
        else:
            raise ValueError('Invalid direction. Choose rx/tx')

        bytes = f.readline()
        bytes = int(bytes)

        f.close()

        return bytes


def gpu_temperature():
    process = Popen(['nvidia-smi', '-q', '-d', 'TEMPERATURE'],
                    stdout=PIPE, stderr=PIPE, stdin=PIPE)
    out, _ = process.communicate()

    state = dict()
    for line in out.splitlines():
        try:
            key, val = line.split(":")
        except ValueError:
            continue
        key, val = key.strip(), val.strip()
        state[key] = val

    return int(state['GPU Current Temp'][:-2])


def aggregate():
    state = {}

    # host dependent
    try:
        state["gpu_temperature_c"] = gpu_temperature()
    except:
        pass

    try:
        state = state.update(ups())
    except:
        pass

    mem = memory()
    stor = storage()

    state["mem_used_bytes"] = mem["used"]
    state["mem_total_bytes"] = mem["total"]
    state["mem_used_percent"] = mem["percent"]
    state["disk_used_bytes"] = stor["used"]
    state["disk_total_bytes"] = stor["total"]
    state["disk_used_percent"] = stor["percent"]
    state["uptime_secs"] = uptime()
    state["cpu_load_percent"] = cpu_load()

    return state


