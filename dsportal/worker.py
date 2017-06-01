"""
Dsportal: a monitoring portal

Usage: %s <server address> <key>

"""
import sys
from os import path
import aiohttp
import asyncio
from threading import Thread
from dsportal import healthchecks
from dsportal import base
import queue
import logging
from dsportal.util import setup_logging
from dsportal.util import TTLQueue
from dsportal.util import ItemExpired
from dsportal.util import extract_classes
from dsportal.util import validate_request
from dsportal.base import HealthCheck



setup_logging(debug=False)
log = logging.getLogger(__name__)

class Worker(object):
    def __init__(self):
        # drop items if workers are too busy -- time not number of items
        self.work_queue = TTLQueue(maxsize=1000,ttl=5)
        # connection problems should not result in old results coming backk
        self.result_queue = TTLQueue(maxsize=1000,ttl=5)

        self.hclasses = extract_classes('dsportal.healthchecks',HealthCheck)

    def start_workers(self,count=4):
        for x in range(count):
            t = Thread()
            t = Thread(target=self._worker)
            t.daemon = True
            t.start()

        return t

    def enqueue(self,id,cls,**kwargs):
        fn = self.hclasses[cls].run_check
        self.work_queue.put_nowait((id,fn,kwargs))
        log.debug('Check enqueued: %s',cls)



    def _worker(self):
        while True:
            try:
                id,fn,kwargs = self.work_queue.get_wait()
            except ItemExpired as e:
                id,fn,kwargs = e.item
                self.result_queue.put_nowait({
                        'id':id,
                        'healthy': None,
                        'error_message' : 'Worker was too busy to run this health check in time',
                    })
                log.warn('Check dropped: %s',fn.__name__)
                continue

            log.debug('Processing check: %s',fn.__name__)
            result = fn(**kwargs)
            self.work_queue.task_done()

            if result['healthy']:
                log.info('Check passed: %s %s',fn.__name__,kwargs)
            elif result['healthy'] == False:
                log.warn('Check failed: %s %s %s',fn.__name__,kwargs,result['error_message'])
            else:
                log.warn('Check error: %s %s %',fn.__name__,kwargs,result['error_message'])

            # TODO when should id be annotated and by what?
            result['id'] = id
            self.result_queue.put_nowait(result)


    def drain(self):
        try:
            self.result_queue.get(block=False)
            self.result_queue.task_done()
        except queue.Empty:
            return



async def websocket_client(loop,worker,host,key):
    url = path.join(host,'worker-websocket')
    session = aiohttp.ClientSession(
            loop=loop,
            headers={
                'Authorization':'Token ' + key,
                },
            )

    connection = session.ws_connect(
            url=url,
            autoping=True,
            heartbeat=10,
        )


    async with connection as ws:
        # TODO consider this implementation
        # https://aiohttp.readthedocs.io/en/v2.1.0/faq.html#how-to-receive-an-incoming-events-from-different-sources-in-parallel

        task = loop.create_task(read_results(worker,ws))

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    jobspec = msg.json()
                    worker.enqueue(**jobspec)
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    print('error')
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print('closed')
                    break
        finally:
            task.cancel()

# TODO reconnect forever

async def read_results(worker,ws):
    while True:
        try:
            while True:
                result = worker.result_queue.get_nowait()
                ws.send_json(result)
        except queue.Empty:
            pass
        except ItemExpired:
            pass

        await asyncio.sleep(0.01)


def main():
    # run as executable, must be remote worker
    if len(sys.argv) < 2:
        print(__doc__ % sys.argv[0])
        sys.exit(1)

    host = sys.argv[1]
    key = sys.argv[2]

    worker = Worker()
    worker.start_workers()

    loop = asyncio.get_event_loop()
    client = websocket_client(loop,worker,host,key)
    loop.run_until_complete(client)
