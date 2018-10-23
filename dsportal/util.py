import logging
import colorlog
import queue
from time import monotonic, time
from os import path
import importlib
import inspect
import re
from collections import OrderedDict
from os import getenv

APCUPSD_CONF_FILE = "/etc/apcupsd/apcupsd.conf"
APCUPSD_STATFILE = None
APCUPSD_STATTIME = 60

try:
    with open(APCUPSD_CONF_FILE) as f:
        for line in f:
            parts = line.split(None, 1)

            if len(parts) != 2:
                continue

            k, v = parts

            if k == "STATFILE":
                APCUPSD_STATFILE = v.strip()

            if k == "STATTIME":
                APCUPSD_STATTIME = int(v)

except FileNotFoundError:
    pass


def get_ups_data():
    "Get UPS stats from apcupsd via STATFILE"

    if not APCUPSD_STATFILE:
        raise Exception("Could not parse location of STATFILE. Is it configured?")

    mtime = path.getmtime(APCUPSD_STATFILE)

    if time() - mtime > APCUPSD_STATTIME * 4:
        raise Exception("UPS data isn't being updated")

    info = {}
    with open(APCUPSD_STATFILE) as f:
        for line in f:
            m = re.search("(\w+)\s*:\s*((\d|\w)+)", line)
            if m:
                try:
                    info[m.group(1)] = int(m.group(2))
                except ValueError:
                    info[m.group(1)] = str(m.group(2))

    if info["STATUS"] == "COMMLOST":
        raise Exception("Could not communicate with UPS")

    return info


def bar_percent(value, _max, _min=0):
    "Return a value, capped integer 0-100 to render a bar chart"
    val = (value - _min) / (_max - _min)
    val *= 100
    val = int(val)
    val = min(val, 100)
    val = max(val, 0)
    return val


def setup_logging():
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(asctime)s  %(log_color)s%(levelname)s%(reset)s %(name)s: %(message)s"
        )
    )
    logger = colorlog.getLogger()

    debug = getenv("DSPORTAL_DEBUG", False)

    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.addHandler(handler)

    # avoid spam
    logging.getLogger("botocore").setLevel(logging.CRITICAL)


class ItemExpired(Exception):
    def __init__(self, item, *args, **kwargs):
        super(ItemExpired, self).__init__(*args, **kwargs)
        self.item = item


class TTLQueue(queue.Queue):
    def __init__(self, *args, ttl=5, **kwargs):
        super(TTLQueue, self).__init__(*args, **kwargs)
        self.ttl = ttl

    def put_nowait(self, item):
        expiry = monotonic() + self.ttl
        super(TTLQueue, self).put((item, expiry), block=False)

    def get_nowait(self):
        item, expiry = super(TTLQueue, self).get(block=False)

        if monotonic() > expiry:
            self.task_done()
            raise ItemExpired(item)

        return item

    def get_wait(self):
        while True:
            item, expiry = super(TTLQueue, self).get(block=True)

            if monotonic() > expiry:
                self.task_done()
                raise ItemExpired(item)

            break

        return item

    def put(self, *args, **kwargs):
        raise NotImplementedError("use put_nowait")

    def get(self, *args, **kwargs):
        raise NotImplementedError("use get_nowait")


def extract_classes(module_path, Class):
    classes = dict()

    module = importlib.import_module(module_path)

    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and Class in inspect.getmro(obj):
            classes[obj.__name__] = obj

    return classes


# TODO marshal validation errors somehow
def validate_result(result, annotated=False):
    if type(result) != dict:
        raise ValueError("Healthcheck result must be a dict")

    if "healthy" not in result:
        raise ValueError("Heathcheck result must have `healthy` key: a bool or None.")

    if type(result["healthy"]) != bool and result["healthy"] != None:
        raise ValueError(
            "`healthy` key must be bool or None. None means unknown-yet or not-applicable."
        )

    if "value" in result:
        if str(result["value"]).endswith("B") and "bytes" not in result:
            raise ValueError(
                "If value is in bytes (with magnitude) bytes key must be present"
            )

    if "bytes" in result:
        if type(result["bytes"]) != int:
            raise ValueError("bytes must be an int")

    if "bar_percent" in result:
        if not isinstance(result["bar_percent"], (int, float)):
            raise ValueError("bar_percent must be a number")

        if result["bar_percent"] < 0 or result["bar_percent"] > 100:
            raise ValueError("bar_percent must be 0-100. Use util.bar_percent()")

        if "bar_min" not in result or "bar_max" not in result:
            raise ValueError(
                "bar_min and bar_max have to be in result if bar_percent is defined"
            )

    if annotated:
        if "reason" not in result:
            raise ValueError(
                "Annotated Heathcheck result must have `reason` key: exception message, nominal failure reason on nominal success reason"
            )

        if "value" not in result:
            raise ValueError(
                "Annotated Heathcheck result must have `value` key, which can be empty"
            )


def slug(string):
    return re.sub(r"\W+", "_", string).lower()


def human_bytes(num):
    for unit in ["B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
        if abs(num) < 1000.0:
            return "%3.1f %s" % (num, unit)
        num /= 1000.0

    return "%.1f %s" % (num, "YiB")


time_mags = OrderedDict(
    [("y", 31557600), ("w", 604800), ("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]
)


def human_seconds(num, max_sf=2):
    notation = ""
    sf = 0
    for suf, size in time_mags.items():
        count = int(num // size)
        num %= size  # remainder
        if count:
            notation += str(count) + suf
            sf += 1
        if sf >= max_sf:
            break

    return notation


def machine_seconds(notation):
    """ convert human notation to seconds, eg 1m -> 60 """
    notation = str(notation)
    if notation[-1] not in time_mags.keys():
        notation += "s"

    seconds = 0
    for c in re.sub(r"([a-z])(\d)", r"\1 \2", notation).split():
        try:
            num = int(c[:-1])
            suf = c[-1]
            seconds += num * time_mags[suf]
        except (ValueError, KeyError):
            raise ValueError(
                "Time notations must be single characters prefixed by int number. Valid characters are %s. Mixed notations are OK."
                % ",".join(time_mags.keys())
            )

    return seconds
