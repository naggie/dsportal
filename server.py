from aiohttp import web
import sys

app = web.Application(debug=True)
app.router.add_get('/',sso)
web.run_app(
        app,
        port=int(PORT),
        host='127.0.0.1',
        shutdown_timeout=6,
    )
