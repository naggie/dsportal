from uuid import uuid4
from time import time
from random import randint
from functools import wraps
from collections import OrderedDict,defaultdict
import inspect
import dsportal.entities
import dsportal.healthchecks
import sleep

HEALTHCHECKS = dict()

class Entity(object):
    def __init__(self,name,description,tab,worker):
        # Used for DOM ID as well
        self.id = str(uuid4())

        self.tab = tab

        # description of the real world thing this instance represents
        self.description = description

        # Aggregate of all health checks belonging to this entity
        # Unknown, yet
        self.healthy = None

        self.healthChecks = list()



def validate_result(result):
    if type(result) != dict:
        raise ValueError('Healthcheck result must be a dict')

    if 'healthy' not in result:
        raise ValueError('Heathcheck result must have `healthy` key: a bool or None.')

    if type(result['healthy']) != bool and result['healthy'] != None:
        raise ValueError('`healthy` key must be bool or None. None means unknown-yet or not-applicable.')

    if not result['healthy'] == False and not result['error_message']:
        raise ValueError('error_message must be set if healthy is False')


# TODO default and way for user to override label and for constructor to modify
class HealthCheck(object):
    label = "The name of this value"
    description = "What this health check does"

    interval = 60 # default, can be overridden in configuration

    def __init__(self,cls,interval=None,worker=None,**config):
        self.id = str(uuid4())

        self.worker = worker

        # kwargs to pass to check
        self.fn_kwargs = config

        # TODO WARN this is a class var not instance FIXME
        self.interval = interval or self.interval

        self.state = {
                "healthy": None,
                }

        # randomise for uniform distribution of health checks rather than
        # periodic stampedes
        # warm up over interval, max 1 min
        self.delay = randint(0,max(self.interval,60))


    def update(self,result):
        validate_result(result)
        self.state = result

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

ENTITY_CLASSES = dict()

for name, obj in inspect.getmembers(entities):
    if inspect.isclass(obj) and entities.Entity in inspect.getmro(obj):
        ENTITY_CLASSES[obj.__name__] = obj


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




class HealthCheckState(object):
    def __init__(self,fn_name,interval=None,**config):

        # validate fn_name
        if fn_name not in HEALTHCHECKS:
            raise KeyError('Given fn_name is not a known healthcheck')

        self.fn_name = fn_name
        self.fn = HEALTHCHECKS[fn_name]

        self.id = str(uuid4())

        # kwargs to pass to healthcheck
        self.fn_kwargs = config

        self.interval = interval or fn.interval

        self.state = {
                "healthy": None,
                }

        # randomise for uniform distribution of health checks rather than
        # periodic stampedes
        #self.last_attempt_time = 0
        t = int(time())
        # warm up over interval, max 1 min
        warmup = max(self.interval,60)
        self.last_attempt_time = randint(t-warmup,t)

    def update(self,state):
        self.state.update(state)

    # used by scheduler to decide when to put job on queue
    # TODO probably replace with async sleep loop and asyncio create_task (or gather? or ensure_future?)
    def must_run(self):
        t = time()
        if self.last_attempt_time + self.interval <= t:
            self.last_attempt_time = t
            return True
        else:
            return False
