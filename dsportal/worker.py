"""
Runs stateless healthchecks scheduled by a dsportal server.
Usage: %s <server address> <token>
"""
import sys
from os import path
import aiohttp
import asyncio
from dsportal.base import Worker
import queue
import logging
from dsportal.util import setup_logging


setup_logging(debug=True)
log = logging.getLogger(__name__)

async def websocket_client(loop,worker,host,key):
    url = path.join(host,'worker-websocket')
    session = aiohttp.ClientSession(
            loop=loop,
            headers={
                'Authorization':'Token ' + key,
                },
            )

    # check auth
    while True:
        try:
            async with session.get(url) as resp:
                if resp.status != 400: # upgrade to ws pls
                    log.error(await resp.text())
                    sys.exit(1)

            connection = session.ws_connect(
                    url=url,
                    autoping=True,
                    heartbeat=10,
                )

            log.info("Connected to server")

            async with connection as ws:
                task = loop.create_task(read_results(worker,ws))

                try:
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            cls,id,kwargs = msg.json()
                            worker.enqueue(cls,id,**kwargs)
                finally:
                    task.cancel()
        except aiohttp.client_exceptions.ClientConnectorError:
            log.error('No connection to server. Will retry in 10 seconds.')

        await asyncio.sleep(10)

# TODO reconnect forever
async def read_results(worker,ws):
    while True:
        try:
            while True:
                response = worker.result_queue.get_nowait()
                ws.send_json(response)
        except queue.Empty:
            pass
        except ItemExpired:
            pass

        # There's got to be a better way! (Spills milk everywhere)
        await asyncio.sleep(0.01)


def main():
    # run as executable, must be remote worker
    if len(sys.argv) < 3:
        print(__doc__ % sys.argv[0])
        sys.exit(1)

    host = sys.argv[1]
    key = sys.argv[2]

    worker = Worker()
    worker.start_workers()

    loop = asyncio.get_event_loop()
    client = websocket_client(loop,worker,host,key)
    loop.run_until_complete(client)
