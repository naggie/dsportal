from aiohttp import web
import sys
from os import path

CONF_DIR = path.realpath(sys.argv[1])
ASSET_DIR = join(CONF_DIR,'assets')
SCRIPT_DIR = path.dirname(path.realpath(__file__))
STATIC_DIR = join(SCRIPT_DIR,'static')
TEMPLATES_DIR = join(SCRIPT_DIR,'templates')

app = web.Application(debug=True)
app.router.add_static('/static',SCRIPT_DIR)
app.router.add_static('/assets',ASSET_DIR)
app.router.add_get('/',sso)
web.run_app(
        app,
        port=int(PORT),
        host='127.0.0.1',
        shutdown_timeout=6,
    )

