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

from threading import Lock
import datetime
import errno
import os
import stat

from typing import Any, Generator, Optional

import fuse
from fuse import Fuse

from fuse_monitor_read_write import convert


fuse.fuse_python_api = (0, 2)
fuse.feature_assert("stateful_files", "has_init")


lock = Lock()  # Lock for csv_files.
csv_files: dict[str, bytes] = {}


def flag2mode(flags: int) -> str:
    md = {os.O_RDONLY: "rb", os.O_WRONLY: "wb", os.O_RDWR: "wb+"}
    m = md[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]

    if flags | os.O_APPEND:
        m = m.replace("w", "a", 1)

    return m


class MonitorReadWrite(Fuse):

    def __init__(self, *args: Any, **kw: Any) -> None:
        Fuse.__init__(self, *args, **kw)
        # Options taken from https://github.com/rflament/loggedfs/blob/82aba9a93489797026ad1a37b637823ece4a7093/src/loggedfs.cpp#L771C1-L771C104
        self.fuse_args.add("nonempty")
        self.fuse_args.add("use_ino")
        self.fuse_args.add("atomic_o_trunc")
        self.file_class = MonitorReadWriteFile

    def getattr(self, path: str) -> Any:
        if path.endswith(".csv"):
            base = path.removesuffix(".csv")
            if len(base) > 1 and os.path.isfile("." + base):
                st = fuse.Stat()
                st.st_mode = stat.S_IFREG | 0o444
                st.st_nlink = 1
                with lock:
                    st.st_size = len(csv_files[base]) if base in csv_files else 0
                return st

        elif path.endswith("-heatmap.png"):
            base = path.removesuffix("-heatmap.png")
            if len(base) > 1 and os.path.isfile("." + base):
                st = fuse.Stat()
                st.st_mode = stat.S_IFREG | 0o444
                st.st_nlink = 1
                # Dummy length (/proc seems to also do it similarly).
                # This has the disadvantage that we cannot directly open it
                # easily from the file explorer. But otherwise we would have to
                # generate heatmaps for all files for the icon preview,
                # which is too expensive.
                st.st_size = 0
                return st

        return os.lstat("." + path)

    def readlink(self, path: str) -> str:
        return os.readlink("." + path)

    def readdir(self, path: str, _offset: int) -> Generator[fuse.Direntry]:
        for e in os.listdir("." + path):
            yield fuse.Direntry(e)
            if os.path.isfile(e):
                yield fuse.Direntry(e + ".csv")
                yield fuse.Direntry(e + "-heatmap.png")

    def unlink(self, path: str) -> None:
        os.unlink("." + path)

    def rmdir(self, path: str) -> None:
        os.rmdir("." + path)

    def symlink(self, path: str, path1: str) -> None:
        os.symlink(path, "." + path1)

    def rename(self, path: str, path1: str) -> None:
        os.rename("." + path, "." + path1)

    def link(self, path: str, path1: str) -> None:
        os.link("." + path, "." + path1)

    def chmod(self, path: str, mode: int) -> None:
        os.chmod("." + path, mode)

    def chown(self, path: str, user: int, group: int) -> None:
        os.chown("." + path, user, group)

    def truncate(self, path: str, length: int) -> None:
        with open("." + path, "a") as f:
            f.truncate(length)

    def mknod(self, path: str, mode: int, dev: Any) -> None:
        os.mknod("." + path, mode, dev)

    def mkdir(self, path: str, mode: int) -> None:
        os.mkdir("." + path, mode)

    def utime(self, path: str, times: Any) -> None:
        os.utime("." + path, times)

    def access(self, path: str, mode: int) -> Any:
        if not os.access("." + path, mode):
            return -errno.EACCES

    def statfs(self) -> Any:
        return os.statvfs(".")

    def fsinit(self) -> None:
        os.fchdir(self.savedrootfd)
        os.close(self.savedrootfd)

    def main(self, *a: Any, **kw: Any) -> Any:
        return Fuse.main(self, *a, **kw)


