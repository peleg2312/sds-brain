#!/usr/bin/env python3
"""Start the Objectify adapter (server.py) with this machine's configuration: config.local.json when it exists (never
committed), else config.example.json, which exposes only the objectify_status tool and contacts nothing."""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
local = os.path.join(HERE, "config.local.json")
sys.argv = [os.path.join(HERE, "server.py"), "--config", local if os.path.isfile(local) else os.path.join(HERE, "config.example.json")] + sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
