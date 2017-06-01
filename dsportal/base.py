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
            healthcheck = HCLASSES[cls](**h) # TODO handle keyerror here
            self.healthchecks.append(healthcheck)



class HealthCheck(object):
    label = "The name of this value"
    description = "What this health check does"

    interval = 60 # default, can be overridden in configuration

    def __init__(self,interval=None,worker=None,**kwargs):
        self.id = str(uuid4())

        self.worker = worker
        self.cls = self.__class__.__name__

        # kwargs to pass to check
        self.check_kwargs = kwargs

        self.interval = interval or self.interval

        self.result = {
                "healthy": None,
                }

        self.healthy = None

        # randomise for uniform distribution of health checks rather than
        # periodic stampedes
        # warm up over interval, max 1 min
        self.delay = randint(0,max(self.interval,60))

        self.last_start = None
        self.last_finish = None


    def update(self,result):
        validate_result(result)
        self.result = result
        self.healthy = result['healthy']
        self.last_finish = monotonic()

        if not result['healthy']:
            log.warn('Check failed: %s %s %s',self.cls,self.check_kwargs,result['error_message'])


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
                    "error_message" : "{e.__class__.__name__}: {e}".format(e=e),
                }
        validate_result(result)

        if not result['healthy']:
            log.warn('Check failed: %s %s %s',CLASS.__name__,kwargs,result['error_message'])

        return result


    async def loop(self,callback):
        """Callback (cls,id,kwargs) at interval. Add to event loop as guarded task."""
        await asyncio.sleep(self.delay)

        while True:
            self.last_start = monotonic()
            callback((self.cls,self.id,self.check_kwargs))
            await asyncio.sleep(self.interval)


    def __str__(self):
        return '{cls} {check_kwargs}'.format(**self.__dict__)


#    # used by scheduler to decide when to put job on queue
#    # TODO probably replace with async sleep loop and asyncio create_task (or gather? or ensure_future?)
#    def must_run(self):
#        t = time()
#        if self.last_attempt_time + self.interval <= t:
#            self.last_attempt_time = t
#            return True
#        else:
#            return False



class Index(object):
    'Keeps track of HealthcheckState and Entity objects organised by tabs, worker, etc'
    def __init__(self):
        # indices
        self.entities = list()
        self.entities_by_tab = OrderedDict()
        self.entities_by_id = dict()

        self.healthchecks = list()
        self.healthcheck_by_worker = defaultdict(list)
        self.healthcheck_by_id = dict()

        self.ECLASSES = extract_classes('dsportal.entities',Entity)


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
            self.healthcheck_by_worker[hcs.worker].append(hcs)
            self.healthcheck_by_id[hcs.id] = hcs


    def instantiate_entity(self,cls,**config):
        entity = self.ECLASSES[cls](**config)
        self._index_entity(entity)