class MonitorReadWriteFile:

    def __init__(self, path: str, flags: int, *mode: Any) -> None:
        self.path = path

        self.is_generated_csv = False
        self.is_generated_heatmap = False

        if path.endswith(".csv"):
            base = path.removesuffix(".csv")
            if len(base) > 1 and os.path.isfile("." + base):
                self.is_generated_csv = True
                self.pathbase = base
                path = base

        elif path.endswith("-heatmap.png"):
            # Note that we have to set direct IO here because in `getattr` we
            # reported the png file as having size 0.
            # If we do not set direct IO the kernel will take the size 0 as the
            # size to buffer and `read` will never actually be called when the
            # file is later tried to be read.
            self.direct_io = True
            base = path.removesuffix("-heatmap.png")
            if len(base) > 1 and os.path.isfile("." + base):
                self.is_generated_heatmap = True
                self.pathbase = base
                path = base
                self.heatmapdata: Optional[bytes] = None

        else:
            self.file = os.fdopen(os.open("." + path, flags, *mode), flag2mode(flags))
            self.fd = self.file.fileno()

        with lock:
            if path not in csv_files:
                csv_files[path] = to_csv(
                    [
                        "Time",
                        "AccessDirection",
                        "Offset",
                        "Length",
                        "Filesize",
                        "ProcessID",
                        "ProcessName",
                    ]
                )

    def read(self, length: int, offset: int) -> bytes:
        if self.is_generated_csv:
            with lock:
                return csv_files[self.pathbase][offset : offset + length]

        if self.is_generated_heatmap:
            if self.heatmapdata is None:
                with lock:
                    tmp = csv_files[self.pathbase].decode("utf8")

                if len(list(tmp.splitlines())) <= 1:
                    # We do not actually have content yet, only the CSV header.
                    return b""

                self.heatmapdata = convert.generate_heatmap(self.pathbase, tmp)

            return self.heatmapdata[offset : offset + length]

        # Requested read may be outside of the file size; in the CSV we
        # report the actually read bytes.
        bytes_read = os.pread(self.fd, length, offset)

        timestamp = get_timestamp()
        filesize = os.fstat(self.fd).st_size
        (pid, pname) = get_process_id_name()

        with lock:
            csv_files[self.path] += to_csv(
                [
                    timestamp,
                    "read",
                    str(offset),
                    str(len(bytes_read)),
                    str(filesize),
                    str(pid),
                    pname,
                ]
            )

        return bytes_read

    def write(self, buf: bytes, offset: int) -> int:
        if self.is_generated_csv or self.is_generated_heatmap:
            return 0  # Silently ignore writes.

        # Write may increase filesize, so we perform it first before querying
        # the filesize.
        bytes_written = os.pwrite(self.fd, buf, offset)

        timestamp = get_timestamp()
        filesize = os.fstat(self.fd).st_size
        (pid, pname) = get_process_id_name()

        with lock:
            csv_files[self.path] += to_csv(
                [
                    timestamp,
                    "write",
                    str(offset),
                    str(len(buf)),
                    str(filesize),
                    str(pid),
                    pname,
                ]
            )

        return bytes_written

    def release(self, _flags: int) -> None:
        if self.is_generated_csv or self.is_generated_heatmap:
            return  # Silently ignore.
        self.file.close()

    def _fflush(self) -> None:
        if self.is_generated_csv or self.is_generated_heatmap:
            return  # Silently ignore.
        if "w" in self.file.mode or "a" in self.file.mode:
            self.file.flush()

    def fsync(self, isfsyncfile: Any) -> None:
        if self.is_generated_csv or self.is_generated_heatmap:
            return  # Silently ignore.
        self._fflush()
        if isfsyncfile and hasattr(os, "fdatasync"):
            os.fdatasync(self.fd)
        else:
            os.fsync(self.fd)

    def flush(self) -> None:
        if self.is_generated_csv or self.is_generated_heatmap:
            return  # Silently ignore.
        self._fflush()
        os.close(os.dup(self.fd))

    def fgetattr(self) -> os.stat_result:
        if self.is_generated_csv or self.is_generated_heatmap:
            return os.stat(self.pathbase)
        return os.fstat(self.fd)

    def ftruncate(self, length: int) -> None:
        if self.is_generated_csv or self.is_generated_heatmap:
            return  # Silently ignore.
        self.file.truncate(length)

    # ignore
    # def lock(self, cmd, owner, **kw):


def to_csv(lst: list[str]) -> bytes:
    res = ['"' + escape_quotes(s) + '"' for s in lst]
    return (",".join(res) + "\n").encode("utf8")


def escape_quotes(s: str) -> str:
    return s.replace('"', '\\"')


def get_timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def get_process_id_name() -> tuple[int, str]:
    pid = fuse.FuseGetContext()["pid"]
    with open(f"/proc/{pid}/comm", "r") as f:
        pname = f.read().strip()
    return (pid, pname)
