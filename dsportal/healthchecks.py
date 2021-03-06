from dsportal.base import HealthCheck
from dsportal.util import get_ups_data
from dsportal.util import bar_percent
from dsportal.util import human_bytes
from dsportal.util import human_seconds
from dsportal.util import machine_seconds
from dsportal import __version__ as version
from whois import whois
import socket
from datetime import datetime
import re
import os
import multiprocessing
import requests
from subprocess import run, PIPE
from urllib.parse import urlparse
from time import sleep, mktime, time
import boto3
import xml.etree.ElementTree as ET
import urllib
import ssl


class RamUsage(HealthCheck):
    """Checks RAM usage is less than 90%. Does not count cache and buffers.
    """

    label = "RAM Usage"
    description = "Checks RAM usage is less than 90%. Does not count cache and buffers."

    @staticmethod
    def check():
        # http://www.linuxatemyram.com/
        with open("/proc/meminfo") as f:
            lines = f.readlines()

        # in kB
        info = {}

        for line in lines:
            m = re.search("(\w+):\s*(\d+)", line)
            if m:
                info[m.group(1)] = int(m.group(2))

        used = info["MemTotal"] - info["MemFree"] - info["Buffers"] - info["Cached"]

        total = info["MemTotal"] * 1024

        # used by applications, not cache/buffers
        value = used * 1024

        status = {
            "value": human_bytes(value),
            "bytes": value,
            "bar_min": "0 GB",
            "bar_max": human_bytes(total),
            "bar_percent": bar_percent(value, total),
        }

        if value < 0.9 * total:
            status["healthy"] = True
            status["reason"] = "RAM usage nominal"
        else:
            status["healthy"] = False
            status["reason"] = "RAM usage too high"

        return status


class CpuUsage(HealthCheck):
    """Checks number of waiting processes per thread is less than 3
    """

    label = "CPU Utilisation"
    description = "Checks CPU load is nominal."

    @staticmethod
    def check(_max=300):
        # "return normalised % load (avg num of processes waiting per processor)"
        load = os.getloadavg()[0]
        load = load / multiprocessing.cpu_count()
        value = int(load * 100)

        status = {
            "value": "%s%%" % value,
            "bar_min": "0%",
            "bar_max": "100%",
            "bar_percent": bar_percent(value, 100),
            "healthy": value < _max,
        }

        if value < _max:
            status["healthy"] = True
            status["reason"] = "CPU usage nominal"
        else:
            status["healthy"] = False
            status["reason"] = "CPU overloaded"

        return status


class DiskUsage(HealthCheck):
    """Inspects used and available blocks on given mount points.

    Args:
        mountpoint (str): mounted directory to test
    """

    label = "Disk Usage"
    description = "Inspects used and available blocks on given mount points."

    def __init__(self, **kwargs):
        super(DiskUsage, self).__init__(**kwargs)
        self.label = "%s usage" % kwargs.get("mountpoint", "/")

    @staticmethod
    def check(mountpoint="/"):
        s = os.statvfs(mountpoint)
        free = s.f_bsize * s.f_bavail
        total = s.f_bsize * s.f_blocks
        usage = total - free
        percent = bar_percent(usage, total)

        status = {
            "value": human_bytes(usage),
            "bytes": usage,
            "bar_min": "0 GB",
            "bar_max": human_bytes(total),
            "bar_percent": percent,
        }

        if usage < 0.9 * total:
            status["healthy"] = True
            status["reason"] = "Disk usage nominal"
        else:
            status["healthy"] = False
            status["reason"] = "Disk is nearly full"

        return status


class UpsVoltage(HealthCheck):
    """Checks mains voltage falls within UK statutory limits of 230V +10% -6%
        Args:
            _min (int): Voltage must not fall below this level
            _max (int): Voltage must not rise above this level
    """

    label = "Mains Voltage"

    @staticmethod
    def check(_min=216, _max=253):
        info = get_ups_data()
        return {
            "bar_min": "%sV" % _min,
            "bar_max": "%sV" % _max,
            "bar_percent": bar_percent(info["LINEV"], _max, _min),
            "value": "%sV" % info["LINEV"],
            "healthy": (info["LINEV"] < _max) and (info["LINEV"] > _min),
        }


