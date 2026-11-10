#!/usr/bin/env python3
"""Start one of the team's connections for the plugin's .mcp.json: `connect.py grafana` runs
connections/grafana/launch.py in the team repository (the launchers, the bundled Grafana server and each machine's
local configuration live there, not in the plugin). No team repository on this machine yet, or no such connection:
a one-tool server that says what is missing, instead of a failed server at every session start."""
import os
import re
import runpy
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brainlib as b  # noqa: E402
import stub_mcp  # noqa: E402

name = sys.argv[1] if len(sys.argv) > 1 and re.fullmatch(r"[a-z0-9-]+", sys.argv[1]) else ""
launch = os.path.join(b.BASE, "connections", name, "launch.py")
if not name or not os.path.isfile(launch):
    why = b.SETUP if not b.ROOT else f"connections/{name}/launch.py is missing in the team repository ({b.ROOT})."
    sys.exit(stub_mcp.serve(name or "connection", (name or "connection").replace("-", "_") + "_setup",
                            f"{name or 'This connection'} is not connected: call this to see what is missing.", why))
sys.argv = [launch] + sys.argv[2:]
runpy.run_path(launch, run_name="__main__")
