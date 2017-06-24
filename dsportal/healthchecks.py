from dsportal.base import HealthCheck
from dsportal.util import get_ups_data
from dsportal.util import bar_percent
from dsportal.util import human_bytes
from dsportal import __version__ as version
import socket
import re
import os
import multiprocessing
import requests
from subprocess import run,PIPE
from urllib.parse import urlparse
from time import sleep,mktime,time
import boto3
import xml.etree.ElementTree as ET

class RamUsage(HealthCheck):
    label = "RAM Usage"
    description = "Checks RAM usage is less than 90%. Does not count cache and buffers."
    nominal_failure = "RAM insufficient"

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
                "value": human_bytes(value),
                "bytes": value,
                "bar_min": "0 GB",
                "bar_max": human_bytes(total),
                "bar_percent": bar_percent(value,total),
                "healthy": value < 0.9*total,
                }

class CpuUsage(HealthCheck):
    label = "CPU Utilisation"
    description = "Checks CPU load is nominal."
    nominal_failure = "CPU overloaded"

    @staticmethod
    def check(_max=200):
        #"return normalised % load (avg num of processes waiting per processor)"
        load = os.getloadavg()[0]
        load = load / multiprocessing.cpu_count()
        value = int(load*100)
        return {
                "value": '%s%%' % value,
                "bar_min":"0%",
                "bar_max":"100%",
                "bar_percent": bar_percent(value,100),
                "healthy": value < _max,
                }


class DiskUsage(HealthCheck):
    label = "Disk Usage"
    description = "Inspects used and available blocks on given mount points."
    nominal_failure = "Disk usage too high"

    def __init__(self,**kwargs):
        super(DiskUsage,self).__init__(**kwargs)
        self.label = '%s usage' % kwargs.get('mountpoint','/')

    @staticmethod
    def check(mountpoint='/'):
        s = os.statvfs(mountpoint)
        free = s.f_bsize * s.f_bavail
        total = s.f_bsize * s.f_blocks
        usage = total - free

        return {
                "value": human_bytes(usage),
                "bytes": usage,
                "bar_min": "0 GB",
                "bar_max": human_bytes(total),
                "bar_percent": bar_percent(usage,total),
                "healthy": usage < 0.9*total,
                }


class UpsVoltage(HealthCheck):
    label = "Mains Voltage"
    description = "Checks mains voltage falls within UK statutory limits of 230V +10% -6%"
    nominal_failure = "Voltage outside legal limit"
    @staticmethod
    def check(_min=216,_max=253):
        info = get_ups_data()
        return {
            "bar_min":'%sV' % _min,
            "bar_max":'%sV' % _max,
            'bar_percent': bar_percent(info['LINEV'],_max,_min),
            'value': '%sV' % info['LINEV'],
            "healthy": (info['LINEV'] < _max) and (info['LINEV'] > _min),
        }

class UpsLoad(HealthCheck):
    label = "UPS Load"
    description = "Checks UPS is not overloaded"
    nominal_failure = "UPS overloaded"
    @staticmethod
    def check():
        info = get_ups_data()
        return {
            "bar_min":"0%",
            "bar_max":"100%",
            'bar_percent': info['LOADPCT'],
            'value': '%s%%' % info['LOADPCT'],
            "healthy": info['LOADPCT'] < 90,
        }

class UpsBattery(HealthCheck):
    label = "UPS battery"
    description = "Checks estimated time remaining and percentage"
    nominal_failure = "UPS battery almost fully discharged"
    @staticmethod
    def check():
        info = get_ups_data()
        return {
            "bar_min":"0%",
            "bar_max":"100%",
            'bar_percent': info['BCHARGE'],
            'value': "%sm" % info['TIMELEFT'],
            "healthy": info['TIMELEFT'] > 10,
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
    nominal_failure = "CPU has overheated"

    @staticmethod
    def check(zone=None,slowdown=80,_max=90):
        # search for hottest or use given zone
        hottest = 0
        for x in [zone] if zone else range(3):
            try:
                with open('/sys/class/thermal/thermal_zone%s/temp' % x) as f:
                    reading = f.read()
                    value = int(reading.strip()[:-3])
                    if value > hottest:
                        hottest = value
            except OSError:
                continue

        if not hottest:
            raise Exception('Could not find any thermal zone')

        return {
                "value": "%s&deg;C" % hottest,
                "bar_min": "15&deg;C",
                "bar_max": "%s&deg;C" % _max,
                "bar_percent": bar_percent(hottest,_max,15),
                "healthy": hottest < slowdown,
                }

class GpuTemperature(HealthCheck):
    label = "GPU Temperature"
    description = "Checks GPU Temperature is nominal"
    nominal_failure = "GPU has overheated"

    @staticmethod
    def check(slowdown=88,_max=93):
        result = run(['nvidia-smi', '-q', '-d', 'TEMPERATURE'],timeout=10,check=True,stdout=PIPE)

        state = dict()
        for line in result.stdout.decode().splitlines():
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
                "bar_percent": bar_percent(value,_max,15),
                "healthy": value < slowdown,
                }


