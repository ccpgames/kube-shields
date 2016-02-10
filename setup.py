"""Kube shields flask frontend.

Can return redirects to shields.io for the health of your pods in kubernetes.

Will only checks pods which are automatically generated and not in the
kube-system namespace.

Extendable to allow more custom checks per pod, drop your checks into the
"snowflakes" folder. See example.py for further details.
"""


import io
import os
import re
from setuptools import setup
from setuptools import find_packages


def find_version(filename):
    """Uses re to pull out the assigned value to __version__ in filename."""

    with io.open(filename, "r", encoding="utf-8") as version_file:
        version_match = re.search(r'^__version__ = [\'"]([^\'"]*)[\'"]',
                                  version_file.read(), re.M)
    if version_match:
        return version_match.group(1)
    return "0.0-version-unknown"


if os.path.isfile("README.md"):
    with io.open("README.md", encoding="utf-8") as opendescr:
        long_description = opendescr.read()
else:
    long_description = __doc__


setup(
    name="kube_shields",
    version=find_version("kube_shields/__init__.py"),
    description="kube shields flask frontend.",
    author="Adam Talsma",
    author_email="se-adam.talsma@ccpgames.com",
    url="https://github.com/ccpgames/kube_shields/",
    download_url="https://github.com/ccpgames/kube_shields/",
    entry_points={"paste.app_factory": ["main = kube_shields.web:paste"]},
    install_requires=["Flask>=0.10.0", "requests>=2.9.0"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Flask",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: MIT License",
    ],
    extras_require={"deploy": ["paste", "PasteDeploy", "uwsgi"]},
    include_package_data=True,
    zip_safe=False,
    package_data={
        "kube_shields": [
            os.path.join("kube_shields", "templates", f) for f in
            os.listdir(os.path.join("kube_shields", "templates"))
        ],
    },
    packages=find_packages(),
    long_description=long_description,
)
