#!/usr/bin/env python3
"""Finds the sun of an equirectangular .hdr (Radiance RGBE): the direction toward it in the
engine's convention (u = atan2(z, x) / 2pi + 0.5, v = asin(-y) / pi + 0.5, the top row is the
zenith) and its color. usage: hdri_sun.py <file.hdr>"""
import math, sys


def read_hdr(path):
    with open(path, "rb") as f:
        data = f.read()
    pos = data.index(b"\n\n") + 2
    line_end = data.index(b"\n", pos)
    parts = data[pos:line_end].split()
    height, width = int(parts[1]), int(parts[3])
    pos = line_end + 1
    rows = []
    for _ in range(height):
        if data[pos] != 2 or data[pos + 1] != 2:
            raise SystemExit("only run-length encoded .hdr files are read")
        pos += 4
        channels = []
        for _ in range(4):
            out = bytearray()
            while len(out) < width:
                count = data[pos]
                pos += 1
                if count > 128:
                    out.extend(bytes([data[pos]]) * (count - 128))
                    pos += 1
                else:
                    out.extend(data[pos:pos + count])
                    pos += count
            channels.append(out)
        rows.append(channels)
    return width, height, rows


def sun_of(path):
    width, height, rows = read_hdr(path)
    # The brightest 0.02% of the sphere by luminance, weighted: the sun disc and its glare.
    samples = []
    for y, (r, g, b, e) in enumerate(rows):
        weight = math.cos((y + 0.5) / height * math.pi - math.pi / 2)  # the solid angle of a row
        for x in range(width):
            if e[x] < 136:  # below 2^8: not a light source of the scale of the sun
                continue
            scale = math.ldexp(1.0, e[x] - 136)
            rgb = (r[x] * scale, g[x] * scale, b[x] * scale)
            luminance = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
            samples.append((luminance, x, y, rgb, weight))
    if not samples:
        return None
    samples.sort(reverse=True)
    top = samples[:max(8, int(width * height * 0.0002))]
    total = sum(s[0] * s[4] for s in top)
    direction = [0.0, 0.0, 0.0]
    color = [0.0, 0.0, 0.0]
    for luminance, x, y, rgb, weight in top:
        u = (x + 0.5) / width
        v = (y + 0.5) / height
        phi = (u - 0.5) * 2 * math.pi
        elevation = -(v - 0.5) * math.pi
        d = (math.cos(elevation) * math.cos(phi), math.sin(elevation), math.cos(elevation) * math.sin(phi))
        w = luminance * weight / total
        for i in range(3):
            direction[i] += d[i] * w
            color[i] += rgb[i] * w
    length = math.sqrt(sum(c * c for c in direction))
    direction = [c / length for c in direction]
    peak = max(color)
    return {"direction": direction, "color": [c / peak for c in color], "peak": top[0][0],
            "elevation": math.degrees(math.asin(direction[1]))}


if __name__ == "__main__":
    print(sun_of(sys.argv[1]))
