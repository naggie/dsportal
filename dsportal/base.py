from uuid import uuid4
from time import time
from random import randint
from functools import wraps
from collections import OrderedDict, defaultdict
from time import sleep
from time import monotonic
from dsportal.util import extract_classes
from dsportal.util import validate_result
from dsportal.util import extract_classes
from dsportal.util import TTLQueue
from dsportal.util import ItemExpired
from dsportal.util import machine_seconds
import queue
from threading import Thread
import asyncio
from dsportal import __version__ as version

import logging

log = logging.getLogger(__name__)


class Entity(object):
    def __init__(self, name, tab, worker=None, healthchecks=[], description=""):
        # Used for DOM ID as well
        self.id = str(uuid4())

        self.tab = tab

        # description of the real world thing this instance represents
        self.name = name
        self.description = description

        self.cls = self.__class__.__name__

        # default worker given to child healthchecks that don't have worker
        # defined
        self.worker = worker

        # Aggregate of all health checks belonging to this entity
        # Unknown, yet
        self.healthy = None

        HCLASSES = extract_classes("dsportal.healthchecks", HealthCheck)

        self.healthchecks = list()

        for h in healthchecks:
            cls = h.pop("cls")
            h["worker"] = h.get("worker", worker)
            healthcheck = HCLASSES[cls](entity=self, **h)  # TODO handle keyerror here
            self.healthchecks.append(healthcheck)

    def evaluate_health(self):
        self.healthy = True

        for h in self.healthchecks:
            if h.result["healthy"] is None:
                self.healthy = None
                break

        for h in self.healthchecks:
            if h.result["healthy"] is False:
                self.healthy = False
                break


class HealthCheck(object):
    label = "The name of this value"
    description = "What this health check does"

    interval = (
        60
    )  # default in seconds, can be overridden in configuration using notation accepted by machine_seconds()

    def __init__(self, entity, interval=None, worker=None, label=None, **kwargs):
        self.id = str(uuid4())

        if entity and not isinstance(entity, Entity):
            raise ValueError('Entity instance expected for "entity"')

        self.entity = entity

        self.worker = worker
        self.cls = self.__class__.__name__

        # kwargs to pass to check
        self.check_kwargs = kwargs

        self.interval = machine_seconds(interval) if interval else self.interval

        self.timeout = self.interval * 2

        self.result = {"healthy": None, "reason": "Waiting for check"}

        # randomise for uniform distribution of health checks rather than
        # periodic stampedes
        # warm up over interval, max 1 min
        self.delay = randint(0, min(self.interval, 60))

        self.last_start = None
        self.last_finish = None

        self.server_version = version

        # set an alias for 2 or more of the same healthcheck on one entity,
        # allowing differentiation.
        if label:
            self.label = label

    def update(self, result):
        validate_result(result)
        self.result = result
        self.last_finish = monotonic()

        if result["healthy"]:
            log.debug("Check passed: %s %s", self.cls, self.check_kwargs)
        else:
            log.debug(
                "Check failed: %s %s %s",
                self.cls,
                self.entity.name,
                result.get("reason", ""),
            )
            log.debug("Result: %s", result)

        # TODO Entity.healty could be a @property -- however, may complicate client patching
        self.entity.evaluate_health()

    @staticmethod
    def check():
        """Run healthcheck. Must be stateless. Must not be run directly. Use
        run(). Exceptions will be caught and treated as failures"""
        raise NotImplemented()

    @classmethod
    def run_check(CLASS, **kwargs):
        """Run check in exception wrapper"""
        log.debug("Processing check: %s %s", CLASS.__name__, kwargs)
        try:
            result = CLASS.check(**kwargs)
        except Exception as e:
            result = {"healthy": None, "reason": str(e)}
        validate_result(result)

        if not result["healthy"]:
            log.debug("Check failed: %s %s", CLASS.__name__, result.get("reason", ""))
            log.debug("Result: %s", result)

        if "reason" not in result:
            result["reason"] = ""

        if "value" not in result:
            result["value"] = ""

        validate_result(result, annotated=True)

        return result

    async def loop(self, callback, initial_delay=0):
        """Callback (self) at interval. Add to event loop as guarded task."""
        await asyncio.sleep(initial_delay)
        await asyncio.sleep(self.delay)

        while True:
            self.last_start = monotonic()
            callback(self)
            await asyncio.sleep(self.interval)

    def __str__(self):
        return "{cls} {check_kwargs}".format(**self.__dict__)


