from dsportal.base import HealthCheck
from dsportal.util import get_ups_data
from dsportal.util import bar_percentage
import socket
import re
import os
import multiprocessing
import requests
from subprocess import run,PIPE

# TODO implement or change representation of magnitude
def human_bytes(x):return x

class RamUsage(HealthCheck):
    label = "RAM Usage"
    description = "Checks RAM usage is less than 90%. Does not count cache and buffers."

    @staticmethod
    def check():
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

        total = info['MemTotal'] * 1024

        # used by applications, not cache/buffers
        value = used * 1024

        return {
                "value": value,
                "bar_min": "0MB",
                "bar_max": human_bytes(total), # TODO standardise way of representing magnitude
                "bar_percentage": bar_percentage(value,total),
                "healthy": value < 0.9*total,
                }

class CpuUsage(HealthCheck):
    label = "CPU Utilisation"
    description = "Checks CPU load is nominal."

    @staticmethod
    def check(_max=200):
        #"return normalised % load (avg num of processes waiting per processor)"
        load = os.getloadavg()[0]
        load = load / multiprocessing.cpu_count()
        value = int(load*100)
        return {
                "value": value,
                "bar_min":"0%",
                "bar_max":"100%",
                "bar_percentage": bar_percentage(value,100),
                "healthy": value < _max,
                }


class DiskUsage(HealthCheck):
    label = "Disk Usage"
    description = "Inspects used and available blocks on given mount points."
    def __init__(self,*args,**kwargs):
        super(DiskUsage,self).__init__(*args,**kwargs)
        self.label = '%s usage' % kwargs.get('mountpoint','/')

    @staticmethod
    def check(mountpoint='/'):
        s = os.statvfs(mountpoint)
        free = s.f_bsize * s.f_bavail
        total = s.f_bsize * s.f_blocks
        usage = total - free

        return {
                "value": usage,
                "bar_min": "0MB",
                "bar_max": human_bytes(total), # TODO standardise way of representing magnitude
                "bar_percentage": bar_percentage(usage,total),
                "healthy": usage < 0.8*total,
                }


class UpsVoltage(HealthCheck):
    label = "Mains Voltage"
    description = "Checks mains voltage falls within UK statutory limits of 230V +10% -6%"
    @staticmethod
    def check(_min=216,_max=253):
        info = get_ups_data()
        return {
            "bar_min":'%sV' % _min,
            "bar_max":'%sV' % _max,
            'bar_percentage': bar_percentage(info['LINEV'],_max,_min),
            'value': '%sV' % info['LINEV'],
            "healthy": (info['LINEV'] < _max) and (info['LINEV'] > _min),
        }

class UpsLoad(HealthCheck):
    label = "UPS Load"
    description = "Checks UPS is not overloaded"
    @staticmethod
    def check():
        info = get_ups_data()
        return {
            "bar_min":"0%",
            "bar_max":"100%",
            'bar_percentage': info['LOADPCT'],
            'value': '%s%%' % info['LOADPCT'],
            "healthy": info['LOADPCT'] < 90,
        }

class UpsBattery(HealthCheck):
    label = "UPS battery"
    description = "Checks estimated time remaining and percentage"
    @staticmethod
    def check():
        info = get_ups_data()
        return {
            "bar_min":"0%",
            "bar_max":"100%",
            'bar_percentage': info['BCHARGE'],
            'value': info['TIMELEFT'], # ???
            "healthy": info['TIMELEFT'] < 300,
        }


class Uptime(HealthCheck):
    label = "Uptime"
    description = "Specify uptime in days"

    @staticmethod
    def check():
        with open('/proc/uptime', 'r') as f:
            line = f.readline()

        seconds = line.partition(' ')[0]
        seconds = float(seconds)

        days = int(round(seconds/86400))

        return {
            "healthy": True,
            "value": '%s days' % days,
            }


class CpuTemperature(HealthCheck):
    label = "CPU Temperature"
    description = "Checks CPU Temperature is nominal"

    @staticmethod
    def check(zone=1,slowdown=80,_max=90):
        with open('/sys/class/thermal/thermal_zone%s/temp' % zone) as f:
            value = int(f.read().strip()[:-3])

        return {
                "value": "%s&deg;C" % value,
                "bar_min": "15&deg;C",
                "bar_max": "%s&deg;C" % _max,
                "bar_percentage": bar_percentage(value,_max,15),
                "healthy": value < slowdown,
                }

