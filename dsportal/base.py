from __future__ import division # TODO just use py3

class Entity(object):
    version = 0

    def __init__(self,id,description):
        # Aggregate of all health checks
        self.healthy = None
        self.id = id

        # description of the real world thing this Entity represents
        self.description = ""


class HealthCheck(ouject):
    version = 0
    # description of what this health check does
    description = "A generic health check"

    # seconds *between* tests. Timer starts after execution such that overruns
    # are impossible. Consider it a rest time.
    interval = 60

    # seconds to wait before reporting a stuck worker (process will need to be
    # restarted)
    timeout = 600

    def __init__(self,
            id,
            on_health_change = lambda x: None,
            ):
        self.healthy = None
        self.id = id
        self.error_message = None

    # TODO decide on returning a patch or calling a publish to the EventBus
    def run():
        """Run health check and updates metrics. Must return dictionary of new
        changed values. Absolutely MUST not hand forever. Implement a timeout
        that raises any exception."""
        return {}

    def update(diff):
        """Update state from output of run(). Used to synchronise a remote
        instance. Must all self.on_health_change if state changes"""
        return False

    # TODO could automate this with get/setattr hooks
    # TODO make this enumerable to include some derived value methods? Or require overriding?
    def _patch(self,patch):
        self.eventBus.patch(self.id,value)


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
