from uuid import uuid4
from time import time
from random import randint
from functools import wraps

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


# TODO strict templating, requiring certain attrs for bar min/max etc? (OOB class?)
def healthcheck(fn):
    '''Registers healthcheck, wraps exceptions and validates I/O'''

    if not f.__doc__:
        raise ValueError('__doc__ describing purpose must be defined for healthcheck.')

    if not f.interval:
        f.interval = 60

    @wraps(fn) # preserve __doc__ among other things
    def _fn(**kwargs):

        try:
            result = fn(**kwargs)
        except Exception as e:
            return {
                    "healthy" : False,
                    "message" : "{e.__class__.__name__}: {e}".format(e=e),
                }

        if type(result) != dict:
            raise ValueError('Healthcheck result must be a dict')

        if 'healthy' not in result:
            raise ValueError('Heathcheck result must have `healthy` key, a bool or None.')

        if type(result['healthy']) != bool and result['healthy'] != None:
            raise ValueError('Heathcheck result must have `healthy` key, a bool or None. None means unknown-yet or not-applicable.')

    return _fn




def percent_bar(self,_min,_max,value):
    'Return a value, capped integer 0-100 to render a bar chart'
    val = (value-_min) / (_max-_min)
    val *= 100
    val = int(val)
    val = min(val,100)
    val = max(val,0)
    return val