class GpuTemperature(HealthCheck):
    label = "GPU Temperature"
    description = "Checks GPU Temperature is nominal"

    @staticmethod
    def check(slowdown=88,_max=93):
        dump = run(['nvidia-smi', '-q', '-d', 'TEMPERATURE'],timeout=10,check=True,stdout=PIPE).stdout

        state = dict()
        for line in dump.decode().splitlines():
            try:
                key, val = line.split(":")
            except ValueError:
                continue
            key, val = key.strip(), val.strip()
            state[key] = val

        value = int(state['GPU Current Temp'][:-2])

        try:
            slowdown = int(state['GPU Slowdown Temp'][:-2])
            _max = int(state['GPU Shutdown Temp'][:-2])
        except ValueError:
            # not specified, so dot change the defaults
            pass

        return {
                "value": "%s&deg;C" % value,
                "bar_min": "15&deg;C",
                "bar_max": "%s&deg;C" % _max,
                "bar_percentage": bar_percentage(value,_max,15),
                "healthy": value < slowdown,
                }


class BtrfsPool(HealthCheck):
    label = "BTRFS Pool"
    description = "Checks BTRFS health"

class HttpStatus(HealthCheck):
    label = "HTTP check"
    description = "Checks service returns 200 OK"
    @staticmethod
    def check(url,status_code=200,timeout=10):
        r = requests.get(url,timeout=timeout)
        if r.status_code != status_code:
            r.raise_for_status()
            raise Exception('Unexpected HTTP 200 received')

        return {
                "healthy": True,
                }

class BrokenLinks(HealthCheck):
    label = "Hyperlinks"
    description = "Crawls website for broken links"
    interval = 5*60*60
    @staticmethod
    def check(url,ignore):
        # https://wummel.github.io/linkchecker/ but use git to install latest revision
        # example linkchecker --check-html --check-css --ignore-url 'xmlrpc.php' --user-agent 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.  110 Safari/537.36' https://cydarmedical.com
        pass

# run time -- 5 mins or so for small website
# run every 5 hours

class CertificateExpiry(HealthCheck):
    "Checks certificate isn't near expiry"
    # https://stackoverflow.com/questions/7689941/how-can-i-retrieve-the-tls-ssl-peer-certificate-of-a-remote-host-using-python

class s3_backup_checker(HealthCheck):
    label = "S3 daily backup"
    description = "Checks to see that a backup was made in the last 25 hours"
    @staticmethod
    def check(bucket,hours=25):
        # list keys in bucket and check the latest upload was < 25 hours ago.
        pass

class PapouchTh2eTemperature(HealthCheck):
    label = "Server room Temperature"
    description = "Checks the temperature reported by a Papouch TH2E"

    @staticmethod
    def check(
        url,
        min_temp=10,
        max_temp=35,
        min_hum=20,
        max_hum=80):
        pass



class SsllabsReport(HealthCheck):
    label = "SSL implementation"
    description = "Checks SSL implementation using ssllabs.org"
    @staticmethod
    def check(host,min_grade='A+'):
        grades = ['A+','A','A-','B','C','D','E','F','T','M']
        grades = dict(zip(grades,range(len(grades)))) # grade -> score

        for x in range(100):
            response = requests.get('https://api.ssllabs.com/api/v2/analyze',params={
                "host": host,
                },timeout=5)
            response.raise_for_status()
            report = response.json()
            sleep(2)

            if report['status'] == 'READY':
                break

            if report['status'] == 'ERROR':
                raise Exception(report['statusMessage'])
        else:
            raise TimeoutError('SSL labs test took too long')

        grade = report['endpoints'][0]['grade']

        if grades[grade] >= grades[min_grade]:
            raise Exception('Grade %s not acheived, got %s.' % (min_grade,grade))

        return {
            'healthy': True,
                }


class PortScan(HealthCheck):
    label = "Firewall"
    description = "Scans host to check ports are closed. Synchronous so relatively quiet/slow."
    @staticmethod
    def check(host,open_ports=[22,80,443],limit=65535,wait=0.5):
        for port in range(1,limit+1):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.settimeout(0.5)
                result = sock.connect_ex((host, port))
                if result == 0 and port not in open_ports:
                    raise Exception('At least port %s is open but should not be' % port)
            except:
                raise
            finally:
                sock.close()
