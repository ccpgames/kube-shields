"""Kube shields."""


import os
from flask import Flask


__author__ = "Adam Talsma"
__author_email__ = "se-adam.talsma@ccpgames.com"
__version__ = "0.0.3"


app = Flask(__name__)

SITE_NAME = os.environ.get("SHIELD_SITE_NAME", "shields")
OTHER_SHIELDS = os.environ.get("OTHER_SHIELDS", "")
OTHER_SHIELDS = OTHER_SHIELDS.split(" ") if OTHER_SHIELDS else False
try:
    with open(os.environ.get("INTRA_SHIELD_SECRET"), "r") as openkey:
        INTRA_SECRET = openkey.read().strip()
except:
    INTRA_SECRET = "not secret"
