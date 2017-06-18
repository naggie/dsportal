import logging
import colorlog
import queue
from time import monotonic,time
from os import path
import importlib
import inspect
import re

def get_ups_data(max_age=120):
    "Get UPS stats from apcupsd via /var/log/apcupsd.status"
    fp = '/var/log/apcupsd.status'

    mtime = path.getmtime(fp)

    if time() - mtime > max_age:
        raise Exception("UPS data isn't being updated")

    info = {}
    with open(fp) as f:
        for line in f:
            m = re.search('(\w+)\s*:\s*((\d|\w)+)', line)
            if m:
                try:
                    info[m.group(1)] = int(m.group(2))
                except ValueError:
                    info[m.group(1)] = str(m.group(2))

    if info['STATUS'] == "COMMLOST":
        raise Exception('Could not communicate with UPS')

    return info


def bar_percentage(value,_max,_min=0):
    'Return a value, capped integer 0-100 to render a bar chart'
    val = (value-_min) / (_max-_min)
    val *= 100
    val = int(val)
    val = min(val,100)
    val = max(val,0)
    return val


def setup_logging(debug=False):
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter('%(asctime)s  %(log_color)s%(levelname)s%(reset)s %(name)s: %(message)s'))
    logger = colorlog.getLogger()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.addHandler(handler)


def human_bytes(b):
    return b

class ItemExpired(Exception):
    def __init__(self,item,*args,**kwargs):
        super(ItemExpired,self).__init__(*args,**kwargs)
        self.item = item

class TTLQueue(queue.Queue):
    def __init__(self,*args,ttl=5,**kwargs):
        super(TTLQueue,self).__init__(*args,**kwargs)
        self.ttl = ttl

    def put_nowait(self,item):
        expiry = monotonic() + self.ttl
        super(TTLQueue,self).put((item,expiry),block=False)

    def get_nowait(self):
        item,expiry = super(TTLQueue,self).get(block=False)

        if monotonic() > expiry:
            self.task_done()
            raise ItemExpired(item)

        return item

    def get_wait(self):
        while True:
            item,expiry = super(TTLQueue,self).get(block=True)

            if monotonic() > expiry:
                self.task_done()
                raise ItemExpired(item)

            break

        return item

    def put(self,*args,**kwargs):
        raise NotImplementedError('use put_nowait')

    def get(self,*args,**kwargs):
        raise NotImplementedError('use get_nowait')


def extract_classes(module_path,Class):
    classes = dict()

    module = importlib.import_module(module_path)

    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and Class in inspect.getmro(obj):
            classes[obj.__name__] = obj

    return classes

# TODO marshal validation errors somehow
def validate_result(result):
    if type(result) != dict:
        raise ValueError('Healthcheck result must be a dict')

    if 'healthy' not in result:
        raise ValueError('Heathcheck result must have `healthy` key: a bool or None.')

    if type(result['healthy']) != bool and result['healthy'] != None:
        raise ValueError('`healthy` key must be bool or None. None means unknown-yet or not-applicable.')

    #if result['healthy'] == False and 'reason' not in result:
    #    raise ValueError('reason must be set if healthy is False')


def slug(string):
    return re.sub(r'\W','_',string).lower()

def human_bytes(num):
    for unit in ['B','KB','MB','GB','TB','PB','EB','ZB']:
        if abs(num) < 1024.0:
            return "%3.1f %s" % (num, unit)
        num /= 1024.0

    return "%.1f %s" % (num, 'YiB')
