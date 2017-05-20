from base import HealthCheck,MetricCheck,DummyCheck
from util import get_ups_data

class RAMUsageCheck(MetricCheck):
    description = "Checks RAM usage is less than 90%. Does not count cache and buffers."
    raw_min = 0
    units = 'bytes'

    def run(self):
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

        # TODO set human values


class CPUUsageCheck(MetricCheck):
    description = "Checks CPU load is nominal."

    def run(self):
        "return normalised % load (avg num of processes waiting per processor)"

        load = os.getloadavg()[0]
        load = load / multiprocessing.cpu_count()
        return int(load * 100)



class DiskUsageCheck(MetricCheck):
    description = "Inspects used and available blocks on given mount points."
    def run(self):
        s = statvfs(self.mountpoint)
        free = s.f_bsize * s.f_bavail
        total = s.f_bsize * s.f_blocks

class UKMainsVoltageCheck(MetricCheck):
    description = "Checks mains voltage falls within UK legal limits of 230V +10% -6%"

class UPSLoadCheck(MetricCheck):
    description = "Checks UPS is not overloaded"

class BatteryLevelCheck(MetricCheck):
    description = "Checks estimated time remaining and percentage"

    def run(self):
        info = util.get_ups_data()
        return {
            'battery_percent': info['BCHARGE'],
            'battery_minutes': info['TIMELEFT'],
            'line_voltage': info['LINEV'],
            'ups_load_percent': info['LOADPCT'],
        }


class UptimeCheck(DummyCheck):
    description = "Specify uptime in days"

    units = 'seconds'

    def run(self):
        with open('/proc/uptime', 'r') as f:
            line = f.readline()

        seconds = line.partition(' ')[0]
        seconds = float(seconds)

        self.value = int(seconds)

        self._patch({'value':self.value})


class CPUTemperatureCheck(MetricCheck):
    description = "Checks CPU Temperature is nominal"

class GPUTemperatureCheck(MetricCheck):
    interval = 60
    description = "Checks GPU Temperature is nominal"

    def run(self):
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


class BTRFSPoolCheck(MetricCheck):
    description = "Checks BTRFS health"

class HTTPStatusCheck(HealthCheck):
    description = "Checks service returns 200 OK"

class CertificateExpiryCheck(HealthCheck):
    description = "Checks certificate isn't near expiry"
    # https://stackoverflow.com/questions/7689941/how-can-i-retrieve-the-tls-ssl-peer-certificate-of-a-remote-host-using-python

class S3BackupChecker(HealthCheck):
    description = "Checks to see that a backup was made in the last 25 hours"
