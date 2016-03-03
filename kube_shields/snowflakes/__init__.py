"""This is where you can put service specific checks.

To make additional checks (beyond the basic/automatically provided ones),
create python files here, the names of which become the service name. The
name doesn't nessesarily have to line up with an actual service in kubernetes,
you can create meta or logical service checks here as well.

So each python file is a service, and in each file, and functions that are
wrapped with the `snowflake` helper function provided by kube_shields will
be detected and the function names themselves become the check name.

An example snowflake check for the route `/_/webapp/hits/`:

# webapp.py

from kube_shields import snowflake

def hits_since(*args, **kwargs):
    # do something
    return hits

@snowflake
def hits():
    hits_in_last_hour = hits_since(minutes=60)
    if hits_in_last_hour > 9000:
        return {"status": hits, "color": "green"}
    elif hits_in_last_hour > 1000:
        return {"status": hits, "color": "yellow"}
    else:
        return {"status": hits, "color": "red"}

# EOF

The shields.io badge created will use the function name for the label, or
left side, and the status key of the dict return for the right side. If the
color key is omitted, or the snowflake return is not a dict, orange is used.
You can override using the function name as a label by including a label key.
"""
