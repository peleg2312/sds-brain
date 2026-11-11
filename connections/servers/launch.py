#!/usr/bin/env python3
"""What the plugin runs for storagegrid, ceph, oneview and ilo on a person's machine (brain-sds/tools/connect.py <name>):
the server over stdio when its Python packages and an inventory are here, else a one-tool server that says what is
missing. Most teams run these servers once on the VM or OpenShift instead (connections/servers/README.md) and point the
plugin at them with connections/http/use.py."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(os.path.dirname(HERE)), "brain-sds", "tools")]
name = sys.argv[1] if len(sys.argv) > 1 else ""
problem = ""
try:
    import mcp  # noqa: F401
    if name == "oneview":
        import hpeOneView  # noqa: F401
    if name == "ilo":
        import redfish  # noqa: F401
except ImportError as e:
    problem = (f"The {name} server needs its Python packages ({e.name} is missing). Either run it once for the team on the "
               "VM or OpenShift (connections/servers/README.md) and point the plugin at it with connections/http/use.py, or "
               "install them here: pip install -r ~/.claude/sds-brain/connections/servers/requirements.txt")
if not problem:
    from sds_mcp import common
    if not common.targets(name if name != "ilo" else "ilo"):
        problem = (f"No {name} systems in the inventory {common.config_path()}: copy connections/servers/targets.example.json to "
                   "targets.json and fill in your systems (no secrets; credentials go in environment variables).")
if problem:
    import stub_mcp
    sys.exit(stub_mcp.serve(name, f"{name}_setup", f"The {name} server is not set up here: call this to see what is missing.", problem))
from sds_mcp.__main__ import main  # noqa: E402
sys.argv = ["sds_mcp", name] + sys.argv[2:]
sys.exit(main() or 0)
