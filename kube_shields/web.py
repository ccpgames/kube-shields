"""Web routes for shields."""


import os
import sys
import json
import random
import requests
import traceback
from flask import abort
from flask import request
from flask import redirect
from flask import Response
from flask import render_template
from hashlib import md5
from datetime import datetime
from datetime import timedelta
from importlib import import_module

from kube_shields import app
from kube_shields import cache
from kube_shields import SITE_NAME
from kube_shields import INTRA_SECRET
from kube_shields import OTHER_SHIELDS
from kube_shields.kubernetes import all_services
from kube_shields.kubernetes import kube_health


def as_redirect_url(label="label", status="status", color="red"):
    """All status checks should be returning these arguments.

    Returns a string url to img.shields.io suitable for the check result.
    """

    def _clean(name):
        """Uses shields.io url formatting spec."""
        return requests.utils.quote(
            name.replace("_", "__").replace("-", "--").replace(" ", "_")
        ).replace("/", "%2f")

    return "https://img.shields.io/badge/{}-{}-{}.svg".format(
        _clean(label),
        _clean(status),
        color,
    )


def as_json(data):
    """flask.jsonify can't do lists for reasons~."""

    return Response(
        json.dumps(data),
        status=200,
        content_type="application/json",
    )


def intra_shield(verify=None):
    """For intra-shield server communication.

    Args:
        verify: boolean, if True, will verify the headers or abort(403)

    Returns:
        if verify is None, returns the Intra-shield headers
    """

    def _gen_md5(phrase, timestamp):
        """Returns a md5 hash with the phrase and the shared secret."""

        _md5 = md5()
        _md5.update(phrase)
        _md5.update(INTRA_SECRET)
        _md5.update(timestamp)
        return _md5.hexdigest()

    time_fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
    if verify:
        header = request.headers.get("Intra-Shield")
        if header:
            phrase, timestamp, md5_hash = header.split(" ")
            if _gen_md5(phrase, timestamp) != md5_hash or (
                datetime.utcnow() - datetime.strptime(timestamp, time_fmt)
            ) > timedelta(seconds=1):
                abort(403)
        else:
            abort(403)
    else:
        letters = [chr(x) for x in range(65, 91)] + \
                  [chr(x) for x in range(97, 123)]
        phrase = "".join([random.choice(letters) for _ in range(20)])
        timestamp = datetime.utcnow().strftime(time_fmt)
        return {
            "Intra-Shield": "{} {} {}".format(
                phrase,
                timestamp,
                _gen_md5(phrase, timestamp),
            ),
        }


@cache.cached(timeout=60)
def all_other_services():
    """Determines all other services and checks in all other clusters.

    Returns: dictionary of {shield_server: {service: [checks]}}
    """

    services = {}
    for shield in OTHER_SHIELDS:
        res = requests.get(
            "https://{}/services/".format(shield),
            headers=intra_shield(),
        )
        try:
            res.raise_for_status()
        except:
            continue
        services[shield] = {}
        for srv in res.json():
            res = requests.get(
                "https://{}/services/{}/".format(shield, srv),
                headers=intra_shield(),
            )
            try:
                res.raise_for_status()
            except:
                continue
            services[shield][srv] = res.json()

    return services


def do_check(service, check):
    """Runs the check for the service. Returns a result dictionary."""

    if check == "health":
        result = kube_health(service)
    else:
        try:
            check_func = getattr(
                import_module("kube_config.snowflakes.{}".format(service)),
                check,
            )
        except (ImportError, AttributeError):
            abort(404)
        else:
            result = check_func()
            if not isinstance(result, dict):
                # the checks should return a dict, this is just a failsafe
                result = {"label": check, "status": result, "color": "orange"}

    return result


def check_to_redirect(service, check):
    """Uses do_check and as_redirect_url to get a redirect url for a check."""

    return as_redirect_url(**do_check(service, check))


@app.route("/_/<service>/<check>/", methods=["GET"])
def service_status(service, check):
    """Checks the status of the check for the service.

    If this is the master server, the check result will be retrived from the
    kube_shield server in the service's cluster (if the service is not local).
    """

    if not OTHER_SHIELDS:
        intra_shield(verify=True)

    if service in all_services():
        return redirect(check_to_redirect(service, check), code=302)

    elif OTHER_SHIELDS:
        # Get the result from the other service
        for server, services in all_other_services().items():
            for _service, _ in services.items():
                if service == _service:
                    res = requests.get(
                        "https://{}/_/{}/{}/".format(server, service, check),
                        headers=intra_shield(),
                    )
                    try:
                        res.raise_for_status()
                    except requests.HTTPError as error:
                        abort(error.code)
                    else:
                        return redirect(res.url, code=302)

        abort(404)


def services_checks(service):
    """Determine the list of checks for a service."""

    checks = ["health"]

    try:
        mod = import_module("kube_config.snowflakes.{}".format(service))
    except ImportError:
        pass
    else:
        checks.extend([f for f in dir(mod) if not f.startswith("_")])

    return checks


@app.route("/services/<service>/", methods=["GET"])
@cache.cached(timeout=30)
def get_services_checks(service):
    """Returns a list of checks available for the service."""

    intra_shield(verify=True)

    if service in all_services():
        return as_json(services_checks(service))
    else:
        abort(404)


@app.route("/services/", methods=["GET"])
@cache.cached(timeout=30)
def get_services():
    """Returns a list of all known services in our cluster."""

    intra_shield(verify=True)

    return as_json(all_services())


@app.route("/")
@cache.cached(timeout=10)
def get_all_statuses():
    """Main page, lists all services/clusters if master server."""

    if OTHER_SHIELDS:
        all_statuses = {"local": {}}
        # first do our own services
        for service in all_services():
            all_statuses["local"][service] = {}
            for check in services_checks(service):
                all_statuses["local"][service][check] = check_to_redirect(
                    service, check
                )

        # then all other services
        for server, services in all_other_services().items():
            all_statuses[server] = {}
            for service, checks in services.items():
                all_statuses[server][service] = {}
                for check in checks:
                    res = requests.get(
                        "https://{}/_/{}/{}/".format(server, service, check),
                        headers=intra_shield(),
                    )
                    try:
                        res.raise_for_status()
                    except:
                        continue
                    else:
                        all_statuses[server][service][check] = res.url

        return render_template(
            "index.html",
            all_statuses=all_statuses,
            site_name=SITE_NAME,
        )
    else:
        abort(404)


def traceback_formatter(excpt, value, tback):
    """Catches all exceptions and re-formats the traceback raised."""

    sys.stdout.write("".join(traceback.format_exception(excpt, value, tback)))


def hook_exceptions():
    """Hooks into the sys module to set our formatter."""

    if hasattr(sys.stdout, "fileno"):  # when testing, sys.stdout is StringIO
        # reopen stdout in non buffered mode
        sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
        # set the hook
        sys.excepthook = traceback_formatter


def paste(*_, **settings):
    """For paste, start and return the Flask app."""

    hook_exceptions()
    return app


def main():
    """Debug/cmdline entry point."""

    paste().run(
        host="0.0.0.0",
        port=8080,
        debug=True,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
