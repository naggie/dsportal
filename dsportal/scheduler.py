from collections import OrderedDict
import inspect
import entities
import healthchecks
import sleep

ENTITY_CLASSES = dict()

for name, obj in inspect.getmembers(entities):
    if inspect.isclass(obj) and entities.Entity in inspect.getmro(obj):
        ENTITY_CLASSES[obj.__name__] = obj


class Scheduler(object):
    def __init__(self,worker='localhost'):
        # worker this scheduler is on
        # ignore tasks which don't match this worker
        self.worker = worker

        self.tabs = OrderedDict()
        self.entities = list()
        self.healthchecks = list()



    def instantiate_entity(name,description,tab,worker,healthchecks,**kwargs):
        entity = ENTITY_CLASSES[cls](
            name=name,
            description=description,
            tab=tab,
            worker=worker,
            **kwargs)

        self.entities.append(entity)

        if tab not in self.tabs:
            self.tabs[tab] = list()

        # add tabs and entities in order of definition!
        self.tabs[tab].append(entity)


        for h in healthchecks:
            instance = HEALTHCHECK_CLASSES[h](**kwargs)
            # used to deserialise on worker
            initial_patch = instance.get_patch()

            self.healthchecks.append(instance)

