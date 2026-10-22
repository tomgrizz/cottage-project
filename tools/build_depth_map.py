"""Build the Big Clear Lake depth map and write it into index.html.

Data (in tools/data):
  big-clear-lake-contours.json   Ontario MNR "Bathymetry Line" (1984 transect survey), depth in metres
  big-clear-lake-shoreline.json  OpenStreetMap relation 1146593 (CanVec shoreline and islands)

Run from the project folder:  python tools/build_depth_map.py
The SVG goes between the <!-- depth-map:start --> and <!-- depth-map:end --> markers.
"""
import json
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tools", "data")
INDEX = os.path.join(ROOT, "index.html")

WIDTH = 600          # SVG units across the map area
PAD = 18             # breathing room around the lake
SIMPLIFY = 0.45      # Douglas-Peucker tolerance in SVG units
M_TO_FT = 3.28084

# Depth bands, in metres: band i covers BANDS[i] to BANDS[i+1]; the last is open-ended
BANDS = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]


def band_of(depth):
    """Index of the band that starts at this contour depth (1 m sits inside the 0-2 m band)."""
    best = 0
    for i, start in enumerate(BANDS):
        if depth >= start:
            best = i
    return best


def band_label(i):
    lo = BANDS[i]
    if i == len(BANDS) - 1:
        return f"{lo} m+ ({round(lo * M_TO_FT)} ft+)"
    hi = BANDS[i + 1]
    return f"{lo}–{hi} m ({round(lo * M_TO_FT)}–{round(hi * M_TO_FT)} ft)"


# ---------- geometry helpers ----------
def area(ring):
    s = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        s += x1 * y2 - x2 * y1
    return s / 2


def contains(ring, pt):
    x, y = pt
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def simplify(points, tol):
    if len(points) < 4:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = points[a]
        bx, by = points[b]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy) or 1e-9
        far, far_d = None, tol
        for i in range(a + 1, b):
            px, py = points[i]
            d = abs(dy * (px - ax) - dx * (py - ay)) / norm
            if d > far_d:
                far, far_d = i, d
        if far is not None:
            keep[far] = True
            stack += [(a, far), (far, b)]
    return [p for p, k in zip(points, keep) if k]


def label_point(ring):
    """A point well inside the ring: the best of a grid of candidates, by distance to the edge."""
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    best, best_d = None, -1
    steps = 14
    for i in range(1, steps):
        for j in range(1, steps):
            pt = (min(xs) + (max(xs) - min(xs)) * i / steps, min(ys) + (max(ys) - min(ys)) * j / steps)
            if not contains(ring, pt):
                continue
            d = min(math.hypot(pt[0] - x, pt[1] - y) for x, y in ring)
            if d > best_d:
                best, best_d = pt, d
    return best or (sum(xs) / len(xs), sum(ys) / len(ys))


def path(ring):
    pts = " ".join(f"{x:.1f} {y:.1f}" for x, y in ring)
    return f"M{pts}Z"


# ---------- load and project ----------
shore = json.load(open(os.path.join(DATA, "big-clear-lake-shoreline.json")))
contours = json.load(open(os.path.join(DATA, "big-clear-lake-contours.json")))["contours"]

all_lonlat = [c for r in shore["rings"] for c in r["coords"]]
lon0 = (min(c[0] for c in all_lonlat) + max(c[0] for c in all_lonlat)) / 2
lat0 = (min(c[1] for c in all_lonlat) + max(c[1] for c in all_lonlat)) / 2
kx = 111320 * math.cos(math.radians(lat0))   # metres per degree of longitude here
ky = 110574                                   # metres per degree of latitude


def to_m(lon, lat):
    return ((lon - lon0) * kx, (lat0 - lat) * ky)


xs = [to_m(*c)[0] for c in all_lonlat]
ys = [to_m(*c)[1] for c in all_lonlat]
scale = (WIDTH - 2 * PAD) / (max(xs) - min(xs))   # SVG units per metre
HEIGHT = round((max(ys) - min(ys)) * scale + 2 * PAD)
x_off, y_off = min(xs), min(ys)


def project(coords):
    pts = [((to_m(*c)[0] - x_off) * scale + PAD, (to_m(*c)[1] - y_off) * scale + PAD) for c in coords]
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    # Split the closed ring at its far point so each half simplifies as an open line
    far = max(range(len(pts)), key=lambda i: math.hypot(pts[i][0] - pts[0][0], pts[i][1] - pts[0][1]))
    first = simplify(pts[: far + 1], SIMPLIFY)
    second = simplify(pts[far:] + [pts[0]], SIMPLIFY)
    return first[:-1] + second[:-1]


outer = [project(r["coords"]) for r in shore["rings"] if r["role"] == "outer"]
islands = [project(r["coords"]) for r in shore["rings"] if r["role"] == "inner"]

rings = []
for c in contours:
    pts = project(c["coords"])
    if len(pts) >= 3:
        rings.append({"depth": c["depth_m"], "pts": pts, "area": abs(area(pts))})

