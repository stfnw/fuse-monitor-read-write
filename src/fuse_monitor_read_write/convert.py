#!/usr/bin/python3

from dataclasses import dataclass
from typing import Generator

import argparse
import csv
import io
import os

import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np

# Use non-interactive backend to avoid "UserWarning: Starting a Matplotlib GUI
# outside of the main thread will likely fail."
matplotlib.use("agg")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert logged CSV files into heatmap diagrams"
    )
    parser.add_argument("infile", help="Input CSV file")
    parser.add_argument("outbase", help="Basename of the output file (e.g. /tmp/out)")
    args = parser.parse_args()

    with open(args.infile, "r") as f:
        csvdata = f.read()

    filename = os.path.basename(args.infile).removesuffix(".csv")
    heatmap = generate_heatmap(filename, csvdata)
    with open(f"{args.outbase}-heatmap.png", "wb") as f:
        f.write(heatmap)


@dataclass
class Range:
    offset: int
    length: int


@dataclass
class Pixel:
    x: int
    y: int
    count: int


def generate_heatmap(filename: str, csvdata: str) -> bytes:
    csvparsed = get_csv_data(csvdata)
    return generate_heatmap_(filename, csvparsed)


def get_csv_data(inp: str) -> list[dict[str, str]]:
    csvdata = []
    for d in csv.DictReader(io.StringIO(inp), delimiter=",", quotechar='"'):
        d = dict(d)
        csvdata.append(d)
    return csvdata


def generate_heatmap_(
    filename: str, csvdata: list[dict[str, str]], sidelength_px: int = 64
) -> bytes:
    if not csvdata:
        return b""

    filesize = max(int(d["Filesize"], 10) for d in csvdata)

    processes = sorted(
        list(set(f"{d['ProcessName']} (pid {d['ProcessID']})" for d in csvdata))
    )

    img = np.zeros(shape=(sidelength_px, sidelength_px), dtype=np.uint64)

    for op in csvdata:
        offset_ = int(op["Offset"], 10)
        length_ = int(op["Length"], 10)
        for px in map_chunks(Range(offset_, length_), sidelength_px, filesize):
            img[px.y, px.x] += px.count

    plt.figure(figsize=(10, 10))

    norm = CustomNorm(1, np.max(img))
    plt.imshow(img, cmap="Greys", interpolation="nearest", norm=norm)

    cbar = plt.colorbar()
    cbar.set_label("Number of affected bytes in each pixel")

    plt.title(f"Number of reads of / writes to file '{filename}'")

    plt.ylabel("row (i)", fontweight="bold")
    plt.xlabel("column (j)", fontweight="bold")

    t_pos_y = -0.2
    t = plt.text(
        0.5,
        t_pos_y,
        (
            f"Image width/height in pixels $w = {sidelength_px}$\n"
            + f"Number of image pixels $p = w \\cdot w = {sidelength_px} \\cdot {sidelength_px} = {sidelength_px * sidelength_px}$\n"
            + f"Filesize in bytes $s = {filesize}$\n"
            + f"$\\Rightarrow$ Each pixel corresponds to a chunk of $b = {filesize//(sidelength_px*sidelength_px)}$ bytes\n"
            + "Pixel at position $(i,j)$ maps to byte region\n"
            + "    from inclusive $b (i \\cdot w + j)$\n"
            + "    to exclusive $b (i \\cdot w + j + 1)$\n"
            + "\n"
            + "Processes:"
            + "".join([("\n  - " + p) for p in processes])
        ),
        ha="left",
        va="top",
        transform=plt.gca().transAxes,
    )
    t_bb = t.get_window_extent().transformed(plt.gca().transAxes.inverted())
    t_pos_x = (t_bb.x1 - t_bb.x0) / 2
    t.set_position((t_pos_x, t_pos_y))

    with io.BytesIO() as buf:
        plt.savefig(buf, dpi=300, bbox_inches="tight")
        buf.seek(0)
        imgbytes = buf.read()

    return imgbytes


# The following code solves the following problem:
# We have a very vide range of values we need to visualize, it can range
# from minimum 0 up to > 10000. Yet we nonetheless want to clearly
# distinguish no access at all (0) from at least one (1) access, while also
# showing gradual differences in higher values. With only linear
# interpolation from 0 to vmax, this difference is not visible.
# Therefore we map 0 -> 0, and then linearly interpolate the rest
# vmin=1 to vmax
#   -> newmin=0.2 (some visually distinguishable value) to newmax=1.0
class CustomNorm(mcolors.Normalize):
    def __init__(self, vmin, vmax, clip=False):
        super().__init__(vmin, vmax, clip)

    def __call__(self, value, clip=None):
        if self.vmin == self.vmax:
            return value

        normed = np.zeros_like(value, dtype=np.float64)

        newmin, newmax = 0.2, 1.0
        f = (newmax - newmin) / (self.vmax - self.vmin)
        normed[value > 0] = newmin + (value[value > 0] - self.vmin) * f

        return normed


def map_chunks(rng: Range, sidelength_px: int, filesize: int) -> Generator[Pixel]:
    nbuckets = sidelength_px * sidelength_px
    bucketsize = filesize / nbuckets

    start = int(rng.offset / bucketsize)
    end = int((rng.offset + rng.length - 1) / bucketsize)

    for i in range(start, end + 1):
        x = i % sidelength_px
        y = i // sidelength_px

        # length of intersection of relevant intervals
        int1 = [i * bucketsize, (i + 1) * bucketsize]
        int2 = [rng.offset, rng.offset + rng.length]
        intersection = [max(int1[0], int2[0]), min(int1[1], int2[1])]
        count = int(intersection[1] - intersection[0])

        yield Pixel(x, y, count)


if __name__ == "__main__":
    main()
