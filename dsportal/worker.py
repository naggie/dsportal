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



class Worker(object):
    def __init__(self):
        self.work_queue =   queue.Queue(maxsize=10)
        self.result_queue = queue.Queue(maxsize=10)

    def start_workers(self,count=4):
        for x in range(count):
            t = Thread()
            t = Thread(target=self._worker)
            t.daemon = True
            t.start()

        return t

    def enqueue(self,id,fn_name,**kwargs):
        try:
            fn = base.HEALTHCHECKS[fn_name]
            self.work_queue.put((id,fn,kwargs))
        except queue.Full:
            # drop check
            pass


    def _worker(self):
        while True:
            id,fn,kwargs = self.work_queue.get(block=True)
            result = fn(**kwargs)
            self.work_queue.task_done()
            try:
                self.result_queue.put((id,result))
                print (result)
            except queue.Full:
                # drop check
                pass


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


    async with session.ws_connect(url) as ws:
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

# TODO reconnect forever


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
