"""
Grab WebApp screenshots if they don't already exist.

Usage: %s <dsportal.yml>

"""

from dsportal.config import USER_CONFIG
from dsportal.config import ASSET_DIR
from dsportal.entities import WebApp
import sys
from dsportal.util import setup_logging

setup_logging()


def main():
    if len(sys.argv) < 2:
        print(__doc__ % sys.argv[0])
        sys.exit(1)

    for e in USER_CONFIG["entities"]:
        if e["cls"] == "WebApp":
            del e["cls"]
            webApp = WebApp(**e)

            if not webApp.screenshot_exists:
                webApp.take_screenshot()