class BtrfsPool(HealthCheck):
    label = "BTRFS Pool"
    description = "Checks BTRFS health"
    nominal_failure = "Pool in degraded state"

class HttpStatus(HealthCheck):
    label = "Page load"
    description = "Checks service returns 200 OK"

    def __init__(self,**kwargs):
        super(HttpStatus,self).__init__(**kwargs)
        self.check_kwargs['url'] = kwargs.get('url',self.entity.url)

    @staticmethod
    def check(url,status_code=200,timeout=10,contains=None):
        r = requests.get(
                url,
                timeout=timeout,
                headers={
                    "User-Agent":'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
                    }
                )
        if r.status_code != status_code:
            r.raise_for_status()
            raise Exception('Unexpected HTTP 200 received')

        if contains and contains not in r.text:
            raise Exception('Unexpected page content despite correct HTTP status')

        return {
                "healthy": True,
                "value": r.status_code,
                }

class BrokenLinks(HealthCheck):
    label = "Page links"
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

class S3BackupChecker(HealthCheck):
    label = "Recent backup"
    description = "Checks to see that a backup was made recently"
    nominal_failure = "No recent backup found"
    interval = 3600

    @staticmethod
    def check(
            bucket,
            hours=25,
            **client_kwargs
            ):
        # list keys in bucket and check the latest upload was < 25 hours ago.
        client = boto3.client(
                service_name='s3',
                **client_kwargs
                )

        paginator = client.get_paginator('list_objects_v2')

        latest = 0
        for page in paginator.paginate(Bucket=bucket):
            for obj in page['Contents']:
                timestamp = mktime(obj['LastModified'].timetuple())
                if timestamp > latest:
                    latest = timestamp

        return {
            "healthy" : time() - latest < hours*3600,
                }



class PapouchTh2eTemperature(HealthCheck):
    label = "Temperature"
    description = "Checks the temperature reported by a Papouch TH2E"
    nominal_failure = "Temperature outside acceptable range"

    @staticmethod
    def check(url,_min=10,_max=35):
        r = requests.get('http://192.168.168.200/fresh.xml',timeout=5)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        value = root[0].attrib['val']
        value = int(float(value))

        return {
                "value": "%s&deg;C" % value,
                "bar_min": "%s&deg;C" % _min,
                "bar_max": "%s&deg;C" % _max,
                "bar_percent": bar_percent(value,_max,_min),
                "healthy": value < _max and value > _min,
                }



class SsllabsReport(HealthCheck):
    label = "SSL implementation"
    description = "Checks SSL implementation using ssllabs.org"
    nominal_failure = "Grade achieved is below threshold"
    interval = 24*3600

    def __init__(self,**kwargs):
        super(SsllabsReport,self).__init__(**kwargs)
        url = kwargs.get('url',self.entity.url)
        if 'host' not in kwargs:
            self.check_kwargs['host'] = urlparse(url).hostname

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

        return {
            'healthy': grades[grade] <= grades[min_grade],
            'value': grade,
                }


class PortScan(HealthCheck):
    label = "Firewall"
    description = "Scans host to check ports are closed. Synchronous so relatively quiet/slow."
    interval = 24*3600
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


class Systemd(HealthCheck):
    label = "Systemd"
    description = "Checks all systemd services are OK"
    nominal_failure = "Service failure(s)"

    @staticmethod
    def check():
        result = run(['systemctl','is-system-running'],timeout=10,stdout=PIPE)

        value = result.stdout.decode().strip()

        return {
                "value": value.capitalize(),
                "healthy": result.returncode == 0,
                }


class WorkerVersion(HealthCheck):
    label = "Worker version"
    description = "Checks dsportal worker version matches server version"
    nominal_failure = "Worker version does not match server version"
    interval = 3600

    def __init__(self,**kwargs):
        super(WorkerVersion,self).__init__(**kwargs)
        self.check_kwargs['server_version'] = self.server_version

    @staticmethod
    def check(server_version):
        return {
                "healthy": version == server_version,
                }
