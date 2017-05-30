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

        raise NotImplemented('Define this method to accept Entity-specific parameters and initialise.')

    def add_healthcheck(self,instance):
        if not isinstance(instance,HealthCheck):
            raise ValueError('Instance or HealthCheck required')

        self.HealthChecks.append(instance)


# TODO strict classification? requiring certain attrs for bar min/max etc? (OOB class?)
def healthcheckfn(fn):
    '''Registers healthcheck, wraps exceptions and validates I/O. Result will
    be used to .update() the state dict to preserve object references and may
    be recorded in a time-series.'''

    if not fn.__doc__:
        raise ValueError('__doc__ describing purpose must be defined for healthcheck.')

    if not getattr(fn,'interval',None):
        fn.interval = 60


    @wraps(fn) # preserve __doc__ among other things
    def _fn(**kwargs):

        try:
            result = fn(**kwargs)
        except Exception as e:
            return {
                    "healthy" : False,
                    "error_message" : "{e.__class__.__name__}: {e}".format(e=e),
                }

        if type(result) != dict:
            raise ValueError('Healthcheck result must be a dict')

        if 'healthy' not in result:
            raise ValueError('Heathcheck result must have `healthy` key: a bool or None.')

        if type(result['healthy']) != bool and result['healthy'] != None:
            raise ValueError('`healthy` key must be bool or None. None means unknown-yet or not-applicable.')

        if not result['healthy'] == False and not result['error_message']:
            raise ValueError('error_message must be set if healthy is False')

        return result

    HEALTHCHECKS[fn.__name__] = _fn

    return _fn


# effectively wraps a healthcheckfn recording state
class HealthCheck(object):
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

        self.healthcheck_states = list()
        self.healthcheck_state_by_worker = defaultdict(list)
        self.healthcheck_state_by_id = dict()


    def add_entity(self,entity):
        if not isinstance(entity,Entity):
            raise ValueError('Instance of an Entity (subclass) required')

        self.entities.append(entity)
        self.entities_by_id[entity.id] = entity

        if entity.tab in self.entities_by_tab:
            self.entities_by_tab[entity.tab].append(entity)
        else:
            self.entities_by_tab[entity.tab] = [entity]


        for hcs in entity.healthcheck_states:
            self.healthcheck_states.append(hcs)
            self.healthcheck_state_by_worker[hcs.worker].append(hcs)
            self.healthcheck_state_by_id[hcs.id] = hcs


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
