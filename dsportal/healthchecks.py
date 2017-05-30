from dsportal.base import healthcheckfn
from dsportal.util import get_ups_data,bar_percentage
import os
import multiprocessing
import requests

@healthcheckfn
def ram_usage():
    "Checks RAM usage is less than 90%. Does not count cache and buffers."
    from time import sleep; sleep(0.5)
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
            "healthy": value < (0.9*total)/100,
            }

# TODO maybe this should be a (stateless) class
ram_usage.label = 'RAM usage'


@healthcheckfn
def cpu_usage(_max=200):
    "Checks CPU load is nominal."
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

@healthcheckfn
def disk_usage():
    "Inspects used and available blocks on given mount points."
    s = statvfs(self.mountpoint)
    free = s.f_bsize * s.f_bavail
    total = s.f_bsize * s.f_blocks
    usage = total - free

    return {
            "value": value,
            "bar_min": "0MB",
            "bar_max": human_bytes(total), # TODO standardise way of representing magnitude
            "bar_percentage": bar_percentage(usage,total),
            "healthy": usage < (0.8*total)/100,
            }

@healthcheckfn
def ups_voltage(_min=216,_max=253):
    "Checks mains voltage falls within UK legal limits of 230V +10% -6%"
    info = util.get_ups_data()
    return {
        "bar_min":'%sV' % _min,
        "bar_max":'%sV' % _max,
        'bar_percentage': bar_percentage(info['LINEV'],_max,_min),
        'value': info['LINEV'],
        "healthy": (info['LINEV'] < _max) and (info['LINEV'] > _max),
    }

@healthcheckfn
def ups_load():
    "Checks UPS is not overloaded"
    info = util.get_ups_data()
    return {
        "bar_min":"0%",
        "bar_max":"100%",
        'bar_percentage': info['LOADPCT'],
        'value': '%s%%' % info['LOADPCT'],
        "healthy": info['LOADPCT'] < 90,
    }

@healthcheckfn
def ups_battery():
    "Checks estimated time remaining and percentage"

    info = util.get_ups_data()
    return {
        "bar_min":"0%",
        "bar_max":"100%",
        'bar_percentage': info['BCHARGE'],
        'value': info['TIMELEFT'], # ???
        "healthy": info['TIMELEFT'] < 300,
    }


@healthcheckfn
def uptime():
    "Specify uptime in days"

    with open('/proc/uptime', 'r') as f:
        line = f.readline()

    seconds = line.partition(' ')[0]
    seconds = float(seconds)

    days = int(round(seconds/86400))

    return {
        "healthy": True,
        "value": '%s days' % days,
        }


@healthcheckfn
def cpu_temperature():
    "Checks CPU Temperature is nominal"

@healthcheckfn
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



@healthcheckfn
def btrfs_pool():
    "Checks BTRFS health"

@healthcheckfn
def http_status(url,timeout=10):
    "Checks service returns 200 OK"

    r = requests.get(url,timeout=timeout)
    r.raise_for_status()

    return {
            "healthy": True,
            }

@healthcheckfn
def broken_links(url,ignore):
    "Crawls website for broken links"
    # https://wummel.github.io/linkchecker/ but use git to install latest revision
    # example linkchecker --check-html --check-css --ignore-url 'xmlrpc.php' --user-agent 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.  110 Safari/537.36' https://cydarmedical.com

# run time -- 5 mins or so for small website
# run every 5 hours
broken_links.interval = 5*60*60

@healthcheckfn
def certificate_expiry():
    "Checks certificate isn't near expiry"
    # https://stackoverflow.com/questions/7689941/how-can-i-retrieve-the-tls-ssl-peer-certificate-of-a-remote-host-using-python

@healthcheckfn
def s3_backup_checker(bucket,hours=25):
    "Checks to see that a backup was made in the last 25 hours"
    # list keys in bucket and check the latest upload was < 25 hours ago.

@healthcheckfn
def papouch_th2e_temperature(
        url,
        min_temp=10,
        max_temp=35,
        min_hum=20,
        max_hum=80):
    """Check the temperature reported by a Papouch TH2E"""

@healthcheckfn
def ssllabs_report(host,min_grade="A+"):
    grades = ['A+','A','A-','B','C','D','E','F','T','M']

    for x in range(100):
        report = requests.get('https://api.ssllabs.com/api/v2/analyze',params={
            "host": host,
            },timeout=5)
        sleep(2)
        print(report)

        if report['status'] == 'READY':
            break
    else:
        raise TimeoutError('SSL labs test took too long')

    grade = report['endpoints'][0]['grade']

    return {
        'healthy': grades[grade] <= grades[min_grade],
            }