class UpsLoad(HealthCheck):
    """Checks UPS is not overloaded.
    Requires apcupsd and configuration to output status to /var/log/apcupsd.status.
    """

    label = "UPS Load"

    @staticmethod
    def check():
        info = get_ups_data()
        return {
            "bar_min": "0%",
            "bar_max": "100%",
            "bar_percent": info["LOADPCT"],
            "value": "%s%%" % info["LOADPCT"],
            "healthy": info["LOADPCT"] < 90,
        }


class UpsBattery(HealthCheck):
    """Checks estimated time remaining and percentage
    Requires apcupsd and configuration to output status to /var/log/apcupsd.status.
    """

    label = "UPS battery"

    @staticmethod
    def check():
        info = get_ups_data()
        return {
            "bar_min": "0%",
            "bar_max": "100%",
            "bar_percent": info["BCHARGE"],
            "value": "%sm" % info["TIMELEFT"],
            "healthy": info["TIMELEFT"] > 10,
        }


class Uptime(HealthCheck):
    """Specifies uptime in days. No check."""

    label = "Uptime"

    @staticmethod
    def check():
        with open("/proc/uptime", "r") as f:
            line = f.readline()

        seconds = line.partition(" ")[0]
        seconds = float(seconds)

        days = int(round(seconds / 86400))

        return {"healthy": True, "value": "%s days" % days}


class CpuTemperature(HealthCheck):
    """Checks CPU Temperature is nominal. Uses ACPI.

        Args:
            zone (int): Zone number to check. If not given, will pick hottest of first 4 zones.
            slowdown (int): Temperature in Celcius at which to fail check (implies thermal throttling)
            _max (int): Max die temperature in Celcius
    """

    label = "CPU Temperature"

    @staticmethod
    def check(zone=None, slowdown=80, _max=90):
        # search for hottest or use given zone
        hottest = 0
        for x in [zone] if zone else range(3):
            try:
                with open("/sys/class/thermal/thermal_zone%s/temp" % x) as f:
                    reading = f.read()
                    value = int(reading.strip()[:-3])
                    if value > hottest:
                        hottest = value
            except OSError:
                continue

        if not hottest:
            raise Exception("Could not find any thermal zone")

        status = {
            "value": "%s&deg;C" % hottest,
            "bar_min": "15&deg;C",
            "bar_max": "%s&deg;C" % _max,
            "bar_percent": bar_percent(hottest, _max, 15),
        }

        if hottest < slowdown:
            status["healthy"] = True
            status["reason"] = "CPU temperature nominal"
        else:
            status["healthy"] = False
            status["reason"] = "CPU overheated"

        return status


class GpuTemperature(HealthCheck):
    """Checks GPU Temperature is nominal

        Args:
            slowdown (int): Temperature in Celcius at which to fail check (implies thermal throttling)
            _max (int): Max die temperature in Celcius

        Requires `nvidia-smi`. If slowdown and shutdown temperature is provided
        by nvidia-smi it will be used instead.
    """

    label = "GPU Temperature"

    @staticmethod
    def check(slowdown=88, _max=93):
        result = run(
            ["nvidia-smi", "-q", "-d", "TEMPERATURE"],
            timeout=10,
            check=True,
            stdout=PIPE,
        )

        state = dict()
        for line in result.stdout.decode().splitlines():
            try:
                key, val = line.split(":")
            except ValueError:
                continue
            key, val = key.strip(), val.strip()
            state[key] = val

        value = int(state["GPU Current Temp"][:-2])

        try:
            slowdown = int(state["GPU Slowdown Temp"][:-2])
            _max = int(state["GPU Shutdown Temp"][:-2])
        except ValueError:
            # not specified, so dot change the defaults
            pass

        status = {
            "value": "%s&deg;C" % value,
            "bar_min": "15&deg;C",
            "bar_max": "%s&deg;C" % _max,
            "bar_percent": bar_percent(value, _max, 15),
        }

        if value < slowdown:
            status["healthy"] = True
            status["reason"] = "GPU temperature nominal"
        else:
            status["healthy"] = False
            status["reason"] = "GPU overheated"

        return status


