from collections import OrderedDict
import inspect
import entities
import healthchecks
import sleep
import queue

ENTITY_CLASSES = dict()
HEALTHCHECK_CLASSES = dict()

for name, obj in inspect.getmembers(entities):
    if inspect.isclass(obj) and entities.Entity in inspect.getmro(obj):
        ENTITY_CLASSES[obj.__name__] = obj

for name, obj in inspect.getmembers(healthchecks):
    if inspect.isclass(obj) and healthchecks.HealthCheck in inspect.getmro(obj):
        HEALTHCHECK_CLASSES[obj.__name__] = obj


class Scheduler(object):
    def __init__(self,worker='localhost'):
        # worker this scheduler is on
        # ignore tasks which don't match this worker
        self.worker = worker

        self.tabs = OrderedDict()
        self.entities = list()
        self.healthchecks = list()

        self.work_queue = queue.Queue(maxsize=10)


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


    def start_workers(self,count=4):
        for x in range(count):
            t = Thread()
            t = Thread(target=self._worker)
            t.daemon = True
            t.start()

        return t

    def start(self):
        # TODO this should be async and in aiohttp event loop
        for h in self.healthchecks:
            if h.must_run():
                try:
                    self.work_queue.add(h)
                except queue.Full:
                    # drop check
                    pass


    def _worker(self):
        while True:
            h = self.work_queue.get(block=True)
            h.run_check() # wraps exceptions
            self.work_queue.task_done()
