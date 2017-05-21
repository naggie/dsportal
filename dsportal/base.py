from uuid import uuid4
from time import time
from random import randint

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

# TODO -- __init__ is run on server not worker! Communicate that somehow.
# TODO alternative to overriding __init__? Initial state patch + kwargs copy to __dict__?
# or just allow __init__? Actually, it would prevent anything done in iinit
# for docs, I guess.
# TODO additional rules -- attributes must be immutable else they won't be synced

class HealthCheck(object):
    # seconds *between* tests. Timer starts after execution such that overruns
    # are impossible. Consider it a rest time.
    interval = 60

    # seconds to wait before reporting a stuck worker (process will need to be
    # restarted)
    timeout = 6

    def __init__(self):
        # used to record changes to attributes for DOM updates and object sync
        # call super __setattr__ so local doesn't trigger
        super(HealthCheck,self).__setattr__('_patch', dict())

        # Used for DOM ID as well
        self.id = str(uuid4())
        self.healthy = None
        self.error_message = None

        # randomise for uniform distribution of health checks rather than
        # periodic stampedes
        #self.last_attempt_time = 0
        t = int(time())
        # warm up over interval, max 1 min
        warmup = max(self.interval,60)
        self.last_attempt_time = randint(t-warmup,t)


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


    # used by scheduler to decide when to put job on queue
    def must_run(self):
        t = time()
        if self.last_attempt_time + self.interval <= t:
            self.last_attempt_time = t
            return True
        else:
            return False

    # TODO tentative --- init both ends instead?
    @classmethod
    def from_initial_patch(cls,patch):
        # bypass __init__
        instance = cls.__new__()
        instance.set_patch(patch)
        return instance

    def run_check(self):
        try:
            self.run()
            self.healthy = True
        except BaseException as e:
            e.error_message = str(e)
            self.healthy = False
            raise


    def check(self):
        """Run health check and updates metrics. Absolutely MUST NOT hang. If
        method runs without raising an exception, the state is assumed to be
        healthy, else unhealthy."""
        pass



class MetricCheck(HealthCheck):
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
        self.display_value = ''
        self.display_max = '100%'
        self.display_min = '0%'


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
