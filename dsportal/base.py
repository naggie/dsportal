from uuid import uuid4
from time import time
from random import randint
from functools import wraps
from collections import OrderedDict,defaultdict
import inspect
import dsportal.entities
import dsportal.healthchecks
import sleep
from time import monotonic
from util import extract_classes
from util import validate_result


class Entity(object):
    def __init__(self,name,tab,worker,healthchecks=[],description=""):
        # Used for DOM ID as well
        self.id = str(uuid4())

        self.tab = tab

        # description of the real world thing this instance represents
        self.name = name
        self.description = description

        # default worker given to child healthchecks that don't have worker
        # defined
        self.worker = worker

        # Aggregate of all health checks belonging to this entity
        # Unknown, yet
        self.healthy = None

        self.healthChecks = list()

        for h in healthchecks:
            cls = h.pop('cls')
            h['worker'] = h['worker'] or worker
            HEALTHCHECKS[cls](**h)
            self.healthChecks.append(healthCheck)



class HealthCheck(object):
    label = "The name of this value"
    description = "What this health check does"

    interval = 60 # default, can be overridden in configuration

    def __init__(self,cls,interval=None,worker=None,**kwargs):
        self.id = str(uuid4())

        self.worker = worker

        # kwargs to pass to check
        self.fn_kwargs = kwargs

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

    @staticmethod
    def check():
        '''Run healthcheck. Must be stateless. Must not be run directly. Use
        run(). Exceptions will be caught and treated as failures'''
        raise NotImplemented()


    @staticmethod
    def run_check(**kwargs):
        '''Run check in exception wrapper'''
        try:
            result = self.check(**kwargs)
        except Exception as e:
            return {
                    "healthy" : False,
                    "error_message" : "{e.__class__.__name__}: {e}".format(e=e),
                }
        validate_result(result)
        return result


    async def loop(self,callback):
        """Callback at interval. Add to event loop as guarded task."""
        await asyncio.sleep(self.delay)

        while True:
            self.last_start = monotonic()
            callback(self.kwargs)
            await asyncio.sleep(self.interval)


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


    def add_entity(self,entity):
        if not isinstance(entity,Entity):
            raise ValueError('Instance of an Entity (subclass) required')

        self.entities.append(entity)
        self.entities_by_id[entity.id] = entity

        if entity.tab in self.entities_by_tab:
            self.entities_by_tab[entity.tab].append(entity)
        else:
            self.entities_by_tab[entity.tab] = [entity]


        for hcs in entity.healthchecks:
            self.healthchecks.append(hcs)
            self.healthcheck_by_worker[hcs.worker].append(hcs)
            self.healthcheck_by_id[hcs.id] = hcs


#    def instantiate_entity(name,description,tab,worker,healthchecks,**kwargs):
#        entity = ENTITY_CLASSES[cls](
#            name=name,
#            description=description,
#            tab=tab,
#            worker=worker,
#            **kwargs)
#
#        self.entities.append(entity)
#
#        if tab not in self.tabs:
#            self.tabs[tab] = list()
#
#        # add tabs and entities in order of definition!
#        self.tabs[tab].append(entity)



HEALTHCHECK_CLASSES= extract_classes(healthchecks,Healthcheck)
ENTITY_CLASSES = extract_classes(entities,Entity)
