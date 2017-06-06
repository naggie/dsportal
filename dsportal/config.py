import yaml
from os import path
import sys

CONFIG_DIR = ASSET_DIR = SCRIPT_DIR = STATIC_DIR = TEMPLATES_DIR = None

if len(sys.argv) >= 2:
    with open(sys.argv[1]) as f:
        CONFIG = yaml.load(f.read())

    CONFIG_DIR = path.realpath(path.dirname(sys.argv[1]))
    # TODO ASSET_DIR yes or no? -- could just be local to yml file
    ASSET_DIR = path.join(CONFIG_DIR,'assets')
    SCRIPT_DIR = path.dirname(path.realpath(__file__))
    STATIC_DIR = path.join(SCRIPT_DIR,'static')
    TEMPLATES_DIR = path.join(SCRIPT_DIR,'templates')