class BtrfsPool(HealthCheck):
    """Checks BTRFS health"""

    label = "BTRFS Pool"


class HttpStatus(HealthCheck):
    """Checks service returns 200 OK or other.

    Args:
        url (str): URL to attempt to load.
        status_code (int): Default 200. HTTP status code to expect.
        timeout (int): Number of seconds to wait for a response
        contains (str): String that must be found in response.
        doublecheck (bool): Retry once given a TCP/IP/DNS problem. Useful to filter
        some local network issues
    """

    label = "Page load"

    def __init__(self, **kwargs):
        super(HttpStatus, self).__init__(**kwargs)
        # inherit URL from entity by default
        self.check_kwargs["url"] = kwargs.get("url", self.entity.url)

    @staticmethod
    def check(
        url,
        status_code=200,
        timeout=10,
        contains=None,
        client_crt=None,
        client_key=None,
    ):
        # N.B. doublecheck mechanism will try one more time upon connection
        # problem as a mitigation against transient local network issues that
        # cause a false-positive. Intermittent "ReadTimeout" errors
        # experienced on t2.micro in AWS.
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"

        kwargs = {"url": url, "timeout": timeout, "headers": {"User-Agent": ua}}

        if client_crt:
            kwargs["cert"] = (client_crt, client_key)

        try:
            r = requests.get(**kwargs)
        except:
            sleep(1)
            try:
                r = requests.get(**kwargs)
            except requests.exceptions.ProxyError:
                # indicates a local problem and therefore the test is invalid
                # and health is unknown.
                raise
            except requests.exceptions.SSLError as e:
                return {"healthy": False, "reason": "Failed to verify SSL connection"}
            except requests.exceptions.ReadTimeout as e:
                return {"healthy": False, "reason": "Read timed out"}
            except requests.exceptions.ConnectTimeout as e:
                return {"healthy": False, "reason": "Connection timed out"}
            except requests.exceptions.TooManyRedirects as e:
                return {"healthy": False, "reason": "Redirect loop detected"}
            # actually a parent of many above
            except requests.exceptions.ConnectionError as e:
                return {"healthy": False, "reason": "Connection failed"}

        if r.status_code != status_code:
            if r.status_code == 200:
                return {
                    "healthy": False,
                    "value": 200,
                    "reason": "Unexpected 200 OK received",
                }
            else:
                return {"healthy": False, "value": r.status_code, "reason": r.reason}

        if contains and contains not in r.text:
            return {
                "healthy": False,
                "value": r.status_code,
                "reason": "Unexpected page content despite correct HTTP status",
            }

        return {"healthy": True, "value": r.status_code}


class BrokenLinks(HealthCheck):
    """Crawls website for broken links"""

    label = "Page links"
    interval = 5 * 60 * 60

    @staticmethod
    def check(url, ignore):
        # https://wummel.github.io/linkchecker/ but use git to install latest revision
        # example linkchecker --check-html --check-css --ignore-url 'xmlrpc.php' --user-agent 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.  110 Safari/537.36' https://cydarmedical.com
        pass


# run time -- 5 mins or so for small website
# run every 5 hours


class S3BackupChecker(HealthCheck):
    """Checks to see that a backup was made recently

        Args:
            bucket (str): Name of s3 bucket to check
            age (str): Time in short notation before a backup is considered too old.
            **client_kwargs (dict): additional kwargs to pass onto boto3.client
    """

    label = "Recent backup"
    interval = 3600

    @staticmethod
    def check(bucket, age="25h", **client_kwargs):
        # list keys in bucket and check the latest upload was < 25 hours ago.
        client = boto3.client(service_name="s3", **client_kwargs)

        paginator = client.get_paginator("list_objects_v2")

        latest = 0
        for page in paginator.paginate(Bucket=bucket):
            for obj in page["Contents"]:
                timestamp = mktime(obj["LastModified"].timetuple())
                if timestamp > latest:
                    latest = timestamp

        return {
            "healthy": time() - latest < machine_seconds(age),
            "reason": "backup was %s old" % human_seconds(time() - latest),
        }


