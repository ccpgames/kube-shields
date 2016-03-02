"""For checking health with the kubernetes API."""


from __future__ import division
from __future__ import unicode_literals

import os
import requests
from datetime import datetime

# standard location for gke containers
CACRT = str("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")


class KubeAPI(object):
    """Stores the automatically injected kube API token."""

    def __init__(self):
        self.base_url = KubeAPI._api_version()

    @staticmethod
    def _api_version():
        """Determines the available api version(s)."""

        if not hasattr(KubeAPI, "base_url"):
            port = int(os.environ.get("KUBERNETES_SERVICE_PORT", "443"))
            url = "http{}://kubernetes:{}/api/".format(
                "s" * int(port == 443),
                port,
            )

            res = requests.get(url, headers=KubeAPI.headers(), verify=CACRT)
            res.raise_for_status()
            KubeAPI.base_url = url + res.json()["versions"][0]

        return KubeAPI.base_url

    @staticmethod
    def headers():
        """Returns the default token content in a headers dict."""

        token_file = "/var/run/secrets/kubernetes.io/serviceaccount/token"

        if not hasattr(KubeAPI, "_token"):
            with open(token_file, "r") as opentoken:
                KubeAPI._token = opentoken.read().strip()
        return {
            "Authorization": "Bearer {}".format(KubeAPI._token)
        }

    def get(self, url=""):
        """Request a URL from the kube API, returns JSON loaded response."""

        res = requests.get(
            "{}/{}".format(self.base_url, url),
            headers=KubeAPI.headers(),
            verify=CACRT,
        )
        res.raise_for_status()
        return res.json()


def all_services():
    """Returns a list of all services (unique pod names) in our cluster."""

    api = KubeAPI()
    services = []
    for pod in api.get("pods")["items"]:
        if pod["metadata"]["namespace"] == "kube-system":
            continue
        try:
            services.append(pod["metadata"]["generateName"][:-1])
        except KeyError:
            pass
    return sorted(set(services))


def check_kube_health(service):
    """Checks the health of a service with the Kube API.

    Args:
        service: string service name to check

    Returns:
        dictionary with keys: ready, total, restarts, color
    """

    api = KubeAPI()
    ready = 0
    total = 0
    restarts = 0
    color = False
    for pod in api.get("pods")["items"]:
        try:
            pod_name = pod["metadata"]["generateName"][:-1]
        except KeyError:
            continue
        if pod_name == service:
            for container in pod["status"].get("containerStatuses", []):
                restarts += container["restartCount"]
                total += 1
                ready += int(container["ready"])

            pod_created = datetime.strptime(
                pod["metadata"]["creationTimestamp"],
                "%Y-%m-%dT%H:%M:%SZ",
            )
            days = max((datetime.utcnow() - pod_created).days, 1)

            if ready != total:
                color = "red"
            elif restarts / days > ((days / 2) / days):
                if not color:  # red takes priority
                    color = "yellow"

    return {
        "ready": ready,
        "total": total,
        "restarts": restarts,
        "color": color,
    }


def kube_health(service):
    """Checks the kube health of the service, returns a result dict."""

    res = check_kube_health(service)
    return {
        "label": "health",
        "status": "{}/{} ({} restart{})".format(
            res["ready"],
            res["total"],
            res["restarts"],
            "s" * int(res["restarts"] != 1),
        ),
        "color": res["color"] or ("green" if res["ready"] else "red"),
    }
