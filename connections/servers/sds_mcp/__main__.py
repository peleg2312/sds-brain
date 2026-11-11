"""python -m sds_mcp <storagegrid|ceph|oneview|ilo> [--http HOST:PORT]   (stdio without --http)"""
import importlib
import sys

from . import SERVERS
from . import common


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in SERVERS:
        sys.exit(f"usage: python -m sds_mcp <{'|'.join(SERVERS)}> [--http HOST:PORT]")
    mod = importlib.import_module(f"sds_mcp.{sys.argv[1]}")
    return common.run(mod.server, sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main() or 0)
