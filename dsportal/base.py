from uuid import uuid4
import logging
from time import time
from random import randint
from functools import wraps
from collections import OrderedDict,defaultdict
from time import sleep
from time import monotonic
from dsportal.util import extract_classes
from dsportal.util import validate_result
from dsportal.util import extract_classes
from dsportal.util import TTLQueue
from dsportal.util import ItemExpired
from threading import Thread
import asyncio

log = logging.getLogger(__name__)


class Entity(object):
    def __init__(self,name,tab,worker,healthchecks=[],description=""):
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

        HCLASSES = extract_classes('dsportal.healthchecks',HealthCheck)

        self.healthchecks = list()

        for h in healthchecks:
            cls = h.pop('cls')
            h['worker'] = h.get('worker',worker)
            healthcheck = HCLASSES[cls](entity=self,**h) # TODO handle keyerror here
            self.healthchecks.append(healthcheck)


    def evaluate_health(self):
        self.healthy = True

        for h in self.healthchecks:
            if h.result['healthy'] is None:
                self.healthy = None
                break

        for h in self.healthchecks:
            if h.result['healthy'] is False:
                self.healthy = False
                break




class HealthCheck(object):
    label = "The name of this value"
    description = "What this health check does"

    interval = 60 # default, can be overridden in configuration

    def __init__(self,entity,interval=None,worker=None,**kwargs):
        self.id = str(uuid4())

        if not isinstance(entity,Entity):
            raise ValueError('Entity instance expected for "entity"')

        self.entity = entity

        self.worker = worker
        self.cls = self.__class__.__name__

        # kwargs to pass to check
        self.check_kwargs = kwargs

        self.interval = interval or self.interval

        self.result = {
                "healthy": None,
                }


        # randomise for uniform distribution of health checks rather than
        # periodic stampedes
        # warm up over interval, max 1 min
        self.delay = randint(0,max(self.interval,60))

        self.last_start = None
        self.last_finish = None


    def update(self,result):
        validate_result(result)
        self.result = result
        self.last_finish = monotonic()

        if result['healthy']:
            log.debug('Check passed: %s %s',self.cls,self.check_kwargs)
        else:
            log.warn('Check failed: %s %s %s',self.cls,self.check_kwargs,result.get('exception_msg',''))
            log.debug('Result: %s',result)

        self.entity.evaluate_health()


    @staticmethod
    def check():
        '''Run healthcheck. Must be stateless. Must not be run directly. Use
        run(). Exceptions will be caught and treated as failures'''
        raise NotImplemented()


    @classmethod
    def run_check(CLASS,**kwargs):
        '''Run check in exception wrapper'''
        log.info('Processing check: %s %s',CLASS.__name__,kwargs)
        try:
            result = CLASS.check(**kwargs)
        except Exception as e:
            result = {
                    "healthy" : False,
                    "exception_msg" : "{e.__class__.__name__}: {e}".format(e=e),
                }
        validate_result(result)

        if not result['healthy']:
            log.warn('Check failed: %s %s %s',CLASS.__name__,kwargs,result.get('exception_msg',''))
            log.debug('Result: %s',result)

        return result


    async def loop(self,callback):
        """Callback (self) at interval. Add to event loop as guarded task."""
        await asyncio.sleep(self.delay)

        while True:
            self.last_start = monotonic()
            callback(self)
            await asyncio.sleep(self.interval)


    def __str__(self):
        return '{cls} {check_kwargs}'.format(**self.__dict__)


class Index(object):
    'Keeps track of HealthcheckState and Entity objects organised by tabs, worker, etc'
    def __init__(self):
        # indices
        self.entities = list()
        self.entities_by_tab = OrderedDict()
        self.entities_by_id = dict()

        self.healthchecks = list()
        self.healthchecks_by_worker = defaultdict(list)
        self.healthcheck_by_id = dict()

        self.worker_locks = set()

        self.ECLASSES = extract_classes('dsportal.entities',Entity)

        self.worker_websockets = dict()
        self.client_websockets = list()

        # list of tasks registered on the event loop to schedule healthchecks
        self.tasks = list()


    def _index_entity(self,entity):
        if not isinstance(entity,Entity):
            raise ValueError('Instance of an Entity (subclass) required')

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


    def instantiate_entity(self,cls,**config):
        entity = self.ECLASSES[cls](**config)
        self._index_entity(entity)

    def register_tasks(self,loop):
        for h in self.healthchecks:
            task = loop.create_task(h.loop(self._dispatch_check))
            log.info('Registered %s for %s',h,h.worker)
            self.tasks.append(task)


    def _dispatch_check(self,h):
        try:
            self.worker_websockets[h.worker].send_json((h.cls,h.id,h.check_kwargs))
        except KeyError:
            log.warn('Worker %s not connected for healthcheck %s',h.worker,h)

    def dispatch_result(self,id,result):
        h = self.healthcheck_by_id[id]
        h.update(result)

        # TODO entity updates
        # TODO delta updates!
        # TODO wire this up!
        for ws in self.client_websockets:
            ws.send_json((id,healthcheck.result))





class Worker(object):
    def __init__(self):
        # drop items if workers are too busy -- time not number of items
        self.work_queue = TTLQueue(maxsize=1000,ttl=5)
        # connection problems should not result in old results coming backk
        self.result_queue = TTLQueue(maxsize=1000,ttl=5)

        self.hclasses = extract_classes('dsportal.healthchecks',HealthCheck)

    def start_workers(self,count=4):
        for x in range(count):
            t = Thread()
            t = Thread(target=self._worker)
            t.daemon = True
            t.start()

        return t

    def enqueue(self,cls,id,**kwargs):
        self.work_queue.put_nowait((cls,id,kwargs))
        log.debug('Check enqueued: %s',cls)


    def _worker(self):
        while True:
            try:
                cls,id,kwargs = self.work_queue.get_wait()
            except ItemExpired as e:
                cls,id,kwargs = e.item
                self.result_queue.put_nowait((id,{
                        'healthy': None,
                        'exception_msg' : 'Worker was too busy to run this health check in time',
                    }))
                log.warn('Check dropped: %s',cls)
                continue

            result = self.hclasses[cls].run_check(**kwargs)
            self.work_queue.task_done()
            self.result_queue.put_nowait((id,result))


    def drain(self):
        try:
            self.result_queue.get(block=False)
            self.result_queue.task_done()
        except queue.Empty:
            return



