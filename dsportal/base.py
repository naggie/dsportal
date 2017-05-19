from __future__ import division # TODO just use py3
from uuid import uuid4

class Entity(object):
    ''' description of the real world thing this instance represents'''

    def __init__(self,name,description,tab,worker):
        # Used for DOM ID as well
        self.id = str(uuid4())

        self.tab = tab

        # description of the real world thing this instance represents
        self.description = description

        # Aggregate of all health checks belonging to this entity
        # Unknown, yet
        self.healthy = None

        self.health_checks = health_checks


        raise NotImplemented('Define this method to accept Entity-specific parameters and initialise.')


class HealthCheck(object):
    '''Description of what this health check does'''
    # seconds *between* tests. Timer starts after execution such that overruns
    # are impossible. Consider it a rest time.
    interval = 60

    # seconds to wait before reporting a stuck worker (process will need to be
    # restarted)
    timeout = 600

    def __init__(self):
        # used to record changes to attributes for DOM updates and object sync
        # call super __setattr__ so local doesn't trigger
        super(HealthCheck,self).__setattr__('_patch', dict())

        # Used for DOM ID as well
        self.id = str(uuid4())
        self.healthy = None
        self.error_message = None
        self.last_attempt_time = 0


    # TODO decide on returning a patch or calling a publish to the EventBus
    def run():
        """Run health check and updates metrics. Must return dictionary of new
        changed values. Absolutely MUST not hand forever. Implement a timeout
        that raises any exception."""
        return {}


    # TODO could automate this with get/setattr hooks
    # TODO make this enumerable to include some derived value methods? Or require overriding?


    # record patches for object sync and DOM updates
    def __setattr__(self, name, value):
        self._patch[name] = value
        super(HealthCheck,self).__setattr__(name, value)

    def get_patch(self):
        patch = self._patch
        super(HealthCheck,self).__setattr__('_patch', dict())
        return patch

    def set_patch(self,patch):
        for k,v in patch.items():
            if k not in self.__dict__:
                raise AttributeError('Patch contained unknown key')

            if k != self.__dict__[k]:
                super(HealthCheck,self).__setattr__(k,v)


class Metric(HealthCheck):
    description = "A generic health check with associated metric"
    # unit with no magnitude
    unit = '%'

    def __init__(self,*args,**kwargs):
        super(Metric,self).__init__(*args,**kwargs)
        # raw values have fixed magnitude
        self.raw_value = None
        self.raw_max = 100
        self.raw_min = 0

        # human values have dynamic magnitude and units attached
        self.human_value = ''
        self.human_max = '100%'
        self.human_min = '0%'


    def percent_bar(self):
        'Return a value, capped integer 0-100 to render a bar chart'
        val = (self.raw_value-self.raw_min) / (self.raw_max-self.raw_min)
        val *= 100
        val = int(val)
        val = min(val,100)
        val = max(val,0)
        return val


class DummyCheck(HealthCheck):
    description = 'A check with no health status and an arbitrary value. Used for information-only, eg uptime.'
    healthy = None
    def __init__(self,*args,**kwargs):
        super(Metric,self).__init__(*args,**kwargs)
        self.value = kwargs['value']
