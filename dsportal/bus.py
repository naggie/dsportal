# just a dummy, can/should be replaced with websocket pubsub system
from collections import defaultdict


class StateChangeEventBus(object):
    """
        Stores mutable dict under ID, objects are built and updated from patches.
        The events are to be consumed by:

            1. The websocket-based javascript update client
            2. The main server for tracking state changes by workers running
               remote checks

        The idea is that the server renders everything from a template, and the
        client just patches the DOM directly to keep it in sync with the server
        state.

        The client can infer how to patch the DOM element representing the
        particular class of health check by inspecting the element class, which
        should list the server-side class. Therefore, on the wire the only
        information needed is the DOM ID which is the same as the Entity or
        HealthCheck ID.
    """
    def __init__(self):
        self.state = defaultdict(dict)

    def patch(self,id,patch):
        for k,v in patch.items():
            if self.state[id][k] == v:
                del patch[k]

        self.state[id].update(patch)
        self.broadcast(id,patch)

    def enumerate_state(self):
        # return a list of state patches to do an initial state sync
        return self.state.items()