class PapouchTh2eTemperature(HealthCheck):
    """Checks the temperature reported by a Papouch TH2E

        Args:
            host (str): IP address or hostname of the Papouch unit
            _min (int): Temperature must not fall below this level
            _max (int): Temperature must not rise above this level

     """

    label = "Temperature"

    @staticmethod
    def check(host, _min=10, _max=35):
        r = requests.get("http://%s/fresh.xml" % host, timeout=5)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        value = root[0].attrib["val"]
        value = int(float(value))

        return {
            "value": "%s&deg;C" % value,
            "bar_min": "%s&deg;C" % _min,
            "bar_max": "%s&deg;C" % _max,
            "bar_percent": bar_percent(value, _max, _min),
            "healthy": value < _max and value > _min,
        }


class SsllabsReport(HealthCheck):
    """Checks SSL implementation using ssllabs.org

        Args:
            host (str): Host or IP address to scan
            min_grade (str): Minimum grade necessary (A+, A-, A-F, T, M)
    """

    label = "SSL implementation"
    interval = 24 * 3600

    def __init__(self, **kwargs):
        super(SsllabsReport, self).__init__(**kwargs)
        url = kwargs.get("url", self.entity.url)
        if "host" not in kwargs:
            self.check_kwargs["host"] = urlparse(url).hostname

    @staticmethod
    def check(host, min_grade="A+"):
        grades = ["A+", "A", "A-", "B", "C", "D", "E", "F", "T", "M"]
        grades = dict(zip(grades, range(len(grades))))  # grade -> score

        for x in range(100):
            response = requests.get(
                "https://api.ssllabs.com/api/v2/analyze",
                params={"host": host},
                timeout=5,
            )
            response.raise_for_status()
            report = response.json()
            sleep(2)

            if report["status"] == "READY":
                break

            if report["status"] == "ERROR":
                raise Exception(report["statusMessage"])
        else:
            raise TimeoutError("SSL labs test took too long")

        grade = report["endpoints"][0]["grade"]

        return {"healthy": grades[grade] <= grades[min_grade], "value": grade}


class PortScan(HealthCheck):
    """Scans host to check ports are closed. Synchronous so relatively quiet/slow.

        Args:
            host (str): Host or IP address to scan
            open_ports (list): list of (int) ports that must be open
            wait (float): Seconds to wait between port checks
    """

    label = "Firewall"
    interval = 24 * 3600

    @staticmethod
    def check(host, open_ports=[22, 80, 443], limit=65535, wait=0.5):
        for port in range(1, limit + 1):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.settimeout(0.5)
                result = sock.connect_ex((host, port))
                if result == 0 and port not in open_ports:
                    raise Exception("At least port %s is open but should not be" % port)
            except:
                raise
            finally:
                sock.close()


class Systemd(HealthCheck):
    """Checks all systemd services are OK"""

    label = "Systemd"

    @staticmethod
    def check():
        result = run(["systemctl", "is-system-running"], timeout=10, stdout=PIPE)

        value = result.stdout.decode().strip()

        return {"value": value.capitalize(), "healthy": result.returncode == 0}


class WorkerVersion(HealthCheck):
    """Checks dsportal worker version matches server version"""

    label = "Worker version"
    interval = 3600

    def __init__(self, **kwargs):
        super(WorkerVersion, self).__init__(**kwargs)
        self.check_kwargs["server_version"] = self.server_version

    @staticmethod
    def check(server_version):
        return {"healthy": version == server_version, "value": version}


class SimpleResolverCheck(HealthCheck):
    """Checks a hostname resolves to a particular IP. Very basic."""

    label = "DNS record integrity"
    interval = 600

    def __init__(self, **kwargs):
        super(SimpleResolverCheck, self).__init__(**kwargs)
        # inherit host from URL from entity by default
        domain = urllib.parse.urlparse(self.entity.url).netloc
        self.check_kwargs["domain"] = kwargs.get("domain", domain)

    @staticmethod
    def check(domain, expected_ip):
        ip = socket.gethostbyname(domain)

        if ip == expected_ip:
            return {"healthy": True, "reason": "Resolved IP matches expected IP"}
        else:
            return {
                "healthy": False,
                "reason": "Resolved IP does not match expected IP",
            }


