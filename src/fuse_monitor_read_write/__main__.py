#!/usr/bin/python3

import sys
import os

import fuse
from fuse_monitor_read_write.fuse import *


def main() -> None:

    server = MonitorReadWrite(
        version="%prog " + fuse.__version__,
        usage=fuse.Fuse.fusage,
        dash_s_do="setsingle",
    )

    server.parse(values=server, errex=1)

    try:
        if server.fuse_args.mount_expected():
            os.chdir(server.fuse_args.mountpoint)
            # This trick with savefd allows mounting over an existing dir
            # (compared to having to create a new directory only for the
            # mountpoint). It is taken from
            # https://github.com/rflament/loggedfs/blob/82aba9a93489797026ad1a37b637823ece4a7093/src/loggedfs.cpp#L953
            server.savedrootfd = os.open(".", 0)
    except OSError:
        print("Can't enter root of underlying filesystem", file=sys.stderr)
        sys.exit(1)

    server.main()


if __name__ == "__main__":
    main()