# Nest the contours: each ring's parent is the smallest larger ring around it
rings.sort(key=lambda r: -r["area"])
for i, r in enumerate(rings):
    r["parent"] = None
    probe = r["pts"][0]
    for j in range(i - 1, -1, -1):
        if contains(rings[j]["pts"], probe):
            r["parent"] = rings[j]
            break
    p = r["parent"]
    if p is None or r["depth"] > p["depth"]:
        r["kind"] = "hole"          # water gets deeper inside this line
    elif r["depth"] < p["depth"]:
        r["kind"] = "hump"          # water gets shallower inside this line
    else:
        r["kind"] = "hump" if p["kind"] == "hole" else "hole"
    b = band_of(r["depth"])
    r["band"] = b if r["kind"] == "hole" else max(0, b - 1)

has_child = {id(r["parent"]) for r in rings if r["parent"]}
deepest = max(r["depth"] for r in rings)

# ---------- SVG ----------
out = []
out.append(f'<svg class="depth-svg" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="depth-title depth-desc">')
out.append('<title id="depth-title">Depth map of Big Clear Lake</title>')
out.append(f'<desc id="depth-desc">Depth contours for Big Clear Lake every 2 metres, from the shoreline down to {deepest:g} metres '
           f'({round(deepest * M_TO_FT)} feet) and deeper in the basins. Lighter blue is shallow, darker blue is deep.</desc>')
out.append('<defs><clipPath id="lake-clip">' + "".join(f'<path d="{path(r)}"/>' for r in outer) + "</clipPath></defs>")
out.append('<rect class="dm-land" width="100%" height="100%"/>')
for r in outer:
    out.append(f'<path class="dm-band dm-b0" data-band="0" d="{path(r)}"/>')
out.append('<g clip-path="url(#lake-clip)">')
for r in rings:
    out.append(f'<path class="dm-band dm-b{r["band"]}" data-band="{r["band"]}" d="{path(r["pts"])}"/>')
out.append("</g>")
for r in islands:
    out.append(f'<path class="dm-island" d="{path(r)}"/>')
for r in outer:
    out.append(f'<path class="dm-shore" d="{path(r)}"/>')

# Labels: the deepest basins, and humps that rise out of deeper water
labels = []
for r in rings:
    if id(r) in has_child or r["area"] < 60:
        continue
    x, y = label_point(r["pts"])
    if r["kind"] == "hole" and r["depth"] >= 12:
        text = f'{r["depth"]:g} m+' if r["depth"] >= BANDS[-1] else f'{r["depth"]:g}–{r["depth"] + 2:g} m'
        labels.append((x, y, text, "dm-label"))
    elif r["kind"] == "hump" and r["parent"] is not None and r["parent"]["depth"] >= 8:
        labels.append((x, y, "Hump", "dm-label dm-label-hump"))
for x, y, text, cls in labels:
    out.append(f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}">{text}</text>')

# Scale bar (500 m) and north arrow, bottom left over land or shallow water
bar = 500 * scale
sx, sy = PAD + 4, HEIGHT - PAD - 6
out.append(f'<g class="dm-scale"><path d="M{sx:.1f} {sy - 5:.1f}V{sy:.1f}H{sx + bar:.1f}V{sy - 5:.1f}"/>'
           f'<text x="{sx + bar / 2:.1f}" y="{sy - 9:.1f}">500 m</text></g>')
nx, ny = WIDTH - PAD - 12, PAD + 22
out.append(f'<g class="dm-north"><path d="M{nx:.1f} {ny - 20:.1f}L{nx + 7:.1f} {ny:.1f}L{nx:.1f} {ny - 5:.1f}L{nx - 7:.1f} {ny:.1f}Z"/>'
           f'<text x="{nx:.1f}" y="{ny + 14:.1f}">N</text></g>')
out.append("</svg>")
svg = "\n".join(out)

legend = ['<ol class="depth-legend" aria-label="Depth key">']
for i in range(len(BANDS)):
    legend.append(f'<li><span class="dm-swatch dm-b{i}"></span><span class="dm-tick">{BANDS[i]}</span></li>')
legend.append("</ol>")
labels_json = json.dumps([band_label(i) for i in range(len(BANDS))])

block = (
    "<!-- depth-map:start (generated by tools/build_depth_map.py; edit the script, not this block) -->\n"
    + svg + "\n"
    + f'<div class="depth-tip" id="depth-tip" hidden></div>\n'
    + f"<script type=\"application/json\" id=\"depth-bands\">{labels_json}</script>\n"
    + "\n".join(legend) + "\n"
    + "<!-- depth-map:end -->"
)

html = open(INDEX, encoding="utf-8").read()
html, n = re.subn(r"<!-- depth-map:start.*?<!-- depth-map:end -->", lambda m: block, html, flags=re.S)
if n != 1:
    raise SystemExit("Could not find the depth-map markers in index.html")
open(INDEX, "w", encoding="utf-8").write(html)

holes = sum(1 for r in rings if r["kind"] == "hole")
print(f"map {WIDTH}x{HEIGHT}, {len(rings)} contours ({holes} deeper-inside, {len(rings) - holes} humps), "
      f"{len(islands)} islands, {len(labels)} labels, deepest contour {deepest:g} m, svg {len(svg) // 1024} KB")
for x, y, text, _ in labels:
    print(f"  label {text!r} at {x:.0f},{y:.0f}")
