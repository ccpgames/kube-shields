# Kube-shields

Redirection service to shields.io for inside a Kubernetes cluster. Uses the
Kubernetes API with the service account token and ca.crt injected to
`/var/run/secrets/kubernetes.io/serviceaccount/` in the running container.


# Configuration

## `OTHER_SHIELDS`

Kube-shields can be run with public access or without. This is dictated by
whether or not the `OTHER_SHIELDS` environment variable is set. You can enable
public access to the all endpoints by setting this value to a DNS name or IP
address of another kube-shield in another cluster. If you only have one cluster
and you want it to have public access, set the value to "None". If a kube-shields
server does not have the `OTHER_SHIELDS` env var set, it will only communicate
to other kube-shields servers sharing the same secret key.

## `SHIELD_SITE_NAME`

The `SHIELD_SITE_NAME` is only used for the `/` route, and thus only required
if the `OTHER_SHIELDS` variable is also set. It will be displayed in the main
html as the page title, and used for the shields' hovertext.

## `INTRA_SECRET`

This must be set on all kube-shield servers. The default is to use part of the
python package itself, which is in no way secure. You should generate a file
to be used as your shared secret and update the `INTRA_SECRET` env var to it's
filepath. If your intra-shield traffic is captured unencrypted it is possible
given enough time to brute force your secret key. This can be mitigated by
using a lengthy key and/or rotating them regularly.


# Automatic Discovery

Any Kubernetes Pod running in the same cluster as the kube-shield service and
also created automatically via some other object such as a ReplicationController
or DaemonSet will be found and have a health check generated for it. The check
is relatively simple, only returning the number of ready containers vs total,
with any discrepancy resulting in a red result instead of green. It also checks
each pod to see if it has restarted more than once every other day. If so,
the result will be yellow.


# Custom Checks

Making a custom check should be simple. You can create a python file with the
name of the pod you would like to apply the check to. In that file, create all
the helper functions you need, but be sure to prefix them with a `_`. The
functions that don't begin with an underscore will be used as custom checks for
that pod. The return format can either be a raw value, or you can return a dict
with the keys `label`, `status`, and `color`.

Caveat: do not name a custom check named `health`, it will be inaccessible.


# API

## `/`

`/` is available only if `OTHER_SHIELDS` is set. `/` will return HTML with a
list of all the service and their checks in all the clusters. There is no
caching anywhere in kube-shields though, keep that in mind.

## `/_/<pod>/<check>/`

The `_` endpoint is for retrieving a specific pod and check's result shield.
The automatically generated check is available under the check name `health`.
Your custom checks are available under their function names.

## `/a/<name>/<check>/`

The `a` endpoint is used to aggregate similarly named pods, as long as they have
the check, into the same shield result. The name section is the leading part of
pod name. For instance, the endpoint `/a/foo/health/` can be used to combine
the output for the pods `foo-bar`, `foo-baz`, and `foo` into a single shield.

## `/services/`

Typically only used with intra-shield traffic, returns a JSON list of all
discovered services. Requires intra-shield authentication if `OTHER_SHIELDS`
is not set.

## `/services/<name>/`

Also typically only used in intra-shield communication, this returns a JSON
list of all checks available for the named service, or 404.
