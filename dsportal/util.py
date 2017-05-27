import logging
import colorlog
import queue
from time import monotonic
from os import path

def get_ups_data():
    "Get UPS stats from apcupsd via apcaccess"

    if not path.exists('/sbin/apcaccess'):
        raise RuntimeError('/sbin/apcaccess not found')

    dump = commands.getstatusoutput('/sbin/apcaccess')

    if dump[0]:
        raise RuntimeError('Failed to run apcaccess command')

    lines = string.split(dump[1], "\n")

    info = {}
    for line in lines:
        m = re.search('(\w+)\s*:\s*(\d+)', line)
        if m:
            info[m.group(1)] = int(m.group(2))

    return info


def percent_bar(value,_max,_min=0):
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
