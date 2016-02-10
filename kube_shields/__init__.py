"""Kube shields."""


import os
from flask import Flask
from flask.ext.cache import Cache


__author__ = "Adam Talsma"
__author_email__ = "se-adam.talsma@ccpgames.com"
__version__ = "0.0.1"


app = Flask(__name__)
cache = Cache(app, config={"CACHE_TYPE": "simple"})

SITE_NAME = os.environ.get("SHIELD_SITE_NAME", "shields")
OTHER_SHIELDS = os.environ.get("OTHER_SHIELDS", "")
OTHER_SHIELDS = OTHER_SHIELDS.split(" ") if OTHER_SHIELDS else False
with open(os.environ.get("INTRA_SHIELD_SECRET"), "r") as openkey:
    INTRA_SECRET = openkey.read().strip()
