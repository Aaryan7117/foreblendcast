"""Simplify data/static/districts.geojson into a compact asset for the Android app.

Usage: python -m outputs.compact_geo [out_path] [tolerance_deg]

Output: {"bounds":[w,s,e,n], "districts":[{"id","name","state","region","c":[lon,lat],"rings":[[x0,y0,x1,y1,...],...]}]}
Coordinates rounded to 3 decimals (~100 m). Douglas-Peucker tolerance in degrees.
"""
import json, math, sys
from pathlib import Path


def dp(points, tol):
    if len(points) < 3:
        return points
    def perp(p, a, b):
        ax, ay = a; bx, by = b; px, py = p
        dx, dy = bx-ax, by-ay
        if dx == 0 and dy == 0:
            return math.hypot(px-ax, py-ay)
        t = max(0, min(1, ((px-ax)*dx + (py-ay)*dy)/(dx*dx+dy*dy)))
        return math.hypot(px-(ax+t*dx), py-(ay+t*dy))
    # iterative DP
    keep = [False]*len(points); keep[0] = keep[-1] = True
    stack = [(0, len(points)-1)]
    while stack:
        i, j = stack.pop()
        if j <= i+1: continue
        dmax, idx = 0.0, -1
        for k in range(i+1, j):
            d = perp(points[k], points[i], points[j])
            if d > dmax: dmax, idx = d, k
        if dmax > tol:
            keep[idx] = True
            stack.append((i, idx)); stack.append((idx, j))
    return [p for p, k in zip(points, keep) if k]

def ring_area(r):
    a = 0.0
    for i in range(len(r)-1):
        a += r[i][0]*r[i+1][1] - r[i+1][0]*r[i][1]
    return a/2


def build_compact(src: Path, out: Path, tol: float = 0.012) -> dict:
    """Write the compact geometry file and return a small stats dict."""
    g = json.load(open(src, encoding="utf-8"))
    W, S_, E, N = 180, 90, -180, -90
    districts = []
    n_in = n_out = 0
    for f in g["features"]:
        p = f["properties"]; geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        rings = []
        cx = cy = ca = 0.0
        for poly in polys:
            outer = poly[0]  # drop holes for a choropleth
            n_in += len(outer)
            simp = dp(outer, tol)
            if len(simp) < 4:
                simp = outer[:: max(1, len(outer)//8)] + [outer[0]]
            n_out += len(simp)
            flat = []
            for x, y in simp:
                flat.append(round(x, 3)); flat.append(round(y, 3))
                W, S_, E, N = min(W, x), min(S_, y), max(E, x), max(N, y)
            rings.append(flat)
            a = abs(ring_area(outer))
            xs = [q[0] for q in outer]; ys = [q[1] for q in outer]
            cx += a*sum(xs)/len(xs); cy += a*sum(ys)/len(ys); ca += a
        c = [round(cx/ca, 3), round(cy/ca, 3)] if ca else [round(rings[0][0], 3), round(rings[0][1], 3)]
        districts.append({"id": p["id"], "name": p["name"], "state": p["state"],
                          "region": p.get("region", ""), "c": c, "rings": rings})
    obj = {"bounds": [round(W, 3), round(S_, 3), round(E, 3), round(N, 3)], "districts": districts}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(obj, separators=(",", ":")), encoding="utf-8")
    return {"vertices_in": n_in, "vertices_out": n_out, "districts": len(districts), "bytes": out.stat().st_size}


if __name__ == "__main__":
    src = Path("data/static/districts.geojson")
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/static/districts_compact.json")
    tol = float(sys.argv[2]) if len(sys.argv) > 2 else 0.012
    print(build_compact(src, out, tol))
