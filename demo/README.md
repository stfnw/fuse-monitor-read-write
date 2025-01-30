This folder contains some example generated output files showing access patterns for different programs and file types.

# demo-iso

Using Debian Live ISO image from https://cdimage.debian.org/debian-cd/current-live/amd64/iso-hybrid/debian-live-12.8.0-amd64-xfce.iso.

```
7z l debian-live.iso
```

# demo-bigbuckbunny

From https://download.blender.org/peach/bigbuckbunny_movies/

```
# identify magic bytes using `file`
file --keep-going big_buck_bunny_720p_h264.mov
```

# demo-linuztarsrc

From https://git.kernel.org/torvalds/t/linux-6.13-rc6.tar.gz

```
# identify magic bytes using `file`
file              linux-6.13-rc6.tar.gz
file --keep-going linux-6.13-rc6.tar.gz

# list contents
tar -vztf         linux-6.13-rc6.tar.gz
```
