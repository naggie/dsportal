"""
Dsportal: a monitoring portal

Usage: %s <config.yml>

Dsportal server listens on port 8080. Use a reverse proxy to provide HTTPS
termination.
"""
import asyncio
import aiohttp
import sys
from os import path
import jinja2
import aiohttp_jinja2
import yaml
import logging
from dsportal.util import setup_logging
from dsportal import base

setup_logging()
log = logging.getLogger(__name__)


if len(sys.argv) < 2:
    print(__doc__ % sys.argv[0])
    sys.exit(1)


with open(sys.argv[1]) as f:
    CONFIG = yaml.load(f.read())

CONFIG_DIR = path.realpath(sys.argv[1])
ASSET_DIR = path.join(CONFIG_DIR,'assets')
SCRIPT_DIR = path.dirname(path.realpath(__file__))
STATIC_DIR = path.join(SCRIPT_DIR,'static')
TEMPLATES_DIR = path.join(SCRIPT_DIR,'templates')


async def worker_websocket(request):

    if "Authorization" not in request.headers:
        return aiohttp.web.Response(text="Authorization Token required",status=403)

    token = request.headers["Authorization"][6:]

    workers = {v: k for k, v in CONFIG['workers'].items()}

    try:
        worker = workers[token]
    except KeyError:
        return aiohttp.web.Response(text="Incorrect token",status=403)

    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)

    #ws.send_json(('CpuUsage','foobar',{}))


    h = request.app['index'].healthchecks[0]
    h = request.app['index'].healthchecks[1]
    h = request.app['index'].healthchecks[2]
    h = request.app['index'].healthchecks[3]
    ws.send_json((h.cls,h.id,h.check_kwargs))


    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            id,result = msg.json()
            request.app['index'].healthcheck_by_id[id].update(result)

#        elif msg.type == aiohttp.WSMsgType.ERROR:
#            print('ws connection closed with exception %s' %
#                    ws.exception())

    print('websocket connection closed')

    return ws



app = aiohttp.web.Application(debug=True)
app.router.add_static('/static',STATIC_DIR) # TODO nginx static overlay
#app.router.add_static('/assets',ASSET_DIR)
#app.router.add_get('/',sso)
app.router.add_get('/worker-websocket',worker_websocket)
#app.router.add_get('/client-websocket',sso)
aiohttp_jinja2.setup(app,loader=jinja2.FileSystemLoader(TEMPLATES_DIR))

# Make scheduler available to request handlers
# See https://aiohttp.readthedocs.io/en/stable/web.html#data-sharing-aka-no-singletons-please
# directly in request dict-like onject!
#app['scheduler'] = TODO


def main():
    app['index'] = base.Index()

    for e in CONFIG['entities']:
        app['index'].instantiate_entity(**e)

    aiohttp.web.run_app(
            app,
            port=int(8080),
            shutdown_timeout=6,
        )

