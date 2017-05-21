"""
Dsportal: a monitoring portal

Usage: %s <server address> <key>

"""
import sys
from os import path
import aiohttp

if len(sys.argv) < 2:
    print(__doc__ % sys.argv[0])
    sys.exit(1)

HOST = argv[1]
KEY = argv[2]

session = aiohttp.ClientSession()
async with session.ws_connect('http://example.org/websocket') as ws:
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
