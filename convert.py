#!/usr/bin/python3

from dataclasses import dataclass
from typing import Generator
import argparse
import csv
import io
import matplotlib.pyplot as plt
import numpy as np
import os


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert logged CSV files from fuse-monitor-read-write.py into diagrams"
    )
    parser.add_argument("infile", help="Input CSV file")
    parser.add_argument("outbase", help="Basename of the output files (e.g. /tmp/out")
    args = parser.parse_args()

    with open(args.infile, "r") as f:
        csvdata = [dict(d) for d in csv.DictReader(f, delimiter=",", quotechar='"')]

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


def generate_heatmap(
    filename: str, csvdata: list[dict[str, str]], sidelength_px: int = 64
) -> bytes:
    filesize = max(int(d["Filesize"], 10) for d in csvdata)

    processes = sorted(
        list(set(f"{d['ProcessName']} ({d['ProcessID']})" for d in csvdata))
    )

    img = np.zeros(shape=(sidelength_px, sidelength_px), dtype=np.uint64)

    def map_chunks(rng: Range) -> Generator[Pixel]:
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

    for op in csvdata:
        offset_ = int(op["Offset"], 10)
        length_ = int(op["Length"], 10)
        for px in map_chunks(Range(offset_, length_)):
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
            f"Image width/height in pixels $w = {sidelength_px}$\n"
            + f"Number of image pixels $p = w \\cdot w = {sidelength_px} \\cdot {sidelength_px} = {sidelength_px * sidelength_px}$\n"
            + f"Filesize in bytes $s = {filesize}$\n"
            + f"$\\Rightarrow$ Each pixel corresponds to a chunk of $b = {filesize//(sidelength_px*sidelength_px)}$ bytes\n"
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

    with io.BytesIO() as buf:
        plt.savefig(buf, dpi=150, bbox_inches="tight")
        buf.seek(0)
        imgbytes = buf.read()

    return imgbytes


if __name__ == "__main__":
    main()
