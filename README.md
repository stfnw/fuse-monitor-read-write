Visualize file reads and file writes.

# What is this?

This is a fuse passthrough filesystem that monitors/logs read and write access to files.
Motivation is to analyze and visualize what parts of files are accessed by a program during its operation.

I got the idea after watching the talk https://media.ccc.de/v/38c3-fearsome-file-formats "Fearsome File Formats" by Ange Albertini about e.g. file polyglots.
This project can help visualize which bits and bytes are actually covered by parsers of various programs, which may help identify unexpected parts that do not actually affect the program execution.

The monitoring logic is adapted from the following projects:
- https://github.com/libfuse/python-fuse/blob/c4169e5e864bfb1eec342fe6dd0427959eeeaa38/example/xmp.py (GNU LGPLv2, Jeff Epler, Csaba Henk)
- https://github.com/rflament/loggedfs/blob/82aba9a93489797026ad1a37b637823ece4a7093/src/loggedfs.cpp (Apache 2.0, Remi Flament)

# Usage

Disclaimer: *Do not use this to mount over folders that contain data you care about. If I messed up the mapping this could potentially corrupt data.*

Clone this repo and install the project using your preferred package manager, e.g.:

```
git clone https://github.com/stfnw/fuse-monitor-read-write
cd fuse-monitor-read-write
python3 -m pipx install .
```

The mount the filesystem over an existing directory you want to monitor:

```
fuse-monitor-read-write $DIR_TO_MONITOR
```

This will shadow that directory and for each original file `$FILE` the following additional files are generated:

  - `$FILE.csv`: A machine readable log of all reads and writes.

  - `$FILE-heatmap.png`: An aggregated heatmap of all accesses to the original file.

These files exist only in-memory for the duration the filesystem is mounted.
To preserve them permanently they can simply be copied out of the FUSE mountpoint.

Finally, the filesystem can be unmounted with:

```
fusermount3 -u $DIR_TO_MONITOR
```

# Demo

TODO
