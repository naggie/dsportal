from uuid import uuid4
from time import time
from random import randint
from functools import wraps

# hm....

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
def healthcheck(fn):
    '''Registers healthcheck, wraps exceptions and validates I/O. Result will
    be used to .update() the state dict to preserve object references and may
    be recorded in a time-series.'''

    if not fn.__doc__:
        raise ValueError('__doc__ describing purpose must be defined for healthcheck.')

    if not getattr(fn,'interval',None):
        fn.interval = 60

    HEALTHCHECKS[fn.__name__] = fn

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
            raise ValueError('Heathcheck result must have `healthy` key, a bool or None.')

        if type(result['healthy']) != bool and result['healthy'] != None:
            raise ValueError('''Heathcheck result must have `healthy` key, a
                    bool or None. None means unknown-yet or not-applicable.''')

        if not result['healthy'] and not result['error_message']:
            raise ValueError('error_message must be set if healthy is False')

    return _fn


# TODO just an idea atm.
class HealthCheckManager(object):
    def __init__(self,fn_name,interval=None,**config):

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
    def must_run(self):
        t = time()
        if self.last_attempt_time + self.interval <= t:
            self.last_attempt_time = t
            return True
        else:
            return False



def percent_bar(self,_min,_max,value):
    'Return a value, capped integer 0-100 to render a bar chart'
    val = (value-_min) / (_max-_min)
    val *= 100
    val = int(val)
    val = min(val,100)
    val = max(val,0)
    return val


