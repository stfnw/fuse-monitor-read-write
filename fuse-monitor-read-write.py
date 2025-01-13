#!/usr/bin/python3

################################################################################
# The original pass-through template code is taken from
# https://github.com/libfuse/python-fuse/blob/c4169e5e864bfb1eec342fe6dd0427959eeeaa38/example/xmp.py
# which is licensed under GNU LGPL. The original copyright notice is reproduced here:
################################################################################
#    Copyright (C) 2001  Jeff Epler  <jepler@gmail.com>
#    Copyright (C) 2006  Csaba Henk  <csaba.henk@creo.hu>
#
#    This program can be distributed under the terms of the GNU LGPL.
#    See the file COPYING.
################################################################################
# Therefore, this project as a whole is licensed under GNU LGPL as well.
################################################################################

import os, sys
from errno import *
from stat import *
import fcntl

import fuse
from fuse import Fuse


fuse.fuse_python_api = (0, 2)
fuse.feature_assert("stateful_files", "has_init")


def flag2mode(flags):
    md = {os.O_RDONLY: "rb", os.O_WRONLY: "wb", os.O_RDWR: "wb+"}
    m = md[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]

    if flags | os.O_APPEND:
        m = m.replace("w", "a", 1)

    return m


class MonitorReadWrite(Fuse):

    def __init__(self, *args, **kw):
        Fuse.__init__(self, *args, **kw)
        # Options taken from https://github.com/rflament/loggedfs/blob/82aba9a93489797026ad1a37b637823ece4a7093/src/loggedfs.cpp#L771C1-L771C104
        self.fuse_args.add("nonempty")
        self.fuse_args.add("use_ino")
        self.fuse_args.add("atomic_o_trunc")

    def getattr(self, path):
        return os.lstat("." + path)

    def readlink(self, path):
        return os.readlink("." + path)

    def readdir(self, path, offset):
        for e in os.listdir("." + path):
            yield fuse.Direntry(e)

    def unlink(self, path):
        os.unlink("." + path)

    def rmdir(self, path):
        os.rmdir("." + path)

    def symlink(self, path, path1):
        os.symlink(path, "." + path1)

    def rename(self, path, path1):
        os.rename("." + path, "." + path1)

    def link(self, path, path1):
        os.link("." + path, "." + path1)

    def chmod(self, path, mode):
        os.chmod("." + path, mode)

    def chown(self, path, user, group):
        os.chown("." + path, user, group)

    def truncate(self, path, len):
        f = open("." + path, "a")
        f.truncate(len)
        f.close()

    def mknod(self, path, mode, dev):
        os.mknod("." + path, mode, dev)

    def mkdir(self, path, mode):
        os.mkdir("." + path, mode)

    def utime(self, path, times):
        os.utime("." + path, times)

    def access(self, path, mode):
        if not os.access("." + path, mode):
            return -EACCES

    def statfs(self):
        return os.statvfs(".")

    def fsinit(self):
        os.fchdir(self.savedrootfd)
        os.close(self.savedrootfd)

    class MonitorReadWriteFile(object):

        def __init__(self, path, flags, *mode):
            self.file = os.fdopen(os.open("." + path, flags, *mode), flag2mode(flags))
            self.fd = self.file.fileno()

        def read(self, length, offset):
            print(f"TODO read at {offset=} of {length=}")
            return os.pread(self.fd, length, offset)

        def write(self, buf, offset):
            print(f"TODO write at {offset=} of {buf=}")
            return os.pwrite(self.fd, buf, offset)

        def release(self, flags):
            self.file.close()

        def _fflush(self):
            if "w" in self.file.mode or "a" in self.file.mode:
                self.file.flush()

        def fsync(self, isfsyncfile):
            self._fflush()
            if isfsyncfile and hasattr(os, "fdatasync"):
                os.fdatasync(self.fd)
            else:
                os.fsync(self.fd)

        def flush(self):
            self._fflush()
            os.close(os.dup(self.fd))

        def fgetattr(self):
            return os.fstat(self.fd)

        def ftruncate(self, len):
            self.file.truncate(len)

        # ignore
        # def lock(self, cmd, owner, **kw):

    def main(self, *a, **kw):
        self.file_class = self.MonitorReadWriteFile
        return Fuse.main(self, *a, **kw)


def main():

    usage = """TODO""" + Fuse.fusage

    server = MonitorReadWrite(
        version="%prog " + fuse.__version__,
        usage=usage,
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
