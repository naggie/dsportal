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
import manager

if len(sys.argv) < 2:
    print(__doc__ % sys.argv[0])
    sys.exit(1)


CONFIG = yaml.load(sys.argv[1])
CONFIG_DIR = path.realpath(sys.argv[1])
ASSET_DIR = path.join(CONFIG_DIR,'assets')
SCRIPT_DIR = path.dirname(path.realpath(__file__))
STATIC_DIR = path.join(SCRIPT_DIR,'static')
TEMPLATES_DIR = path.join(SCRIPT_DIR,'templates')

app = web.Application(debug=True)
app.router.add_static('/static',STATIC_DIR)
#app.router.add_static('/assets',ASSET_DIR)
#app.router.add_get('/',sso)


aiohttp_jinja2.setup(app,loader=jinja2.FileSystemLoader(TEMPLATES_DIR))

def main():
    web.run_app(
            app,
            port=int(8080),
            shutdown_timeout=6,
        )

