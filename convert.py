#!/usr/bin/python3

import argparse
import matplotlib.pyplot as plt
import numpy as np
from dataclasses import dataclass
from typing import Generator


def main():
    parser = argparse.ArgumentParser(
        description="Convert logged CSV files from fuse-monitor-read-write.py into diagrams"
    )
    parser.add_argument("infile", help="Input CSV file")
    parser.add_argument("outbase", help="Basename of the output files (e.g. /tmp/out")
    args = parser.parse_args()

    with open(args.infile, "r") as f:
        data = f.read()


def tmp():
    # TODO replace example data with actual data read from a CSV
    filename = "/debian-live-12.8.0-amd64-xfce.iso"
    filesize = 3188801536
    data = [
        [0, 16384],
        [524288, 4096],
    ]

    @dataclass
    class Range:
        offset: int
        length: int

    @dataclass
    class Pixel:
        x: int
        y: int
        count: int

    length = 64

    img = np.zeros(shape=(length, length), dtype=np.uint64)

    def map_chunks(rng: Range) -> Generator[Pixel]:
        nbuckets = length * length
        bucketsize = filesize / nbuckets

        start = int(rng.offset / bucketsize)
        end = int((rng.offset + rng.length - 1) / bucketsize)

        for i in range(start, end + 1):
            x = i % length
            y = i // length

            # length of intersection of relevant intervals
            int1 = [i * bucketsize, (i + 1) * bucketsize]
            int2 = [rng.offset, rng.offset + rng.length]
            intersection = [max(int1[0], int2[0]), min(int1[1], int2[1])]
            count = int(intersection[1] - intersection[0])

            yield Pixel(x, y, count)

    for op in data:
        for px in map_chunks(Range(op[0], op[1])):
            img[px.y, px.x] += px.count

    fig = plt.figure(figsize=(10, 10))

    plt.imshow(img, cmap="Greys", interpolation="nearest")

    cbar = plt.colorbar()
    cbar.set_label("Number of affected bytes in each pixel")

    plt.title(f"Number of reads of file '{filename}'")

    plt.ylabel("row (i)", fontweight="bold")
    plt.xlabel("column (j)", fontweight="bold")

    t_pos_y = -0.2
    t = plt.text(
        0.5,
        t_pos_y,
        (
            f"Image width/height in pixels $w = {length}$\n"
            + f"Number of image pixels $p = w \\cdot w = {length} \\cdot {length} = {length * length}$\n"
            + f"Filesize in bytes $s = {filesize}$\n"
            + f"$\\Rightarrow$ Each pixel corresponds to a chunk of $b = {filesize//(length*length)}$ bytes\n"
            + "Pixel at position $(i,j)$ maps to byte region\n"
            + "    from inclusive $b (i \\cdot w + j)$\n"
            + "    to exclusive $b (i \\cdot w + j + 1)$"
        ),
        ha="left",
        va="center",
        transform=plt.gca().transAxes,
    )
    t_bb = t.get_window_extent().transformed(plt.gca().transAxes.inverted())
    t_pos_x = (t_bb.x1 - t_bb.x0) / 2
    t.set_position((t_pos_x, t_pos_y))

    # TODO add filter by program name
    # TODO output list of program names and pids

    # TODO adapt (e.g. BytesIO to get bytes)
    plt.savefig("/tmp/test.png", dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    main()