class Index(object):
    "Keeps track of HealthcheckState and Entity objects organised by tabs, worker, etc"

    def __init__(self, name):
        self.name = name
        # indices
        self.entities = list()
        self.entities_by_tab = OrderedDict()
        self.entities_by_id = dict()

        self.healthchecks = list()
        self.healthchecks_by_worker = defaultdict(list)
        self.healthcheck_by_id = dict()

        # TODO remove unused indicies

        self.worker_locks = set()

        self.entity_classes = extract_classes("dsportal.entities", Entity)

        self.worker_websockets = dict()
        self.client_websockets = list()

        # list of tasks registered on the event loop to schedule healthchecks
        self.tasks = list()

        self.local_worker = Worker()
        self.local_worker.start()

        self.alerter_classes = extract_classes("dsportal.alerters", Alerter)
        self.alerters = list()

    def instantiate_entity(self, cls, **config):
        try:
            entity = self.entity_classes[cls](**config)
        except KeyError:
            raise ValueError("Entity class %s does not exist" % cls)

        self.entities.append(entity)
        self.entities_by_id[entity.id] = entity

        # in order of definition!
        if entity.tab in self.entities_by_tab:
            self.entities_by_tab[entity.tab].append(entity)
        else:
            self.entities_by_tab[entity.tab] = [entity]

        for hcs in entity.healthchecks:
            self.healthchecks.append(hcs)
            self.healthchecks_by_worker[hcs.worker].append(hcs)
            self.healthcheck_by_id[hcs.id] = hcs

    def register_tasks(self, loop):
        for h in self.healthchecks:
            # wait 12 seconds for all workers to reconnect
            task = loop.create_task(
                h.loop(self._dispatch_check, initial_delay=12 if h.worker else 0)
            )

            log.debug("Registered %s for %s", h, h.worker or "local worker")
            self.tasks.append(task)

        loop.create_task(
            self.local_worker.read_results(lambda r: self.dispatch_result(r[0], r[1]))
        )

        loop.create_task(self.check_timeouts())

    def _dispatch_check(self, h):
        if h.worker == "local" or h.worker == None:
            self.local_worker.enqueue(h.cls, h.id, **h.check_kwargs)
        else:
            try:
                self.worker_websockets[h.worker].send_json(
                    (h.cls, h.id, h.check_kwargs)
                )
            except KeyError:
                log.warn("Worker %s not connected for healthcheck", h.worker)
                # Invalidate result
                result = {"healthy": None, "reason": "Worker %s was offline" % h.worker}
                validate_result(result)
                self.dispatch_result(h.id, result)
                # NOTE Context was set to worker name, however connection
                # failures may correlate resulting in `n` notifications instead
                # of one. If notifications are not correlated, the first
                # notification should be sufficient to prompt investigation.
                # NOTE Worker connection issues are generally inconsequential
                # and annoying. QoS should be implemented to make sure worker
                # connection issues don't matter as much.
                # self._alert('workers','Worker(s) are having connection issues')

    def dispatch_result(self, id, result):
        h = self.healthcheck_by_id[id]
        h.update(result)

        # TODO delta updates!
        for ws in self.client_websockets:
            ws.send_json((id, healthcheck.result))

        if result["healthy"] == False:
            # stop iOS previews: http://support.fastsms.co.uk/knowledgebase/ios-10-update-impacts-sms-messages/
            # leave a space at the end!
            self._alert(
                h.id,
                "{h.label} unhealthy on {h.entity.name}, reason: {h.result[reason]} ".format(
                    h=h
                ),
            )

    @property
    def healthy_healthchecks(self):
        return [h for h in self.healthchecks if h.result["healthy"] == True]

    @property
    def unknown_healthchecks(self):
        return [h for h in self.healthchecks if h.result["healthy"] == None]

    @property
    def unhealthy_healthchecks(self):
        return [h for h in self.healthchecks if h.result["healthy"] == False]

    @property
    def healthy_entities(self):
        return [e for e in self.entities if e.healthy == True]

    @property
    def unknown_entities(self):
        return [e for e in self.entities if e.healthy == None and e.healthchecks]

    @property
    def unhealthy_entities(self):
        return [e for e in self.entities if e.healthy == False]

    async def check_timeouts(self):
        while True:
            await asyncio.sleep(10)
            t = monotonic()
            for h in self.healthchecks:
                if h.last_finish and h.last_finish < t - h.timeout:
                    log.warn("Healthcheck %s timeout", h)
                    # Invalidate result
                    result = {"healthy": None}
                    validate_result(result)
                    self.dispatch_result(h.id, result)

    def _alert(self, context, text):
        for a in self.alerters:
            a.alert(context, text)

    def instantiate_alerter(self, cls, **kwargs):
        try:
            alerter = self.alerter_classes[cls](name=self.name, **kwargs)
        except KeyError:
            raise ValueError("Alerter class %s does not exist" % cls)

        log.debug("Registered alerter: %s", alerter)
        self.alerters.append(alerter)


