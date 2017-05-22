"""
Dsportal: a monitoring portal

Usage: %s <server address> <key>

"""
import sys
from os import path
import aiohttp
from thread import Thread
import healthchecks
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
            fn = healthchecks.base.HEALTHCHECKS[fn_name]
            self.work_queue.add((id,fn,kwargs))
        except queue.Full:
            # drop check
            pass


    def _worker(self):
        while True:
            id,fn,kwargs = self.work_queue.get(block=True)
            result = fn(**kwargs)
            self.work_queue.task_done()
            try:
                self.result_queue.add((id,result))
            except queue.Full:
                # drop check
                pass




def main():
    # run as executable, must be remote worker
    if len(sys.argv) < 2:
        print(__doc__ % sys.argv[0])
        sys.exit(1)
    HOST = argv[1]
    KEY = argv[2]

    session = aiohttp.ClientSession()
    async with session.ws_connect(HOST) as ws:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close cmd':
                    await ws.close()
                    break
                else:
                    ws.send_str(msg.data + '/answer')
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break