class DomainExpiryCheck(HealthCheck):
    """Checks a domain is not about to expire"""

    label = "Domain expiry"
    # TODO  -- shorter interval when failing (and longer when OK)
    interval = 3600

    def __init__(self, **kwargs):
        super(self.__class__, self).__init__(**kwargs)
        # inherit host from URL from entity by default
        domain = urllib.parse.urlparse(self.entity.url).netloc
        self.check_kwargs["domain"] = kwargs.get("domain", domain)

    @staticmethod
    def check(domain, margin="4w"):
        expiry = whois(domain)["expiration_date"]

        if isinstance(expiry, list):
            expiry.sort()
            expiry = expiry[0]

        expiry = expiry.timestamp()
        remaining = expiry - time()
        margin = machine_seconds(margin)

        return {
            "healthy": remaining > margin,
            "value": human_seconds(remaining),
            "reason": "Domain expires in %s" % human_seconds(remaining),
        }


# see https://serverlesscode.com/post/ssl-expiration-alerts-with-lambda/
class CertificateExpiryCheck(HealthCheck):
    """Checks an SSL certificate is not about to expire"""

    label = "Certificate expiry"
    interval = 3600

    def __init__(self, **kwargs):
        super(self.__class__, self).__init__(**kwargs)
        # inherit host from URL from entity by default
        domain = urllib.parse.urlparse(self.entity.url).netloc
        self.check_kwargs["domain"] = kwargs.get("domain", domain)

    @staticmethod
    def check(domain, margin="2w"):
        margin = machine_seconds(margin)
        context = ssl.create_default_context()
        conn = context.wrap_socket(
            socket.socket(socket.AF_INET), server_hostname=domain
        )
        conn.settimeout(5)
        conn.connect((domain, 443))
        ssl_info = conn.getpeercert()
        expiry = datetime.strptime(
            ssl_info["notAfter"], r"%b %d %H:%M:%S %Y %Z"
        ).timestamp()
        remaining = expiry - time()

        return {
            "healthy": remaining > margin,
            "value": human_seconds(remaining),
            "reason": "SSL certificate expires in %s" % human_seconds(remaining),
        }


class ElasticSearchHealth(HealthCheck):
    label = "Elastic search health"

    @staticmethod
    def check(base_url, client_crt=None, client_key=None):
        url = os.path.join(base_url, "_cluster/health")

        # if this fails, it will throw an exception and dsportal will treat
        # this as UNKNOWN -- which is true. The endpoint should be monitored separately with HttpStatus
        r = requests.get(
            url=url, timeout=10, cert=(client_crt, client_key) if client_crt else None
        )
        r.raise_for_status()
        j = r.json()

        return {
            # warning would be yellow, and fail red.
            "healthy": j["status"] == "green",
            "reason": 'Cluster status is "{status}"'.format(**j),
            "value": j["status"],
        }


class GithubExposureCheck(HealthCheck):
    """Checks a github user or organisation has only the given public repositories.

        Args:
            username (str): username or github organisation
            expected_repos (list): a list of expected (short) repository names without org/user/or .git.

     """

    label = "Github exposure"
    interval = 84600

    @staticmethod
    def check(username, expected_repos=[]):
        r = requests.get("https://api.github.com/users/%s/repos" % username, timeout=5)
        r.raise_for_status()

        repos_exposed = [repo["name"] for repo in r.json()]

        for repo in repos_exposed:
            if repo not in expected_repos:
                return {"healthy": True, "reason": "%s repo is unexpectedly public"}

        return {"healthy": True, "reason": "No unexpected repositories are public"}


class PortCheck(HealthCheck):
    """Checks a given port is listening. Good to check an internet connection from outside.
        Args:
            host (str): Host or IP address to scan
            port (int): Port to check
    """

    label = "Internet connection"
    interval = 600

    @staticmethod
    def check(host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            if result == 0:
                return {
                    "healthy": True,
                    "reason": "Network is responding",
                    "value": "Online",
                }
            else:
                return {
                    "healthy": True,
                    "reason": "Network is down",
                    "value": "Offline",
                }

        finally:
            sock.close()