class Worker(object):
    def __init__(self):
        # drop items if workers are too busy -- time not number of items
        self.work_queue = TTLQueue(maxsize=1000, ttl=5)
        # connection problems should not result in old results coming backk
        self.result_queue = TTLQueue(maxsize=1000, ttl=5)

        self.hclasses = extract_classes("dsportal.healthchecks", HealthCheck)

    def start(self, count=4):
        for x in range(count):
            t = Thread()
            t = Thread(target=self._worker)
            t.daemon = True
            t.start()

        return t

    def enqueue(self, cls, id, **kwargs):
        self.work_queue.put_nowait((cls, id, kwargs))
        log.debug("Check enqueued: %s", cls)

    def _worker(self):
        while True:
            try:
                cls, id, kwargs = self.work_queue.get_wait()
            except ItemExpired as e:
                cls, id, kwargs = e.item
                self.result_queue.put_nowait(
                    (
                        id,
                        {
                            "healthy": None,
                            "reason": "Worker was too busy to run this health check in time",
                        },
                    )
                )
                log.warn("Check dropped: %s", cls)
                continue

            try:
                fn = self.hclasses[cls].run_check
            except KeyError:
                self.result_queue.put_nowait(
                    (id, {"healthy": None, "reason": "Healthcheck not known by worker"})
                )
                log.warn("Check unknown: %s", cls)
                self.work_queue.task_done()
                continue

            result = fn(**kwargs)
            self.work_queue.task_done()
            self.result_queue.put_nowait((id, result))

    async def read_results(self, callback):
        while True:
            try:
                while True:
                    response = self.result_queue.get_nowait()
                    callback(response)
            except queue.Empty:
                pass
            except ItemExpired:
                pass

            # There's got to be a better way! (Spills milk everywhere)
            await asyncio.sleep(0.01)


class Alerter(object):
    """ABC for sending alerts that require human intervention. Will throttle
    events from the same given context by interval. Example contexts: worker,
    healthcheck ID"""

    def __init__(self, name, interval="12h", deploy_snooze=3600):
        # last notification times by context
        # time is monotonic unix timestamp
        # preloaded with now -- so alerts come at least interval after
        # deplotyment
        self.start = monotonic()
        self.interval = machine_seconds(interval)
        self.last_notifications = defaultdict(
            lambda: self.start - self.interval + deploy_snooze
        )

        # name of system (domain name)
        self.name = name

    def alert(self, context, text):
        if self.last_notifications[context] < monotonic() - self.interval:
            self.last_notifications[context] = monotonic()
            log.info("Broadcasting alert: %s", text)
            self.broadcast_alert(text)
        else:
            log.debug("Alert throttled: %s (interval:%s)", text, self.interval)

    def broadcast_alert(self, text):
        raise NotImplemented()
