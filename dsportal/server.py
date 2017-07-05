"""
Dsportal: a monitoring portal

Usage: %s <config.yml>

Dsportal server listens on port 8080. Use a reverse proxy to provide HTTPS
termination.
"""
from dsportal.config import USER_CONFIG
from dsportal.config import ASSET_DIR
from dsportal.config import STATIC_DIR
from dsportal.config import TEMPLATES_DIR
import asyncio
import aiohttp
import sys
import jinja2
import aiohttp_jinja2
import logging
from dsportal.util import setup_logging,human_seconds
from dsportal import base

setup_logging(debug=False)
log = logging.getLogger(__name__)

async def worker_websocket(request):
    if "Authorization" not in request.headers:
        return aiohttp.web.Response(text="Authorization Token required",status=403)

    token = request.headers["Authorization"][6:]
    workers = {v: k for k, v in USER_CONFIG['workers'].items()}
    index = request.app['index']

    try:
        worker = workers[token]
    except KeyError:
        return aiohttp.web.Response(text="Incorrect token",status=403)

    if worker in index.worker_websockets:
        return aiohttp.web.Response(text="Worker %s already connected" % worker,status=403)

    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)

    try:
        index.worker_websockets[worker] = ws

        log.info('worker %s connected',worker)

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                id,result = msg.json()
                index.dispatch_result(id,result)
    finally:
        del index.worker_websockets[worker]

    return ws


@aiohttp_jinja2.template('tab.html')
async def tab_handler(request):
    index = request.app['index']
    tab = request.match_info.get('tab',index.entities[0].tab)

    healthchecks = []
    entities = []

    if tab in index.entities_by_tab:
        entities = index.entities_by_tab[tab]
    elif tab == "healthchecks":
        healthchecks = index.unhealthy_healthchecks + index.unknown_healthchecks + index.healthy_healthchecks
    else:
        # TODO replace with exception and special 403 middleware
        return aiohttp.web.Response(text="Unregistered tab",status=403)


    return {
        "tab":tab,
        "tabs": list(index.entities_by_tab.keys()),
        "entities": entities,
        "name": USER_CONFIG.get('name'),
        "css": USER_CONFIG.get('css'),
        "header": USER_CONFIG.get('header',''),
        "footer": USER_CONFIG.get('footer',''),
        "num_healthy": len(index.healthy_healthchecks),
        "num_unhealthy": len(index.unhealthy_healthchecks),
        "num_unknown": len(index.unknown_healthchecks),
        "healthchecks": healthchecks,
            }



def main():
    if len(sys.argv) < 2:
        print(__doc__ % sys.argv[0])
        sys.exit(1)

    app = aiohttp.web.Application()
    app.router.add_static('/static',STATIC_DIR) # TODO nginx static overlay
    app.router.add_static('/assets',ASSET_DIR)
    app.router.add_get('/worker-websocket',worker_websocket)
    #app.router.add_get('/client-websocket',sso)
    app.router.add_get('/',tab_handler)
    app.router.add_get('/{tab}',tab_handler)

    # kwargs are passed to jinja2.Environment constructor
    aiohttp_jinja2.setup(
            app,
            loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
            filters={
                'human_seconds':human_seconds,
                }
            )

    index = app['index'] = base.Index(USER_CONFIG['name'])

    for e in USER_CONFIG['entities']:
        index.instantiate_entity(**e)

    if 'alerters' in USER_CONFIG:
        for a in USER_CONFIG['alerters']:
            index.instantiate_alerter(**a)

    loop = asyncio.get_event_loop()
    index.register_tasks(loop)

    aiohttp.web.run_app(
            app,
            port=USER_CONFIG.get('port',8080),
            host=USER_CONFIG.get('host','127.0.0.1'),
            shutdown_timeout=6,
            access_log=None,
            loop=loop,
        )

