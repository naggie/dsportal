from dsportal.base import healthcheck
from dsportal.util import get_ups_data,percent_bar
import os
import multiprocessing

@healthcheck
def ram_usage():
    "Checks RAM usage is less than 90%. Does not count cache and buffers."
    # http://www.linuxatemyram.com/
    with open('/proc/meminfo') as f:
        lines = f.readlines()

    # in kB
    info = {}

    for line in lines:
        m = re.search('(\w+):\s*(\d+)', line)
        if m:
            info[m.group(1)] = int(m.group(2))

    used = info['MemTotal'] - info['MemFree'] - info['Buffers'] - info['Cached']

    self.raw_total = info['MemTotal'] * 1024

    # used by applications, not cache/buffers
    self.raw_value = used * 1024


@healthcheck
def cpu_usage(_max=200):
    "Checks CPU load is nominal."
    #"return normalised % load (avg num of processes waiting per processor)"
    load = os.getloadavg()[0]
    load = load / multiprocessing.cpu_count()
    value = int(load*100)
    return {
            "value": value,
            "percentage": percent_bar(value,100),
            "healthy": value < _max,
            }

@healthcheck
def disk_usage():
    "Inspects used and available blocks on given mount points."
    s = statvfs(self.mountpoint)
    free = s.f_bsize * s.f_bavail
    total = s.f_bsize * s.f_blocks

@healthcheck
def mains_voltage(_min=216,_max=253):
    "Checks mains voltage falls within UK legal limits of 230V +10% -6%"

@healthcheck
def ups_load():
    "Checks UPS is not overloaded"

@healthcheck
def battery_level():
    "Checks estimated time remaining and percentage"

    info = util.get_ups_data()
    return {
        'battery_percent': info['BCHARGE'],
        'battery_minutes': info['TIMELEFT'],
        'line_voltage': info['LINEV'],
        'ups_load_percent': info['LOADPCT'],
    }


@healthcheck
def uptime():
    "Specify uptime in days"

    with open('/proc/uptime', 'r') as f:
        line = f.readline()

    seconds = line.partition(' ')[0]
    seconds = float(seconds)

    self.value = int(seconds)

    self._patch({'value':self.value})


@healthcheck
def cpu_temperature():
    "Checks CPU Temperature is nominal"

@healthcheck
def gpu_temperature():
    "Checks GPU Temperature is nominal"

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

    int(state['GPU Current Temp'][:-2])

    try:
        int(state['GPU Shutdown Temp'][:-2])
        int(state['GPU Slowdown Temp'][:-2])
    except ValueError:
        # not specified, so dot change the defaults
        pass



@healthcheck
def btrfs_pool():
    "Checks BTRFS health"

@healthcheck
def http_status(url):
    "Checks service returns 200 OK"

@healthcheck
def broken_links(url,ignore):
    "Crawls website for broken links"

@healthcheck
def certificate_expiry():
    "Checks certificate isn't near expiry"
    # https://stackoverflow.com/questions/7689941/how-can-i-retrieve-the-tls-ssl-peer-certificate-of-a-remote-host-using-python

@healthcheck
def s3_backup_checker():
    "Checks to see that a backup was made in the last 25 hours"

@healthcheck
def papouch_th2e_temperature(
        url,
        min_temp=10,
        max_temp=35,
        min_hum=20,
        max_hum=80):
    """Check the temperature reported by a Papouch TH2E"""

