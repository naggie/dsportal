from base import healthcheck
from util import get_ups_data

@healthcheck
def ramusagecheck():
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
def cpuusagecheck():
    "Checks CPU load is nominal."
    #"return normalised % load (avg num of processes waiting per processor)"
    load = os.getloadavg()[0]
    load = load / multiprocessing.cpu_count()
    return int(load * 100)



@healthcheck
def diskusagecheck():
    "Inspects used and available blocks on given mount points."
    s = statvfs(self.mountpoint)
    free = s.f_bsize * s.f_bavail
    total = s.f_bsize * s.f_blocks

@healthcheck
def ukmainsvoltagecheck():
    "Checks mains voltage falls within UK legal limits of 230V +10% -6%"

@healthcheck
def upsloadcheck():
    "Checks UPS is not overloaded"

@healthcheck
def batterylevelcheck():
    "Checks estimated time remaining and percentage"

    info = util.get_ups_data()
    return {
        'battery_percent': info['BCHARGE'],
        'battery_minutes': info['TIMELEFT'],
        'line_voltage': info['LINEV'],
        'ups_load_percent': info['LOADPCT'],
    }


@healthcheck
def uptimecheck():
    "Specify uptime in days"

    with open('/proc/uptime', 'r') as f:
        line = f.readline()

    seconds = line.partition(' ')[0]
    seconds = float(seconds)

    self.value = int(seconds)

    self._patch({'value':self.value})


@healthcheck
def cputemperaturecheck():
    "Checks CPU Temperature is nominal"

@healthcheck
def gputemperaturecheck():
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

gputemperaturecheck.interval = 60


@healthcheck
def btrfspoolcheck():
    "Checks BTRFS health"

@healthcheck
def httpstatuscheck():
    "Checks service returns 200 OK"

@healthcheck
def certificateexpirycheck():
    "Checks certificate isn't near expiry"
    # https://stackoverflow.com/questions/7689941/how-can-i-retrieve-the-tls-ssl-peer-certificate-of-a-remote-host-using-python

@healthcheck
def s3backupchecker():
    "Checks to see that a backup was made in the last 25 hours"

@healthcheck
def papouchth2e_temperature(url,
        min_temp=10,
        max_temp=35,
        min_hum=20,
        max_hum=80):
    """Check the temperature reported by a Papouch TH2E"""

