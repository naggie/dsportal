from collections import OrderedDict,defaultdict
import inspect
import entities
import healthchecks
import sleep

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
