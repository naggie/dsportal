"""
Dsportal: a monitoring portal

Usage: %s <config.yml>

Dsportal server listens on port 8080. Use a reverse proxy to provide HTTPS
termination.
"""
from aiohttp import web
import sys
from os import path
import jinja2
import aiohttp_jinja2
import yaml

if len(sys.argv) < 2:
    print(__doc__ % sys.argv[0])
    sys.exit(1)


CONFIG = yaml.load(sys.argv[1])
CONFIG_DIR = path.realpath(sys.argv[1])
ASSET_DIR = path.join(CONFIG_DIR,'assets')
SCRIPT_DIR = path.dirname(path.realpath(__file__))
STATIC_DIR = path.join(SCRIPT_DIR,'static')
TEMPLATES_DIR = path.join(SCRIPT_DIR,'templates')


async def worker_websocket(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
            else:
                ws.send_str(msg.data + '/answer')
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' %
                    ws.exception())

            print('websocket connection closed')

    return ws



app = web.Application(debug=True)
app.router.add_static('/static',STATIC_DIR) # TODO nginx static overlay
#app.router.add_static('/assets',ASSET_DIR)
#app.router.add_get('/',sso)
app.router.add_get('/worker-websocket',worker_websocket)
#app.router.add_get('/client-websocket',sso)
aiohttp_jinja2.setup(app,loader=jinja2.FileSystemLoader(TEMPLATES_DIR))

def main():
    web.run_app(
            app,
            port=int(8080),
            shutdown_timeout=6,
        )

