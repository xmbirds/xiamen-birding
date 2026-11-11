# -*- coding: utf-8 -*-
import json
import math
import os
from spots_data_1109 import INTRO_DATA, SPOTS_1109

OUT_DIR = "/Users/libo/xmbirds/birdspoint"

with open(os.path.join(OUT_DIR, "osm_xiamen_raw.json"), "r", encoding="utf-8") as f:
    osm = json.load(f)

with open(os.path.join(OUT_DIR, "xiamen_districts.json"), "r", encoding="utf-8") as f:
    districts_data = json.load(f)

osm_extra_path = os.path.join(OUT_DIR, "osm_xiamen_extra.json")
osm_extra = None
if os.path.exists(osm_extra_path):
    with open(osm_extra_path, "r", encoding="utf-8") as f:
        osm_extra = json.load(f)

def lonlat_to_tile_xy(lon, lat, z):
    n = 2.0 ** z
    x = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y

z = 11
min_lon, max_lon = 117.88, 118.45
min_lat, max_lat = 24.41, 24.90

x0_f, y0_f = lonlat_to_tile_xy(min_lon, max_lat, z)
x1_f, y1_f = lonlat_to_tile_xy(max_lon, min_lat, z)

SVG_W = 1000
SVG_H = int(round(SVG_W * (y1_f - y0_f) / (x1_f - x0_f)))

def tile_xy_to_svg(tx_float, ty_float):
    sx = (tx_float - x0_f) / (x1_f - x0_f) * SVG_W
    sy = (ty_float - y0_f) / (y1_f - y0_f) * SVG_H
    return sx, sy

def lonlat_to_svg(lon, lat):
    tx, ty = lonlat_to_tile_xy(lon, lat, z)
    sx, sy = tile_xy_to_svg(tx, ty)
    return round(sx, 1), round(sy, 1)

# Parse OSM nodes and ways
nodes = {}
ways = {}
relations = []

for el in osm["elements"]:
    t = el["type"]
    if t == "node":
        nodes[el["id"]] = (el["lon"], el["lat"])
    elif t == "way":
        ways[el["id"]] = el
    elif t == "relation":
        relations.append(el)

extra_nodes = {}
extra_ways = {}
if osm_extra:
    for el in osm_extra["elements"]:
        if el["type"] == "node":
            extra_nodes[el["id"]] = (el["lon"], el["lat"])
        elif el["type"] == "way":
            extra_ways[el["id"]] = el

# Stitch high-precision OSM coastline
coast_ways = [
    w["nodes"] for w in ways.values()
    if w.get("tags", {}).get("natural") == "coastline" and len(w.get("nodes", [])) >= 2
]

start_map = {}
for idx, nlist in enumerate(coast_ways):
    start_map.setdefault(nlist[0], []).append(idx)

used = set()
closed_rings = []
open_chains = []

end_nodes = {nlist[-1] for nlist in coast_ways}
for idx, nlist in enumerate(coast_ways):
    if idx in used:
        continue
    if nlist[0] not in end_nodes:
        used.add(idx)
        chain = list(nlist)
        while True:
            curr_end = chain[-1]
            next_candidates = [i for i in start_map.get(curr_end, []) if i not in used]
            if not next_candidates:
                break
            nxt = next_candidates[0]
            used.add(nxt)
            chain.extend(coast_ways[nxt][1:])
            if chain[0] == chain[-1]:
                break
        if chain[0] == chain[-1]:
            closed_rings.append(chain)
        else:
            open_chains.append(chain)

for idx, nlist in enumerate(coast_ways):
    if idx in used:
        continue
    used.add(idx)
    chain = list(nlist)
    while True:
        if chain[0] == chain[-1]:
            break
        curr_end = chain[-1]
        next_candidates = [i for i in start_map.get(curr_end, []) if i not in used]
        if not next_candidates:
            break
        nxt = next_candidates[0]
        used.add(nxt)
        chain.extend(coast_ways[nxt][1:])
    if chain[0] == chain[-1]:
        closed_rings.append(chain)
    else:
        open_chains.append(chain)

def nodes_to_svg_pts(nlist, node_dict=nodes, min_dist=0.55):
    pts = [lonlat_to_svg(node_dict[nid][0], node_dict[nid][1]) for nid in nlist if nid in node_dict]
    if len(pts) < 2:
        return []
    out = [pts[0]]
    for p in pts[1:]:
        dx = p[0] - out[-1][0]
        dy = p[1] - out[-1][1]
        if dx*dx + dy*dy >= min_dist * min_dist:
            out.append(p)
    if out[-1] != pts[-1]:
        out.append(pts[-1])
    return out

def pts_to_path_d(pts, close=True):
    if len(pts) < 2:
        return ""
    cmds = [f"M{pts[0][0]},{pts[0][1]}"]
    for p in pts[1:]:
        cmds.append(f"L{p[0]},{p[1]}")
    if close:
        cmds.append("Z")
    return "".join(cmds)

land_path_parts = []
coastline_stroke_parts = []
global_land_lonlat_rings = []

for chain in open_chains:
    pts = nodes_to_svg_pts(chain, min_dist=0.55)
    if len(pts) < 3:
        continue
    coastline_stroke_parts.append(pts_to_path_d(pts, close=False))
    raw_lonlat = [nodes[nid] for nid in chain if nid in nodes]
    p0 = nodes[chain[0]]
    p1 = nodes[chain[-1]]
    if p0[0] < 118.00 and p1[0] > 118.40:
        closed_pts = pts + [(SVG_W + 30, pts[-1][1]), (SVG_W + 30, -30), (-30, -30), (-30, pts[0][1])]
        land_path_parts.append(pts_to_path_d(closed_pts, close=True))
        global_land_lonlat_rings.append(raw_lonlat + [(118.55, p1[1]), (118.55, 25.00), (117.80, 25.00), (117.80, p0[1])])
    elif p0[0] > 118.40 and p1[1] < 24.41:
        closed_pts = pts + [(pts[-1][0], SVG_H + 30), (SVG_W + 30, SVG_H + 30), (SVG_W + 30, pts[0][1])]
        land_path_parts.append(pts_to_path_d(closed_pts, close=True))
        global_land_lonlat_rings.append(raw_lonlat + [(p1[0], 24.35), (118.55, 24.35), (118.55, p0[1])])
    elif p0[0] < 118.08 and p1[0] < 118.08 and p0[1] < 24.43:
        closed_pts = pts + [(-30, pts[-1][1]), (-30, SVG_H + 30), (pts[0][0], SVG_H + 30)]
        land_path_parts.append(pts_to_path_d(closed_pts, close=True))
        global_land_lonlat_rings.append(raw_lonlat + [(117.80, p1[1]), (117.80, 24.35), (p0[0], 24.35)])

for ring in closed_rings:
    pts = nodes_to_svg_pts(ring, min_dist=0.5)
    if len(pts) >= 3:
        d_str = pts_to_path_d(pts, close=True)
        land_path_parts.append(d_str)
        coastline_stroke_parts.append(d_str)
        global_land_lonlat_rings.append([nodes[nid] for nid in ring if nid in nodes])

svg_exact_land_d = " ".join(land_path_parts)
svg_exact_coast_d = " ".join(coastline_stroke_parts)

# Real inland water bodies
water_path_parts = []
for w in ways.values():
    tags = w.get("tags", {})
    if tags.get("natural") == "water" and len(w.get("nodes", [])) >= 4:
        pts = nodes_to_svg_pts(w["nodes"], min_dist=0.7)
        if len(pts) >= 3:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if (max(xs) - min(xs)) >= 2.2 or (max(ys) - min(ys)) >= 2.2:
                water_path_parts.append(pts_to_path_d(pts, close=True))

for rel in relations:
    tags = rel.get("tags", {})
    if tags.get("natural") == "water":
        for m in rel.get("members", []):
            if m["type"] == "way" and m["ref"] in ways and m.get("role") in ("outer", ""):
                w_nodes = ways[m["ref"]].get("nodes", [])
                pts = nodes_to_svg_pts(w_nodes, min_dist=0.7)
                if len(pts) >= 3:
                    water_path_parts.append(pts_to_path_d(pts, close=(w_nodes[0] == w_nodes[-1])))

svg_exact_water_d = " ".join(water_path_parts)

# Real Forest / Park polygons & Major Highways/Bridges
real_green_parts = []
real_road_parts = []
for w in extra_ways.values():
    tags = w.get("tags", {})
    nlist = w.get("nodes", [])
    if any(k in tags for k in ("leisure", "natural", "landuse")) and len(nlist) >= 4:
        pts = nodes_to_svg_pts(nlist, node_dict=extra_nodes, min_dist=1.2)
        if len(pts) >= 3:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if (max(xs) - min(xs)) >= 4.0 or (max(ys) - min(ys)) >= 4.0:
                real_green_parts.append(pts_to_path_d(pts, close=True))
    elif "highway" in tags and len(nlist) >= 2:
        pts = nodes_to_svg_pts(nlist, node_dict=extra_nodes, min_dist=1.8)
        if len(pts) >= 2:
            real_road_parts.append(pts_to_path_d(pts, close=False))

svg_real_green_d = " ".join(real_green_parts)
svg_real_roads_d = " ".join(real_road_parts)

# Separate Xiamen Outer City Boundary (市界) vs Internal District Boundaries (区界)
xiamen_district_names = {"思明区", "湖里区", "集美区", "海沧区", "同安区", "翔安区"}
way_to_xm_districts = {}

for rel in relations:
    tags = rel.get("tags", {})
    dname = tags.get("name")
    if tags.get("boundary") == "administrative" and dname in xiamen_district_names:
        for m in rel.get("members", []):
            if m["type"] == "way" and m["ref"] in ways:
                w_obj = ways[m["ref"]]
                w_tags = w_obj.get("tags", {})
                if w_tags.get("maritime") == "yes" or w_tags.get("natural") == "coastline":
                    continue
                way_to_xm_districts.setdefault(m["ref"], set()).add(dname)

city_border_parts = []
district_border_parts = []

for wid, dset in way_to_xm_districts.items():
    pts = nodes_to_svg_pts(ways[wid].get("nodes", []), min_dist=0.8)
    if len(pts) < 2:
        continue
    d_str = pts_to_path_d(pts, close=False)
    if len(dset) >= 2:
        district_border_parts.append(d_str)
    else:
        city_border_parts.append(d_str)

svg_city_border_d = " ".join(city_border_parts)
svg_district_border_d = " ".join(district_border_parts)

district_colors_blue = {
    "思明区": "#f8f6ee",
    "湖里区": "#f3f0e6",
    "集美区": "#f6f3ea",
    "海沧区": "#f2efe5",
    "同安区": "#f7f5ed",
    "翔安区": "#f4f1e8",
}

district_tint_blue_els = []
for feat in districts_data["features"]:
    name = feat["properties"]["name"]
    geom = feat["geometry"]
    coords = geom["coordinates"]
    if geom["type"] == "Polygon":
        coords = [coords]
    d_parts = []
    for poly in coords:
        for ring in poly:
            pts = [lonlat_to_svg(pt[0], pt[1]) for pt in ring]
            if len(pts) >= 3:
                d_parts.append(pts_to_path_d(pts, close=True))
    d_joined = " ".join(d_parts)
    district_tint_blue_els.append(f'              <path d="{d_joined}" fill="{district_colors_blue.get(name, "#f6f4ec")}" />')

svg_district_tints_blue = "\n".join(district_tint_blue_els)

eco_zones = [
    {"lon": 117.926, "lat": 24.602, "rx": 46, "ry": 34, "rot": -15},
    {"lon": 118.015, "lat": 24.675, "rx": 55, "ry": 34, "rot": 20},
    {"lon": 118.135, "lat": 24.835, "rx": 78, "ry": 42, "rot": -10},
    {"lon": 118.235, "lat": 24.785, "rx": 48, "ry": 28, "rot": 15},
    {"lon": 118.122, "lat": 24.458, "rx": 30, "ry": 18, "rot": -12},
    {"lon": 118.084, "lat": 24.491, "rx": 11, "ry": 8, "rot": 15},
    {"lon": 118.118, "lat": 24.502, "rx": 16, "ry": 7, "rot": -8},
    {"lon": 118.040, "lat": 24.485, "rx": 15, "ry": 12, "rot": -20},
]
eco_svg_list = []
for ez in eco_zones:
    cx, cy = lonlat_to_svg(ez["lon"], ez["lat"])
    eco_svg_list.append(
        f'              <ellipse cx="{cx}" cy="{cy}" rx="{ez["rx"]}" ry="{ez["ry"]}" transform="rotate({ez["rot"]} {cx} {cy})" fill="#cde0b4" opacity="0.62"/>'
    )
svg_eco_str = "\n".join(eco_svg_list)

# District labels on main map (bilingual data-zh / data-en)
district_labels = [
    ("同 安 区", "TONG'AN", 118.135, 24.745, True),
    ("翔 安 区", "XIANG'AN", 118.285, 24.642, True),
    ("集 美 区", "JIMEI", 118.035, 24.622, True),
    ("海 沧 区", "HAICANG", 117.965, 24.515, True),
    ("湖 里 区", "HULI", 118.138, 24.532, True),
    ("思 明 区", "SIMING", 118.105, 24.448, True),
    ("金 门 岛", "Kinmen Island", 118.382, 24.452, False),
]

svg_labels_list = []
for zh_txt, en_txt, lon, lat, is_xm in district_labels:
    lx, ly = lonlat_to_svg(lon, lat)
    cls = "district-label xm-label" if is_xm else "district-label other-label"
    svg_labels_list.append(
        f'            <text x="{lx}" y="{ly}" class="{cls} i18n-svg-text" data-zh="{zh_txt}" data-en="{en_txt}">{zh_txt}</text>'
    )
svg_labels_str = "\n".join(svg_labels_list)

habitat_pin_colors = {
    "coastal": "#1565C0",
    "wetland": "#00838F",
    "forest": "#388E3C",
    "mountain": "#1B5E20",
}

habitat_pill_fills = {
    "coastal": "rgba(227, 242, 253, 0.95)",
    "wetland": "rgba(224, 247, 250, 0.95)",
    "forest": "rgba(232, 245, 233, 0.95)",
    "mountain": "rgba(215, 238, 217, 0.95)",
}

# Placement for the 9 markers on main map (zero overlap in both Chinese and English!)
label_placement_9 = {
    1: (-24, 5, "end"),     # ① 筼筜湖西堤纳潮闸口 (left towards western sea)
    2: (24, 5, "start"),    # ② 东坪山公园 (right)
    3: (24, 5, "start"),    # ③ 五通浦口 (right towards eastern sea)
    4: (-24, 5, "end"),     # ④ 虎头山公园 (left)
    5: (24, 5, "start"),    # ⑤ 天竺山森林公园 (right)
    6: (-24, 5, "end"),     # ⑥ 马銮湾 (left)
    7: (24, 5, "start"),    # ⑦ 杏林湾 (right)
    8: (24, 5, "start"),    # ⑧ 小坪森林公园 (right)
    9: (24, -5, "start"),   # ⑨ 欧厝-蔡厝滨海滩涂 (upper-right)
}

svg_markers_list = []
for s in SPOTS_1109:
    sx, sy = lonlat_to_svg(s["lon"], s["lat"])
    s["sx"], s["sy"] = sx, sy
    c = habitat_pin_colors.get(s["habitat_tag"], "#1565C0")
    pill_fill = habitat_pill_fills.get(s["habitat_tag"], "rgba(255, 255, 255, 0.94)")
    label_dx, label_dy, text_anchor = label_placement_9.get(s["id"], (24, 5, "start"))
    zh_short = s["short_zh"]
    en_short = s["short_en"]

    # Estimate initial pill width for Chinese text (approx 16.5px per CJK char + 18px padding)
    est_w = int(len(zh_short) * 16.8 + 18)
    pill_h = 26
    pill_y = -18.5
    if text_anchor == "end":
        pill_x = -est_w + 6
        txt_x = -3
    else:
        pill_x = -6
        txt_x = 3

    svg_markers_list.append(f'''            <g class="spot-marker" data-id="{s['id']}" tabindex="0" role="button" aria-label="{s['num']} {s['name_zh']}" onclick="selectSpot({s['id']})">
              <circle class="pulse-ring" cx="{sx}" cy="{sy}" r="26" fill="none" stroke="{c}" stroke-width="3.2"/>
              <circle class="pin-bg" cx="{sx}" cy="{sy}" r="20" fill="{c}" stroke="#ffffff" stroke-width="3.2"/>
              <text x="{sx}" y="{sy + 6.4}" text-anchor="middle" fill="#ffffff" font-size="18.5" font-weight="900" font-family="-apple-system, BlinkMacSystemFont, sans-serif">{s['id']}</text>
              <g class="pin-tag" data-anchor="{text_anchor}" transform="translate({sx + label_dx}, {sy + label_dy})">
                <rect class="pin-pill-bg" x="{pill_x}" y="{pill_y}" width="{est_w}" height="{pill_h}" rx="7" ry="7" fill="{pill_fill}" stroke="{c}" stroke-width="2.0"/>
                <text x="{txt_x}" y="0" text-anchor="{text_anchor}" fill="{c}" class="pin-label-text i18n-svg-text" data-zh="{zh_short}" data-en="{en_short}">{zh_short}</text>
              </g>
            </g>''')

svg_markers_str = "\n".join(svg_markers_list)

# Build Overview Satellite Tile Layer (exact Web Mercator z=11 grid aligned with SVG_W x SVG_H)
tx_min, tx_max = int(math.floor(x0_f)), int(math.floor(x1_f))
ty_min, ty_max = int(math.floor(y0_f)), int(math.floor(y1_f))
sat_tile_els = []
for ty in range(ty_min, ty_max + 1):
    for tx in range(tx_min, tx_max + 1):
        sx0, sy0 = tile_xy_to_svg(tx, ty)
        sx1, sy1 = tile_xy_to_svg(tx + 1, ty + 1)
        tw = round(sx1 - sx0 + 0.6, 2)
        th = round(sy1 - sy0 + 0.6, 2)
        t_url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{ty}/{tx}"
        sat_tile_els.append(
            f'            <image href="{t_url}" x="{round(sx0, 2)}" y="{round(sy0, 2)}" width="{tw}" height="{th}" preserveAspectRatio="none" />'
        )
svg_sat_tiles_str = "\n".join(sat_tile_els)

# Helper to stitch multi-way OSM relations (e.g. Xinglin Bay, Yundang Lake, Maluan Bay) into closed rings
def stitch_ways_into_rings(nlists):
    rings = []
    open_segs = []
    for nl in nlists:
        if len(nl) < 2:
            continue
        if nl[0] == nl[-1]:
            rings.append(nl)
        else:
            open_segs.append(list(nl))
    while open_segs:
        cur = open_segs.pop(0)
        changed = True
        while changed and cur[0] != cur[-1]:
            changed = False
            for i, seg in enumerate(open_segs):
                if cur[-1] == seg[0]:
                    cur.extend(seg[1:])
                    open_segs.pop(i)
                    changed = True
                    break
                elif cur[-1] == seg[-1]:
                    cur.extend(reversed(seg[:-1]))
                    open_segs.pop(i)
                    changed = True
                    break
                elif cur[0] == seg[-1]:
                    cur = seg[:-1] + cur
                    open_segs.pop(i)
                    changed = True
                    break
                elif cur[0] == seg[0]:
                    cur = list(reversed(seg[1:])) + cur
                    open_segs.pop(i)
                    changed = True
                    break
        if len(cur) >= 3:
            rings.append(cur)
    return rings

# Pre-stitch all OSM water relations into lon/lat rings
water_relation_rings_list = []
for rel in relations:
    if rel.get("tags", {}).get("natural") == "water":
        m_nlists = [
            ways[m["ref"]].get("nodes", [])
            for m in rel.get("members", [])
            if m["type"] == "way" and m["ref"] in ways and m.get("role") in ("outer", "inner", "")
        ]
        stitched = stitch_ways_into_rings(m_nlists)
        rel_rings = []
        for r_nids in stitched:
            pts = [nodes[nid] for nid in r_nids if nid in nodes]
            if len(pts) >= 3:
                rel_rings.append(pts)
        if rel_rings:
            water_relation_rings_list.append(rel_rings)


# Standard Sutherland-Hodgman polygon clipping against a rectangle (xmin, ymin, xmax, ymax)
def sutherland_hodgman_clip(poly, xmin, ymin, xmax, ymax):
    def clip_edge(pts, inside_fn, intersect_fn):
        if not pts:
            return []
        out = []
        s = pts[-1]
        for e in pts:
            if inside_fn(e):
                if not inside_fn(s):
                    out.append(intersect_fn(s, e))
                out.append(e)
            elif inside_fn(s):
                out.append(intersect_fn(s, e))
            s = e
        return out

    pts = list(poly)
    pts = clip_edge(pts, lambda p: p[0] >= xmin, lambda s, e: (xmin, s[1] + (e[1] - s[1]) * (xmin - s[0]) / (e[0] - s[0] if e[0] != s[0] else 1e-9)))
    pts = clip_edge(pts, lambda p: p[0] <= xmax, lambda s, e: (xmax, s[1] + (e[1] - s[1]) * (xmax - s[0]) / (e[0] - s[0] if e[0] != s[0] else 1e-9)))
    pts = clip_edge(pts, lambda p: p[1] >= ymin, lambda s, e: (s[0] + (e[0] - s[0]) * (ymin - s[1]) / (e[1] - s[1] if e[1] != s[1] else 1e-9), ymin))
    pts = clip_edge(pts, lambda p: p[1] <= ymax, lambda s, e: (s[0] + (e[0] - s[0]) * (ymax - s[1]) / (e[1] - s[1] if e[1] != s[1] else 1e-9), ymax))
    return [(round(p[0], 1), round(p[1], 1)) for p in pts]


# Build stylized Pure-SVG Local Guide Map for each of the 9 spots!
def build_local_spot_svg(spot):
    lm = spot["local_map"]
    w_lon, s_lat, e_lon, n_lat = lm["bbox"]
    dlon = e_lon - w_lon
    dlat = n_lat - s_lat
    LW, LH = 600, 400  # Exact 3:2 aspect ratio matching 1200x800 satellite guide map!
    BLEED = 18.0  # Bleed outside viewport so clipped polygon edges never show inside [0, LW] x [0, LH]

    def to_local(lon, lat):
        lx = (lon - w_lon) / dlon * LW
        ly = (n_lat - lat) / dlat * LH
        return round(lx, 1), round(ly, 1)

    def simplify_local(pts, min_d=1.4):
        if len(pts) < 2:
            return []
        out = [pts[0]]
        for p in pts[1:]:
            if (p[0] - out[-1][0])**2 + (p[1] - out[-1][1])**2 >= min_d * min_d:
                out.append(p)
        if out[-1] != pts[-1]:
            out.append(pts[-1])
        return out

    def clip_polyline(raw_pts):
        pad_x, pad_y = dlon * 0.08, dlat * 0.08
        segs = []
        cur = []
        for lon, lat in raw_pts:
            if (w_lon - pad_x) <= lon <= (e_lon + pad_x) and (s_lat - pad_y) <= lat <= (n_lat + pad_y):
                cur.append(to_local(lon, lat))
            else:
                if len(cur) >= 2:
                    segs.append(simplify_local(cur))
                cur = []
        if len(cur) >= 2:
            segs.append(simplify_local(cur))
        return [s for s in segs if len(s) >= 2]

    def clip_polygon_exact(raw_pts, min_span=3.5):
        if len(raw_pts) < 3:
            return []
        # Fast bbox reject in lon/lat
        lons = [p[0] for p in raw_pts]
        lats = [p[1] for p in raw_pts]
        if max(lons) < w_lon or min(lons) > e_lon or max(lats) < s_lat or min(lats) > n_lat:
            return []
        local_pts = [to_local(lon, lat) for lon, lat in raw_pts]
        clipped = sutherland_hodgman_clip(local_pts, -BLEED, -BLEED, LW + BLEED, LH + BLEED)
        simp = simplify_local(clipped, min_d=1.3)
        if len(simp) < 3:
            return []
        xs = [p[0] for p in simp]
        ys = [p[1] for p in simp]
        if (max(xs) - min(xs)) < min_span and (max(ys) - min(ys)) < min_span:
            return []
        return simp

    parts = []
    parts.append(f'<svg class="local-spot-svg" viewBox="0 0 {LW} {LH}" xmlns="http://www.w3.org/2000/svg">')
    parts.append('  <defs>')
    parts.append('    <linearGradient id="localLandGrad" x1="0%" y1="0%" x2="100%" y2="100%">')
    parts.append('      <stop offset="0%" stop-color="#f7f5ec"/>')
    parts.append('      <stop offset="100%" stop-color="#ede9dc"/>')
    parts.append('    </linearGradient>')
    parts.append('    <linearGradient id="localSeaGrad" x1="0%" y1="0%" x2="100%" y2="100%">')
    parts.append('      <stop offset="0%" stop-color="#9ed0ee"/>')
    parts.append('      <stop offset="100%" stop-color="#7fc0e6"/>')
    parts.append('    </linearGradient>')
    parts.append('    <filter id="localPinShadow" x="-20%" y="-20%" width="140%" height="140%">')
    parts.append('      <feDropShadow dx="0" dy="1.5" stdDeviation="1.8" flood-color="#102436" flood-opacity="0.28"/>')
    parts.append('    </filter>')
    parts.append('  </defs>')

    # Check if this spot's bbox intersects any real OSM coastline (skip Spot 9 where OSM coastline predates coastal reclamation)
    coast_segs_in_bbox = []
    if spot["id"] != 9:
        for w in ways.values():
            if w.get("tags", {}).get("natural") == "coastline":
                raw_pts = [nodes[nid] for nid in w.get("nodes", []) if nid in nodes]
                for seg in clip_polyline(raw_pts):
                    coast_segs_in_bbox.append(seg)

    if coast_segs_in_bbox:
        # Coastal spot: fill sea background first, then render exact clipped OSM land polygons!
        parts.append(f'  <rect width="{LW}" height="{LH}" fill="url(#localSeaGrad)"/>')
        land_d_list = []
        for lring in global_land_lonlat_rings:
            c_pts = clip_polygon_exact(lring, min_span=2.0)
            if len(c_pts) >= 3:
                land_d_list.append(pts_to_path_d(c_pts, close=True))
        if land_d_list:
            parts.append(f'  <path d="{" ".join(land_d_list)}" fill="url(#localLandGrad)" fill-rule="evenodd"/>')
    else:
        # Inland spot (or Spot 9 with exact satellite shoreline in water_areas): fill land background directly
        parts.append(f'  <rect width="{LW}" height="{LH}" fill="url(#localLandGrad)"/>')

    # Extract real OSM green polygons inside bbox (cleanly clipped outside viewport bleed, no artificial stroke)
    for w in extra_ways.values():
        tags = w.get("tags", {})
        nlist = w.get("nodes", [])
        if any(k in tags for k in ("leisure", "natural", "landuse")) and len(nlist) >= 4:
            raw_pts = [extra_nodes[nid] for nid in nlist if nid in extra_nodes]
            pts = clip_polygon_exact(raw_pts, min_span=5.0)
            if len(pts) >= 3:
                parts.append(f'  <path d="{pts_to_path_d(pts, close=True)}" fill="#c5e3c6" opacity="0.65"/>')

    # Extract real OSM water relations (Xinglin Bay + Garden Expo islands, Yundang Lake + islands, Maluan Bay)
    for rel_rings in water_relation_rings_list:
        rel_d_parts = []
        for r_pts in rel_rings:
            c_pts = clip_polygon_exact(r_pts, min_span=2.5)
            if len(c_pts) >= 3:
                rel_d_parts.append(pts_to_path_d(c_pts, close=True))
        if rel_d_parts:
            parts.append(f'  <path d="{" ".join(rel_d_parts)}" fill="#7cc3e8" stroke="#3b82ad" stroke-width="0.9" fill-rule="evenodd"/>')

    # Extract real closed OSM water ways inside bbox (skip Spot 3 where old OSM fishponds are now sand beach)
    if spot["id"] != 3:
        for w in ways.values():
            tags = w.get("tags", {})
            nlist = w.get("nodes", [])
            if tags.get("natural") == "water" and len(nlist) >= 4 and nlist[0] == nlist[-1]:
                raw_pts = [nodes[nid] for nid in nlist if nid in nodes]
                pts = clip_polygon_exact(raw_pts, min_span=3.0)
                if len(pts) >= 3:
                    parts.append(f'  <path d="{pts_to_path_d(pts, close=True)}" fill="#7cc3e8" stroke="#3b82ad" stroke-width="0.9"/>')

    # Render exact satellite-aligned water bodies for Spots 3, 5, 8, 9
    if spot["id"] in (3, 5, 8, 9):
        for wpoly in lm.get("water_areas", []):
            pts = clip_polygon_exact(wpoly, min_span=2.0)
            if len(pts) >= 3:
                parts.append(f'  <path d="{pts_to_path_d(pts, close=True)}" fill="#7cc3e8" stroke="#3b82ad" stroke-width="0.9"/>')

    # Crisp coastline stroke
    for seg in coast_segs_in_bbox:
        parts.append(f'  <path d="{pts_to_path_d(seg, close=False)}" fill="none" stroke="#3b82ad" stroke-width="1.4"/>')

    # Extract real OSM highways inside bbox (cleanly clipped)
    for w in extra_ways.values():
        tags = w.get("tags", {})
        if "highway" in tags:
            raw_pts = [extra_nodes[nid] for nid in w.get("nodes", []) if nid in extra_nodes]
            for seg in clip_polyline(raw_pts):
                d_str = pts_to_path_d(seg, close=False)
                parts.append(f'  <path d="{d_str}" fill="none" stroke="#e4c988" stroke-width="3.2" stroke-linecap="round" opacity="0.8"/>')
                parts.append(f'  <path d="{d_str}" fill="none" stroke="#fffdf7" stroke-width="1.4" stroke-linecap="round" opacity="0.85"/>')

    # Road name labels for major roads (no artificial red dashed lines)
    for rd in lm.get("roads", []):
        if rd.get("major"):
            pts = [to_local(p[0], p[1]) for p in rd["pts"]]
            mid = pts[len(pts) // 2]
            parts.append(
                f'  <text x="{mid[0]}" y="{mid[1] - 6}" text-anchor="middle" font-size="10.5" font-weight="700" fill="#5c4b28" stroke="#fffdf8" stroke-width="3" paint-order="stroke" class="i18n-svg-text" data-zh="{rd["zh"]}" data-en="{rd["en"]}">{rd["zh"]}</text>'
            )

    # Landmarks (Metro stations, peaks, water labels, parks)
    for lmk in lm.get("landmarks", []):
        lx, ly = to_local(lmk["lon"], lmk["lat"])
        ltype = lmk.get("type", "village")
        if ltype == "water":
            color = "#165c85"
            fsize = "12"
        elif ltype == "metro":
            color = "#1b4978"
            fsize = "11"
        elif ltype == "park" or ltype == "peak":
            color = "#235c3b"
            fsize = "11"
        else:
            color = "#4a555e"
            fsize = "10.5"
        parts.append(
            f'  <text x="{lx}" y="{ly}" text-anchor="middle" font-size="{fsize}" font-weight="700" fill="{color}" stroke="rgba(255,255,255,0.92)" stroke-width="3.2" paint-order="stroke" class="i18n-svg-text" data-zh="{lmk["zh"]}" data-en="{lmk["en"]}">{lmk["zh"]}</text>'
        )

    # Main Flag Marker (single clean label; enlarged to match subspot concentric ring scale)
    fl = lm["flag"]
    fx, fy = to_local(fl["lon"], fl["lat"])
    parts.append(f'  <g transform="translate({fx}, {fy})" filter="url(#localPinShadow)">')
    parts.append('    <text x="-4" y="7" text-anchor="start" font-size="22">🚩</text>')
    parts.append(
        f'    <text x="22" y="4" text-anchor="start" font-size="13.5" font-weight="800" fill="#183045" stroke="#ffffff" stroke-width="4.5" paint-order="stroke" class="i18n-svg-text" data-zh="{fl["zh"]}" data-en="{fl["en"]}">{fl["zh"]}</text>'
    )
    parts.append('  </g>')

    # Sub-spots (子观鸟点 - red target rings with high-contrast labels, aligned 1:1 with satellite guide map!)
    for idx, sub in enumerate(lm.get("subspots", []), 1):
        if "img_px" in sub and len(sub["img_px"]) == 2:
            sx, sy = round(sub["img_px"][0] / 2.0, 1), round(sub["img_px"][1] / 2.0, 1)
        else:
            sx, sy = to_local(sub["lon"], sub["lat"])
        dx = sub.get("dx", 14)
        dy = sub.get("dy", 5)
        anchor = sub.get("anchor", "start")
        parts.append(f'  <g class="subspot-group" transform="translate({sx}, {sy})" filter="url(#localPinShadow)">')
        parts.append('    <circle cx="0" cy="0" r="10.5" fill="rgba(217, 48, 37, 0.16)" stroke="#d93025" stroke-width="2.6"/>')
        parts.append('    <circle cx="0" cy="0" r="4" fill="#d93025" stroke="#ffffff" stroke-width="1.3"/>')
        parts.append(
            f'    <text x="{dx}" y="{dy}" text-anchor="{anchor}" font-size="12.5" font-weight="800" fill="#b31412" stroke="#fffef8" stroke-width="4.2" paint-order="stroke" class="i18n-svg-text" data-zh="{sub["zh"]}" data-en="{sub["en"]}">{sub["zh"]}</text>'
        )
        parts.append('  </g>')

    # Scale bar (bottom-left) & Mini Compass (top-right)
    scale_m = lm.get("scale_m", 200)
    parts.append(f'  <g transform="translate(16, {LH - 18})">')
    parts.append('    <rect x="-6" y="-16" width="84" height="22" rx="4" fill="rgba(255,255,255,0.85)" stroke="#b5cfe3" stroke-width="1"/>')
    parts.append('    <path d="M2,-3 L2,1 L52,1 L52,-3" fill="none" stroke="#183045" stroke-width="1.8"/>')
    parts.append(f'    <text x="27" y="-5" text-anchor="middle" font-size="10" font-weight="700" fill="#183045" class="i18n-svg-text" data-zh="{scale_m}米" data-en="{scale_m}m">{scale_m}米</text>')
    parts.append('  </g>')

    parts.append(f'  <g transform="translate({LW - 26}, 26)">')
    parts.append('    <circle cx="0" cy="0" r="14" fill="rgba(255,255,255,0.88)" stroke="#9bc0dc" stroke-width="1"/>')
    parts.append('    <polygon points="0,-10 -3.5,3 0,0 3.5,3" fill="#b5382a"/>')
    parts.append('    <text x="0" y="-10.5" text-anchor="middle" font-size="7" font-weight="800" fill="#183045">N</text>')
    parts.append('  </g>')

    parts.append('</svg>')
    return "\n".join(parts)

# Pre-build local SVG for each spot
for s in SPOTS_1109:
    s["local_svg"] = build_local_spot_svg(s)

def build_bilingual_page(default_lang="zh"):
    is_en = (default_lang == "en")
    html_lang = "en" if is_en else "zh-CN"
    page_title = INTRO_DATA["title_en"] if is_en else INTRO_DATA["title_zh"]

    return f'''<!DOCTYPE html>
<html lang="{html_lang}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=4.0, user-scalable=yes" />
  <title>{page_title}</title>
  <style>
    :root {{
      --page-bg: #edf4f9;
      --header-grad-top: #d6e8f5;
      --header-border: #b5cfe3;
      --card-bg: #ffffff;
      --ink-dark: #183045;
      --ink-muted: #4b657d;
      --sea-fill: url(#seaGradBlue);
      --accent-main: #1b6592;
      --accent-red: #b5382a;
      --border-color: #cbddec;
      --frame-border: #9bc0dc;
      --toolbar-border: #b0cce3;
      --thead-bg: #dfeef8;
      --row-hover: #f2f8fc;
      --chip-bg: #ebf5f0;
      --chip-text: #1f6349;
      --chip-border: #c0dfd0;
      --coast-stroke: #3b82ad;
      --water-fill: #72bfe6;
      --water-stroke: #469bc7;
      --city-border-color: #7d2626;
      --dist-border-color: #245d82;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }}
    body {{
      background-color: var(--page-bg);
      color: var(--ink-dark);
      font-family: "PingFang SC", "Hiragino Sans GB", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      line-height: 1.62;
      padding-bottom: 54px;
    }}

    .handbook-header {{
      max-width: 920px;
      margin: 0 auto;
      padding: 18px 18px 16px;
      border-bottom: 2px solid var(--header-border);
      background: linear-gradient(180deg, var(--header-grad-top) 0%, var(--page-bg) 100%);
    }}
    .badge-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 10px;
    }}
    .org-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--accent-main);
      color: #fff;
      font-size: 12.5px;
      font-weight: 600;
      padding: 4px 11px;
      border-radius: 6px;
      letter-spacing: 0.4px;
    }}
    .lang-switch {{
      display: inline-flex;
      background: #d7e7f4;
      border: 1px solid #9bc0dc;
      border-radius: 20px;
      padding: 2px;
      gap: 2px;
      flex-shrink: 0;
    }}
    .lang-btn {{
      border: none;
      background: transparent;
      color: var(--ink-muted);
      font-size: 12.5px;
      font-weight: 700;
      padding: 4px 12px;
      border-radius: 16px;
      cursor: pointer;
      transition: all 0.18s;
    }}
    .lang-btn.active {{
      background: var(--accent-main);
      color: #ffffff;
      box-shadow: 0 1px 4px rgba(27, 101, 146, 0.3);
    }}

    .handbook-title {{
      font-family: "Songti SC", "STSong", "Noto Serif SC", Georgia, serif;
      font-size: 25px;
      font-weight: 800;
      color: var(--ink-dark);
      letter-spacing: 0.8px;
      margin-bottom: 10px;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      margin-bottom: 12px;
    }}
    .stat-card {{
      background: rgba(255, 255, 255, 0.82);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 7px 10px;
      text-align: center;
    }}
    .stat-num {{
      font-size: 17px;
      font-weight: 800;
      color: var(--accent-main);
      line-height: 1.25;
    }}
    .stat-label {{
      font-size: 11.5px;
      color: var(--ink-muted);
      margin-top: 2px;
    }}
    .handbook-lead {{
      font-size: 13.8px;
      color: var(--ink-dark);
      opacity: 0.92;
      text-align: justify;
    }}
    .handbook-lead p + p {{
      margin-top: 6px;
    }}

    .map-section {{
      max-width: 920px;
      margin: 14px auto 0;
      padding: 0 14px;
    }}
    .map-frame {{
      position: relative;
      width: 100%;
      border: 2px solid var(--frame-border);
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 6px 20px rgba(30, 45, 55, 0.09);
      background: #ffffff;
    }}
    .map-canvas-wrap {{
      position: relative;
      width: 100%;
      overflow: hidden;
      background: #0d2336;
    }}
    .map-svg {{
      display: block;
      width: 100%;
      height: auto;
      user-select: none;
    }}

    /* Bottom-right Ping/Pong Map Mode Toggle Control */
    .map-pingpong-btn {{
      position: absolute;
      right: 12px;
      bottom: 12px;
      z-index: 18;
      display: inline-flex;
      align-items: center;
      gap: 2px;
      padding: 3px;
      border-radius: 22px;
      border: 1.5px solid rgba(27, 101, 146, 0.45);
      background: rgba(255, 255, 255, 0.93);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      box-shadow: 0 3px 12px rgba(15, 32, 48, 0.24);
      cursor: pointer;
      font-family: inherit;
      user-select: none;
      transition: transform 0.14s ease, box-shadow 0.14s ease;
    }}
    .map-pingpong-btn:hover {{
      transform: translateY(-1px);
      box-shadow: 0 5px 15px rgba(15, 32, 48, 0.3);
    }}
    .map-pingpong-btn:active {{
      transform: scale(0.97);
    }}
    .map-pingpong-btn .pp-opt {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      font-weight: 800;
      color: var(--ink-muted);
      padding: 4px 10px;
      border-radius: 18px;
      transition: all 0.18s ease;
      white-space: nowrap;
    }}
    .map-pingpong-btn .pp-opt.active {{
      background: var(--accent-main);
      color: #ffffff;
      box-shadow: 0 1px 4px rgba(27, 101, 146, 0.35);
    }}

    /* Satellite mode high-contrast overrides for Overview Map */
    .map-canvas-wrap.sat-mode #coastlineStrokePath {{
      stroke: rgba(145, 222, 255, 0.88);
      stroke-width: 1.35px;
    }}
    .map-canvas-wrap.sat-mode #cityBorderPath {{
      stroke: #ff6b5b;
    }}
    .map-canvas-wrap.sat-mode #distBorderPath {{
      stroke: #7ad3ff;
    }}
    .map-canvas-wrap.sat-mode .district-label.xm-label {{
      fill: #ffffff;
      stroke: rgba(12, 28, 44, 0.92);
      stroke-width: 4.5px;
    }}
    .map-canvas-wrap.sat-mode .district-label.other-label {{
      fill: rgba(245, 240, 228, 0.92);
      stroke: rgba(20, 30, 38, 0.88);
      stroke-width: 3.5px;
    }}

    #oceanBgRect {{ fill: var(--sea-fill); }}
    #coastlineStrokePath {{ stroke: var(--coast-stroke); }}
    #inlandWaterPath {{ fill: var(--water-fill); stroke: var(--water-stroke); }}
    #cityBorderPath {{ stroke: var(--city-border-color); }}
    #distBorderPath {{ stroke: var(--dist-border-color); }}

    .district-label {{
      font-family: "Songti SC", "STSong", Georgia, serif;
      font-weight: 800;
      text-anchor: middle;
      pointer-events: none;
      paint-order: stroke;
      stroke-linejoin: round;
    }}
    .district-label.xm-label {{
      font-size: 15.5px;
      fill: rgba(24, 54, 80, 0.82);
      stroke: rgba(255, 255, 255, 0.92);
      stroke-width: 4px;
      letter-spacing: 2.5px;
    }}
    .district-label.other-label {{
      font-size: 13.5px;
      fill: rgba(90, 84, 72, 0.58);
      stroke: rgba(245, 240, 228, 0.8);
      stroke-width: 3px;
      letter-spacing: 1.5px;
    }}

    .spot-marker {{ cursor: pointer; }}
    .spot-marker .pulse-ring {{
      opacity: 0;
      transform-origin: center;
      transform-box: fill-box;
    }}
    .spot-marker.active .pulse-ring {{
      opacity: 1;
      animation: pulseAnim 1.6s infinite ease-out;
    }}
    .spot-marker.active .pin-bg {{
      stroke: #ffdd57;
      stroke-width: 4.5px;
      r: 22px;
    }}
    .spot-marker.active .pin-pill-bg {{
      fill: #fffbeb;
      stroke-width: 2.8px;
    }}
    @keyframes pulseAnim {{
      0% {{ transform: scale(0.85); opacity: 0.95; }}
      100% {{ transform: scale(1.9); opacity: 0; }}
    }}
    .pin-label-text {{
      font-size: 16.5px;
      font-weight: 800;
      letter-spacing: 0.2px;
    }}

    .map-legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      padding: 9px 14px;
      background: rgba(255, 253, 248, 0.96);
      border-top: 1px solid var(--border-color);
      font-size: 12px;
      color: var(--ink-dark);
      align-items: center;
    }}
    .legend-item {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }}
    .legend-dot {{
      width: 11px;
      height: 11px;
      border-radius: 50%;
      display: inline-block;
    }}
    .legend-line-city {{
      width: 22px;
      border-top: 2.6px dashed var(--city-border-color);
      display: inline-block;
    }}
    .legend-line-dist {{
      width: 22px;
      border-top: 2px dashed var(--dist-border-color);
      display: inline-block;
    }}

    /* Table / List Section */
    .table-section {{
      max-width: 920px;
      margin: 18px auto 0;
      padding: 0 14px;
    }}
    .section-head {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 10px;
    }}
    .section-title {{
      font-family: "Songti SC", "STSong", Georgia, serif;
      font-size: 19px;
      font-weight: 800;
      color: var(--ink-dark);
    }}
    .filter-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .filter-pill {{
      border: 1px solid var(--toolbar-border);
      background: var(--card-bg);
      color: var(--ink-muted);
      font-size: 12px;
      font-weight: 600;
      padding: 4.5px 11px;
      border-radius: 16px;
      cursor: pointer;
    }}
    .filter-pill.active {{
      background: var(--accent-main);
      color: #fff;
      border-color: var(--accent-main);
    }}

    .table-card {{
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      overflow: hidden;
      box-shadow: 0 3px 10px rgba(0,0,0,0.04);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13.5px;
    }}
    thead {{
      background: var(--thead-bg);
      color: var(--ink-dark);
      text-align: left;
    }}
    th, td {{
      padding: 12px 14px;
      border-bottom: 1px solid var(--border-color);
      vertical-align: middle;
    }}
    tbody tr {{
      cursor: pointer;
      transition: background 0.15s;
    }}
    tbody tr:hover {{ background: var(--row-hover); }}
    tbody tr.active-row {{ background: #fff3d6; }}
    .num-badge {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 26px;
      height: 26px;
      border-radius: 50%;
      color: #fff;
      font-weight: 700;
      font-size: 12.5px;
    }}
    .spot-title-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }}
    .spot-link {{
      color: #1c4e63;
      font-weight: 700;
      font-size: 15px;
    }}
    .row-arrow {{
      color: var(--ink-muted);
      font-size: 17px;
      font-weight: 700;
      opacity: 0.45;
      flex-shrink: 0;
    }}
    .spot-submeta {{
      font-size: 12.5px;
      color: var(--ink-muted);
      margin-top: 3px;
    }}
    .mobile-birds-wrap {{
      display: none;
      margin-top: 7px;
    }}
    .bird-chip {{
      display: inline-block;
      background: var(--chip-bg);
      color: var(--chip-text);
      border: 1px solid var(--chip-border);
      border-radius: 4px;
      padding: 1.5px 7px;
      font-size: 12px;
      margin: 2px 4px 2px 0;
      white-space: nowrap;
    }}
    .bird-chip.highlight-chip {{
      background: #fff4e5;
      color: #9a3412;
      border-color: #f6cca2;
      font-weight: 600;
    }}

    @media (max-width: 680px) {{
      .handbook-title {{ font-size: 21px; }}
      .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
      thead {{ display: none; }}
      th.col-habitat, td.col-habitat,
      th.col-birds, td.col-birds {{
        display: none;
      }}
      td {{ padding: 13px 12px; }}
      td.col-num {{
        width: 42px;
        padding-right: 4px;
        vertical-align: top;
        padding-top: 15px;
      }}
      .mobile-birds-wrap {{ display: block; }}
    }}

    /* Detail Sheet Modal */
    .card-backdrop {{
      position: fixed;
      inset: 0;
      background: rgba(20, 28, 32, 0.48);
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.25s ease;
      z-index: 90;
    }}
    .card-backdrop.open {{
      opacity: 1;
      pointer-events: auto;
    }}
    .spot-sheet {{
      position: fixed;
      left: 50%;
      bottom: 0;
      transform: translate(-50%, 105%);
      width: 100%;
      max-width: 740px;
      max-height: 88vh;
      overflow-y: auto;
      background: var(--card-bg);
      border-top: 4px solid var(--accent-red);
      border-radius: 18px 18px 0 0;
      box-shadow: 0 -8px 30px rgba(0,0,0,0.24);
      padding: 18px 18px 28px;
      transition: transform 0.28s cubic-bezier(0.2, 0.9, 0.3, 1);
      z-index: 100;
    }}
    .spot-sheet.open {{
      transform: translate(-50%, 0);
    }}
    .sheet-header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
    }}
    .sheet-title-wrap {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .sheet-num {{
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: var(--accent-red);
      color: #fff;
      font-weight: 800;
      font-size: 16px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }}
    .sheet-title {{
      font-family: "Songti SC", "STSong", Georgia, serif;
      font-size: 19.5px;
      font-weight: 800;
      color: var(--ink-dark);
    }}
    .close-btn {{
      border: 1px solid var(--border-color);
      background: var(--page-bg);
      color: var(--ink-muted);
      width: 32px;
      height: 32px;
      border-radius: 50%;
      font-size: 18px;
      cursor: pointer;
      flex-shrink: 0;
    }}
    .meta-grid {{
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      margin-bottom: 12px;
    }}
    .meta-tag {{
      font-size: 12px;
      padding: 3.5px 9px;
      border-radius: 5px;
      background: var(--thead-bg);
      color: var(--ink-dark);
      font-weight: 600;
    }}

    /* Local Spot Guide Map Box (Vector + Satellite Ping/Pong) inside Sheet */
    .local-map-box {{
      border: 1.5px solid var(--frame-border);
      border-radius: 10px;
      overflow: hidden;
      background: #f7f5ec;
      margin-bottom: 12px;
    }}
    .local-map-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 7px 12px;
      background: #dfeef8;
      border-bottom: 1px solid var(--border-color);
      font-size: 12.5px;
      font-weight: 700;
      color: var(--ink-dark);
    }}
    .local-map-stage {{
      position: relative;
      width: 100%;
      aspect-ratio: 3 / 2;
      overflow: hidden;
      background: #102436;
    }}
    .local-spot-svg {{
      display: block;
      width: 100%;
      height: 100%;
    }}
    .local-sat-wrap {{
      position: relative;
      width: 100%;
      height: 100%;
    }}
    .local-sat-img {{
      display: block;
      width: 100%;
      height: 100%;
      object-fit: cover;
      user-select: none;
    }}
    .local-sat-overlay {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      display: block;
    }}
    .local-subspot-hit {{
      cursor: pointer;
      fill: rgba(217, 48, 37, 0.01);
      stroke: rgba(255, 255, 255, 0);
      stroke-width: 3px;
      transition: all 0.18s;
    }}
    .local-subspot-hit:hover {{
      fill: rgba(255, 221, 87, 0.28);
      stroke: #ffdd57;
    }}
    .local-map-stage .map-pingpong-btn {{
      right: 10px;
      bottom: 10px;
    }}
    .subspots-bar {{
      padding: 8px 11px;
      background: #f5f9fc;
      border-top: 1px solid var(--border-color);
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 6px;
    }}
    .subspot-nav-pill {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      font-weight: 600;
      color: #1b6592;
      background: #ffffff;
      border: 1px solid #a9cbe4;
      border-radius: 15px;
      padding: 3px 10px;
      text-decoration: none;
      transition: all 0.15s;
    }}
    .subspot-nav-pill:hover {{
      background: #1b6592;
      color: #ffffff;
    }}

    .sheet-desc {{
      font-size: 14px;
      color: var(--ink-dark);
      background: var(--page-bg);
      border-left: 3.5px solid var(--accent-main);
      padding: 10px 13px;
      border-radius: 0 8px 8px 0;
      margin-bottom: 12px;
      text-align: justify;
    }}
    .sheet-desc p + p {{ margin-top: 7px; }}

    .info-block {{
      font-size: 13px;
      color: var(--ink-dark);
      margin-bottom: 9px;
      background: #f8fbfd;
      border: 1px solid #d9e8f4;
      padding: 8px 11px;
      border-radius: 7px;
    }}
    .bird-group-row {{
      margin-bottom: 7px;
    }}
    .bird-group-label {{
      font-size: 12.5px;
      font-weight: 700;
      color: var(--ink-muted);
      margin-right: 6px;
    }}
    .sheet-tips {{
      font-size: 13px;
      color: #5b4628;
      background: #fff6e0;
      border: 1px dashed #dfbe78;
      padding: 9px 12px;
      border-radius: 7px;
      margin-top: 10px;
    }}
    .sheet-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }}
    .btn-primary, .btn-amap {{
      flex: 1;
      min-width: 140px;
      text-align: center;
      padding: 11px 14px;
      border-radius: 8px;
      font-size: 13.5px;
      font-weight: 700;
      text-decoration: none;
      cursor: pointer;
      border: none;
    }}
    .btn-primary {{ background: #1b6592; color: #ffffff; }}
    .btn-amap {{ background: #2d6a4f; color: #ffffff; }}

    /* Editorial Credits Footer */
    .credits-section {{
      max-width: 920px;
      margin: 22px auto 0;
      padding: 0 14px;
    }}
    .credits-card {{
      background: linear-gradient(180deg, #f7fbfe 0%, #ffffff 100%);
      border: 1px solid var(--border-color);
      border-top: 3px solid var(--accent-main);
      border-radius: 10px;
      padding: 16px 18px 14px;
      box-shadow: 0 3px 10px rgba(24, 48, 69, 0.04);
    }}
    .credits-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px;
      padding-bottom: 10px;
      margin-bottom: 12px;
      border-bottom: 1px dashed var(--border-color);
    }}
    .credits-title {{
      font-family: "Songti SC", "STSong", Georgia, serif;
      font-size: 15px;
      font-weight: 800;
      color: var(--ink-dark);
      letter-spacing: 0.5px;
    }}
    .credits-sub {{
      font-size: 12px;
      color: var(--ink-muted);
    }}
    .credits-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
    }}
    .credit-group {{
      background: rgba(237, 244, 249, 0.65);
      border: 1px solid #d7e7f4;
      border-radius: 8px;
      padding: 10px 12px;
    }}
    .credit-role {{
      font-size: 12px;
      font-weight: 700;
      color: var(--ink-muted);
      margin-bottom: 7px;
      display: flex;
      align-items: center;
      gap: 5px;
    }}
    .credit-people {{
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
    }}
    .author-pill {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      background: #ffffff;
      border: 1px solid #c5dced;
      border-radius: 6px;
      padding: 3.5px 9px;
      font-size: 13px;
      color: var(--ink-dark);
      box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }}
    .author-name {{
      font-weight: 700;
    }}
    .author-nick {{
      font-size: 11.5px;
      font-weight: 600;
      color: #1f6349;
      background: #ebf5f0;
      border: 1px solid #c0dfd0;
      border-radius: 4px;
      padding: 0.5px 6px;
    }}
    @media (max-width: 680px) {{
      .credits-grid {{
        grid-template-columns: 1fr;
        gap: 8px;
      }}
    }}
  </style>
</head>
<body>

  <header class="handbook-header">
    <div class="badge-row">
      <span class="org-badge" id="orgBadgeText"></span>
      <div class="lang-switch" role="tablist" aria-label="Language Switch">
        <button class="lang-btn" id="btnLangZh" onclick="setLanguage('zh')">中文</button>
        <button class="lang-btn" id="btnLangEn" onclick="setLanguage('en')">EN</button>
      </div>
    </div>
    <h1 class="handbook-title" id="mainTitleText"></h1>
    <div class="stats-grid" id="statsGrid"></div>
    <div class="handbook-lead" id="introLead"></div>
  </header>

  <main id="mainOverview">
    <section class="map-section">
      <div class="map-frame">
        <div class="map-canvas-wrap" id="overviewCanvasWrap">
          <svg id="xiamenMapSvg" class="map-svg" viewBox="0 0 {SVG_W} {SVG_H}" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <filter id="softShadow" x="-10%" y="-10%" width="120%" height="120%">
                <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#1b2620" flood-opacity="0.22"/>
              </filter>
              <linearGradient id="seaGradBlue" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#add8f2"/>
                <stop offset="50%" stop-color="#94c9ea"/>
                <stop offset="100%" stop-color="#7ebae2"/>
              </linearGradient>
              <path id="exactLandPath" d="{svg_exact_land_d}" fill-rule="evenodd"/>
              <clipPath id="exactLandClip">
                <use href="#exactLandPath"/>
              </clipPath>
            </defs>

            <rect id="oceanBgRect" width="{SVG_W}" height="{SVG_H}" />

            <g id="pureVectorBaseLayer">
              <use id="surroundingLandUse" href="#exactLandPath" fill="#e2dfd5" />
              <g id="blueLandGroup" clip-path="url(#exactLandClip)">
{svg_district_tints_blue}
{svg_eco_str}
                <path d="{svg_real_green_d}" fill="#bedfc0" opacity="0.72" fill-rule="evenodd" />
              </g>
              <path id="majorRoadsPath" d="{svg_real_roads_d}" fill="none" stroke="#dfd5c0" stroke-width="1.0" opacity="0.65" pointer-events="none"/>
              <path id="inlandWaterPath" d="{svg_exact_water_d}" stroke-width="0.45" fill-rule="evenodd" />
            </g>

            <g id="overviewSatLayer" style="display:none">
{svg_sat_tiles_str}
            </g>

            <g id="crispCoastAndBordersLayer" pointer-events="none">
              <path id="coastlineStrokePath" d="{svg_exact_coast_d}" fill="none" stroke-width="1.05" stroke-linejoin="round" />
              <path d="{svg_district_border_d}" fill="none" stroke="#fffdf7" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round" opacity="0.88" />
              <path id="distBorderPath" d="{svg_district_border_d}" fill="none" stroke-width="1.8" stroke-dasharray="6,4" stroke-linecap="round" stroke-linejoin="round" />
              <path d="{svg_city_border_d}" fill="none" stroke="#fffdf7" stroke-width="4.8" stroke-linecap="round" stroke-linejoin="round" opacity="0.92" />
              <path id="cityBorderPath" d="{svg_city_border_d}" fill="none" stroke-width="2.6" stroke-dasharray="10,4,2,4" stroke-linecap="round" stroke-linejoin="round" />
{svg_labels_str}
            </g>

            <g id="markersLayer" filter="url(#softShadow)">
{svg_markers_str}
            </g>

            <g transform="translate({SVG_W - 52}, 52)" pointer-events="none">
              <circle cx="0" cy="0" r="22" fill="rgba(255,253,248,0.9)" stroke="#b5a88b" stroke-width="1.2"/>
              <polygon points="0,-16 -5,4 0,0 5,4" fill="#b5382a"/>
              <polygon points="0,14 -4,-2 0,0 4,-2" fill="#7c857e"/>
              <text x="0" y="-18" text-anchor="middle" font-size="9" font-weight="700" fill="#2b312c">N</text>
            </g>
          </svg>

          <button type="button" class="map-pingpong-btn" id="btnOverviewPingPong" onclick="toggleOverviewMapMode()" aria-label="切换简图或卫星图"></button>
        </div>

        <div class="map-legend" id="mapLegend"></div>
      </div>
    </section>

    <section class="table-section">
      <div class="section-head">
        <h2 class="section-title" id="tableSectionTitle"></h2>
        <div class="filter-pills" id="filterPills"></div>
      </div>

      <div class="table-card">
        <table>
          <thead>
            <tr id="tableHeadRow"></tr>
          </thead>
          <tbody id="spotsTableBody"></tbody>
        </table>
      </div>
    </section>

    <section class="credits-section" id="creditsSection"></section>
  </main>

  <div id="cardBackdrop" class="card-backdrop" onclick="closeCard()"></div>
  <aside id="spotSheet" class="spot-sheet" aria-live="polite"></aside>

  <script>
    const INTRO = {json.dumps(INTRO_DATA, ensure_ascii=False)};
    const SPOTS = {json.dumps(SPOTS_1109, ensure_ascii=False)};
    const PIN_COLORS = {json.dumps(habitat_pin_colors, ensure_ascii=False)};

    let currentLang = '{default_lang}';
    const urlLang = new URLSearchParams(window.location.search).get('lang');
    if (urlLang === 'en' || urlLang === 'zh') {{
      currentLang = urlLang;
    }}

    let currentFilter = 'all';
    let currentOpenSpotId = null;
    let overviewMapMode = 'vector'; // 'vector' | 'sat'
    let localMapMode = 'vector';    // 'vector' | 'sat'

    const UI_TEXT = {{
      zh: {{
        tableTitle: '📋 厦门九大观鸟点导览（五大区域）',
        filters: [
          {{ key: 'all', label: '全部 (9)' }},
          {{ key: 'island', label: '厦门岛（思明·湖里）' }},
          {{ key: 'haicang', label: '海沧区' }},
          {{ key: 'jimei', label: '集美区' }},
          {{ key: 'tongan', label: '同安区' }},
          {{ key: 'xiangan', label: '翔安区' }}
        ],
        thNum: '编号',
        thSpot: '观鸟点',
        thHabitat: '生境与最佳月份',
        thBirds: '代表及高光鸟种',
        legendCity: '厦门市界',
        legendDist: '区级边界',
        legendWetland: '湖泊/海湾湿地',
        legendCoastal: '滨海滩涂/沙滩',
        legendForest: '城市山林公园',
        legendMountain: '高山森林/水库',
        localMapTitle: '🗺️ 单点局部导览图（含子观鸟点）',
        subspotsNavLabel: '📍 子观鸟点一键导航：',
        labelDuration: '⏱️ 建议时长：',
        labelMonths: '📅 最佳月份：',
        labelTransport: '🚌 交通方式：',
        labelDifficulty: '🥾 难度系数：',
        labelTip: '💡 观鸟提示：',
        btnTencent: '🧭 腾讯地图导航 (微信推荐)',
        btnAmap: '🗺️ 高德地图导航',
        ppVector: '🗺️ 简图',
        ppSat: '🛰️ 卫星图'
      }},
      en: {{
        tableTitle: '📋 9 Birding Hotspots in Xiamen (5 Areas)',
        filters: [
          {{ key: 'all', label: 'All (9)' }},
          {{ key: 'island', label: 'Xiamen Island (Siming & Huli)' }},
          {{ key: 'haicang', label: 'Haicang' }},
          {{ key: 'jimei', label: 'Jimei' }},
          {{ key: 'tongan', label: "Tong'an" }},
          {{ key: 'xiangan', label: "Xiang'an" }}
        ],
        thNum: 'No.',
        thSpot: 'Birding Hotspot',
        thHabitat: 'Habitat & Best Months',
        thBirds: 'Key & Notable Birds',
        legendCity: 'City Boundary',
        legendDist: 'District Boundary',
        legendWetland: 'Lake / Bay Wetland',
        legendCoastal: 'Coastal Mudflats',
        legendForest: 'Urban Forest Park',
        legendMountain: 'Mountain Forest',
        localMapTitle: '🗺️ Local Spot Guide Map & Sub-sites',
        subspotsNavLabel: '📍 Navigate to Sub-sites:',
        labelDuration: '⏱️ Duration: ',
        labelMonths: '📅 Best Months: ',
        labelTransport: '🚌 Getting There: ',
        labelDifficulty: '🥾 Difficulty: ',
        labelTip: '💡 Birding Tip: ',
        btnTencent: '🧭 Tencent Maps (WeChat)',
        btnAmap: '🗺️ Amap Navigation',
        ppVector: '🗺️ Vector',
        ppSat: '🛰️ Satellite'
      }}
    }};

    function buildPingPongInnerHtml(mode) {{
      const t = UI_TEXT[currentLang];
      const isSat = (mode === 'sat');
      return `
        <span class="pp-opt ${{!isSat ? 'active' : ''}}">${{t.ppVector}}</span>
        <span class="pp-opt ${{isSat ? 'active' : ''}}">${{t.ppSat}}</span>
      `;
    }}

    function syncOverviewMapModeUI() {{
      const isSat = (overviewMapMode === 'sat');
      const vecLayer = document.getElementById('pureVectorBaseLayer');
      const satLayer = document.getElementById('overviewSatLayer');
      const wrap = document.getElementById('overviewCanvasWrap');
      const btn = document.getElementById('btnOverviewPingPong');
      if (vecLayer) vecLayer.style.display = isSat ? 'none' : '';
      if (satLayer) satLayer.style.display = isSat ? '' : 'none';
      if (wrap) wrap.classList.toggle('sat-mode', isSat);
      if (btn) btn.innerHTML = buildPingPongInnerHtml(overviewMapMode);
    }}

    function toggleOverviewMapMode() {{
      overviewMapMode = (overviewMapMode === 'vector') ? 'sat' : 'vector';
      syncOverviewMapModeUI();
    }}

    function syncLocalMapModeUI() {{
      const isSat = (localMapMode === 'sat');
      const vecBox = document.getElementById('localSvgContainer');
      const satBox = document.getElementById('localSatContainer');
      const btn = document.getElementById('btnLocalPingPong');
      if (vecBox) vecBox.style.display = isSat ? 'none' : 'block';
      if (satBox) satBox.style.display = isSat ? 'block' : 'none';
      if (btn) btn.innerHTML = buildPingPongInnerHtml(localMapMode);
      if (!isSat && vecBox) {{
        applySvgLanguage(vecBox);
      }}
    }}

    function toggleLocalMapMode() {{
      localMapMode = (localMapMode === 'vector') ? 'sat' : 'vector';
      syncLocalMapModeUI();
    }}

    function applySvgLanguage(rootEl) {{
      if (!rootEl) return;
      rootEl.querySelectorAll('.i18n-svg-text').forEach(el => {{
        const val = el.getAttribute(currentLang === 'en' ? 'data-en' : 'data-zh');
        if (val) el.textContent = val;
      }});
      rootEl.querySelectorAll('.pin-tag').forEach(tag => {{
        const txt = tag.querySelector('.pin-label-text');
        const rect = tag.querySelector('.pin-pill-bg');
        if (txt && rect) {{
          try {{
            const bbox = txt.getBBox();
            if (bbox.width > 0) {{
              const padX = 16;
              const w = Math.ceil(bbox.width + padX);
              const anchor = tag.getAttribute('data-anchor') || 'start';
              rect.setAttribute('width', w);
              if (anchor === 'end') {{
                rect.setAttribute('x', -(w - 5));
              }} else {{
                rect.setAttribute('x', -5);
              }}
            }}
          }} catch (e) {{}}
        }}
      }});
    }}

    function renderHeaderAndLegend() {{
      const isEn = (currentLang === 'en');
      document.documentElement.lang = isEn ? 'en' : 'zh-CN';
      document.title = isEn ? INTRO.title_en : INTRO.title_zh;

      document.getElementById('btnLangZh').classList.toggle('active', !isEn);
      document.getElementById('btnLangEn').classList.toggle('active', isEn);

      document.getElementById('orgBadgeText').textContent = isEn ? INTRO.org_en : INTRO.org_zh;
      document.getElementById('mainTitleText').textContent = isEn ? INTRO.title_en : INTRO.title_zh;

      const stats = isEn ? INTRO.stats_en : INTRO.stats_zh;
      document.getElementById('statsGrid').innerHTML = stats.map(st => `
        <div class="stat-card">
          <div class="stat-num">${{st.num}}</div>
          <div class="stat-label">${{st.label}}</div>
        </div>
      `).join('');

      const paras = isEn ? INTRO.paragraphs_en : INTRO.paragraphs_zh;
      document.getElementById('introLead').innerHTML = paras.map(p => `<p>${{p}}</p>`).join('');

      const t = UI_TEXT[currentLang];
      document.getElementById('mapLegend').innerHTML = `
        <span class="legend-item"><i class="legend-line-city"></i> <strong>${{t.legendCity}}</strong></span>
        <span class="legend-item"><i class="legend-line-dist"></i> <strong>${{t.legendDist}}</strong></span>
        <span class="legend-item"><i class="legend-dot" style="background:#1565C0"></i> ${{t.legendCoastal}}</span>
        <span class="legend-item"><i class="legend-dot" style="background:#00838F"></i> ${{t.legendWetland}}</span>
        <span class="legend-item"><i class="legend-dot" style="background:#388E3C"></i> ${{t.legendForest}}</span>
        <span class="legend-item"><i class="legend-dot" style="background:#1B5E20"></i> ${{t.legendMountain}}</span>
      `;

      document.getElementById('tableSectionTitle').textContent = t.tableTitle;
      document.getElementById('filterPills').innerHTML = t.filters.map(f => `
        <button class="filter-pill ${{currentFilter === f.key ? 'active' : ''}}" onclick="filterTable('${{f.key}}')">${{f.label}}</button>
      `).join('');

      document.getElementById('tableHeadRow').innerHTML = `
        <th style="width:54px">${{t.thNum}}</th>
        <th>${{t.thSpot}}</th>
        <th class="col-habitat" style="width:190px">${{t.thHabitat}}</th>
        <th class="col-birds" style="width:270px">${{t.thBirds}}</th>
      `;

      document.getElementById('creditsSection').innerHTML = isEn ? `
        <div class="credits-card">
          <div class="credits-header">
            <span class="credits-title">🐦 Credits & Editorial Team · Xiamen BirdWatching Society</span>
            <span class="credits-sub">Please keep a safe distance and watch birds quietly</span>
          </div>
          <div class="credits-grid">
            <div class="credit-group">
              <div class="credit-role">🗺️ Map Production</div>
              <div class="credit-people">
                <span class="author-pill"><span class="author-name">Liu Jie (刘杰)</span><span class="author-nick">猫行天下</span></span>
              </div>
            </div>
            <div class="credit-group">
              <div class="credit-role">✍️ Text & Guide</div>
              <div class="credit-people">
                <span class="author-pill"><span class="author-name">Chen Yuhan (陈雨晗)</span><span class="author-nick">Hans</span></span>
                <span class="author-pill"><span class="author-name">Li Xiang (李享)</span><span class="author-nick">无足之鸟</span></span>
              </div>
            </div>
            <div class="credit-group">
              <div class="credit-role">🔍 Proofreading & Review</div>
              <div class="credit-people">
                <span class="author-pill"><span class="author-name">Chen Yuesheng (陈跃生)</span><span class="author-nick">林鸮</span></span>
                <span class="author-pill"><span class="author-name">Liu Xin (刘昕)</span><span class="author-nick">流小星</span></span>
                <span class="author-pill"><span class="author-name">Chen Zhihong (陈志鸿)</span><span class="author-nick">岩鹭</span></span>
              </div>
            </div>
          </div>
        </div>
      ` : `
        <div class="credits-card">
          <div class="credits-header">
            <span class="credits-title">🐦 厦门全域观鸟地图 · 创作与编校团队</span>
            <span class="credits-sub">厦门市观鸟协会 出品 · 保持安全距离，文明安静观鸟</span>
          </div>
          <div class="credits-grid">
            <div class="credit-group">
              <div class="credit-role">🗺️ 地图制作</div>
              <div class="credit-people">
                <span class="author-pill"><span class="author-name">刘杰</span><span class="author-nick">猫行天下</span></span>
              </div>
            </div>
            <div class="credit-group">
              <div class="credit-role">✍️ 文字介绍</div>
              <div class="credit-people">
                <span class="author-pill"><span class="author-name">陈雨晗</span><span class="author-nick">Hans</span></span>
                <span class="author-pill"><span class="author-name">李享</span><span class="author-nick">无足之鸟</span></span>
              </div>
            </div>
            <div class="credit-group">
              <div class="credit-role">🔍 校对审核</div>
              <div class="credit-people">
                <span class="author-pill"><span class="author-name">陈跃生</span><span class="author-nick">林鸮</span></span>
                <span class="author-pill"><span class="author-name">刘昕</span><span class="author-nick">流小星</span></span>
                <span class="author-pill"><span class="author-name">陈志鸿</span><span class="author-nick">岩鹭</span></span>
              </div>
            </div>
          </div>
        </div>
      `;

      syncOverviewMapModeUI();
      applySvgLanguage(document.getElementById('xiamenMapSvg'));
    }}

    function renderTable() {{
      const isEn = (currentLang === 'en');
      const tbody = document.getElementById('spotsTableBody');
      const filtered = currentFilter === 'all'
        ? SPOTS
        : SPOTS.filter(s => s.area_key === currentFilter);

      tbody.innerHTML = filtered.map(s => {{
        const c = PIN_COLORS[s.habitat_tag] || '#b5382a';
        const name = isEn ? s.name_en : s.name_zh;
        const dist = isEn ? s.district_en : s.district_zh;
        const summary = isEn ? s.summary_en : s.summary_zh;
        const hab = isEn ? s.habitat_en : s.habitat_zh;
        const months = isEn ? s.months_en : s.months_zh;
        const birds = isEn ? s.key_birds_en : s.key_birds_zh;
        const birdsHtml = birds.map(b => `<span class="bird-chip">${{b}}</span>`).join('');

        return `
          <tr id="row-${{s.id}}" class="${{currentOpenSpotId === s.id ? 'active-row' : ''}}" onclick="selectSpot(${{s.id}})">
            <td class="col-num"><span class="num-badge" style="background:${{c}}">${{s.id}}</span></td>
            <td>
              <div class="spot-title-row">
                <span class="spot-link">${{name}}</span>
                <span class="row-arrow">›</span>
              </div>
              <div class="spot-submeta">${{dist}} · ${{s.difficulty_stars}} · ${{summary}}</div>
              <div class="mobile-birds-wrap">${{birdsHtml}}</div>
            </td>
            <td class="col-habitat" style="font-size:12.5px;color:var(--ink-muted)">
              <div style="font-weight:600;color:var(--ink-dark)">${{hab}}</div>
              <div style="margin-top:2px">${{months}}</div>
            </td>
            <td class="col-birds">${{birdsHtml}}</td>
          </tr>
        `;
      }}).join('');
    }}

    function filterTable(key) {{
      currentFilter = key;
      renderHeaderAndLegend();
      renderTable();
    }}

    function selectSpot(id) {{
      const spot = SPOTS.find(s => s.id === id);
      if (!spot) return;
      currentOpenSpotId = id;
      const isEn = (currentLang === 'en');
      const t = UI_TEXT[currentLang];

      document.querySelectorAll('.spot-marker').forEach(m => {{
        m.classList.toggle('active', Number(m.dataset.id) === id);
      }});
      document.querySelectorAll('#spotsTableBody tr').forEach(r => {{
        r.classList.toggle('active-row', r.id === `row-${{id}}`);
      }});

      const c = PIN_COLORS[spot.habitat_tag] || '#b5382a';
      const name = isEn ? spot.name_en : spot.name_zh;
      const dist = isEn ? spot.district_en : spot.district_zh;
      const hab = isEn ? spot.habitat_en : spot.habitat_zh;
      const dur = isEn ? spot.duration_en : spot.duration_zh;
      const months = isEn ? spot.months_en : spot.months_zh;
      const descList = isEn ? spot.desc_en : spot.desc_zh;
      const transport = isEn ? spot.transport_en : spot.transport_zh;
      const diff = isEn ? spot.difficulty_en : spot.difficulty_zh;
      const groups = isEn ? spot.bird_groups_en : spot.bird_groups_zh;
      const tips = isEn ? spot.tips_en : spot.tips_zh;

      const subspots = spot.local_map.subspots || [];
      const subspotsNavHtml = subspots.map(sub => {{
        const subName = isEn ? sub.en : sub.zh;
        const navUrl = `https://apis.map.qq.com/uri/v1/marker?marker=coord:${{sub.gcj_lat}},${{sub.gcj_lon}};title:${{encodeURIComponent(name + ' - ' + subName)}};addr:${{encodeURIComponent('厦门市' + spot.district_zh)}}&referer=xmbirds`;
        return `<a class="subspot-nav-pill" href="${{navUrl}}" target="_blank" rel="noopener">⭕ ${{subName}} ↗</a>`;
      }}).join('');

      const satImgSrc = `assets_1110/spot_${{spot.id}}_${{isEn ? 'en' : 'zh'}}.png`;
      const satHitsHtml = subspots.map(sub => {{
        if (!sub.img_px) return '';
        const subName = isEn ? sub.en : sub.zh;
        const navUrl = `https://apis.map.qq.com/uri/v1/marker?marker=coord:${{sub.gcj_lat}},${{sub.gcj_lon}};title:${{encodeURIComponent(name + ' - ' + subName)}};addr:${{encodeURIComponent('厦门市' + spot.district_zh)}}&referer=xmbirds`;
        return `<a href="${{navUrl}}" target="_blank" rel="noopener"><circle class="local-subspot-hit" cx="${{sub.img_px[0]}}" cy="${{sub.img_px[1]}}" r="32"><title>${{subName}}</title></circle></a>`;
      }}).join('');

      const groupsHtml = groups.map(g => {{
        const chipCls = g.highlight ? 'bird-chip highlight-chip' : 'bird-chip';
        const chips = g.items.map(item => `<span class="${{chipCls}}">${{item}}</span>`).join('');
        return `<div class="bird-group-row"><span class="bird-group-label">${{g.label}}:</span>${{chips}}</div>`;
      }}).join('');

      const qqNavUrl = `https://apis.map.qq.com/uri/v1/marker?marker=coord:${{spot.gcj_lat}},${{spot.gcj_lon}};title:${{encodeURIComponent(name)}};addr:${{encodeURIComponent('厦门市' + spot.district_zh)}}&referer=xmbirds`;
      const amapNavUrl = `https://uri.amap.com/marker?position=${{spot.gcj_lon}},${{spot.gcj_lat}}&name=${{encodeURIComponent(name)}}`;

      const sheet = document.getElementById('spotSheet');
      sheet.style.borderTopColor = c;
      sheet.innerHTML = `
        <div class="sheet-header">
          <div class="sheet-title-wrap">
            <span class="sheet-num" style="background:${{c}}">${{spot.id}}</span>
            <div>
              <h3 class="sheet-title">${{name}}</h3>
              <span style="font-size:12.5px;color:var(--ink-muted)">${{dist}} · ${{hab}}</span>
            </div>
          </div>
          <button class="close-btn" onclick="closeCard()" aria-label="Close">×</button>
        </div>

        <div class="meta-grid">
          <span class="meta-tag">${{t.labelDuration}}${{dur}}</span>
          <span class="meta-tag">${{t.labelMonths}}${{months}}</span>
        </div>

        <div class="local-map-box">
          <div class="local-map-header">
            <span>${{t.localMapTitle}}</span>
            <span style="font-size:11.5px;color:var(--ink-muted)">${{spot.lon.toFixed(4)}}°E, ${{spot.lat.toFixed(4)}}°N</span>
          </div>
          <div class="local-map-stage">
            <div id="localSvgContainer" style="width:100%;height:100%">${{spot.local_svg}}</div>
            <div id="localSatContainer" class="local-sat-wrap" style="display:none">
              <img class="local-sat-img" src="${{satImgSrc}}" alt="${{name}}" loading="lazy" />
              <svg class="local-sat-overlay" viewBox="0 0 1200 800" xmlns="http://www.w3.org/2000/svg">
                ${{satHitsHtml}}
              </svg>
            </div>
            <button type="button" class="map-pingpong-btn" id="btnLocalPingPong" onclick="toggleLocalMapMode()" aria-label="切换简图或卫星图"></button>
          </div>
          <div class="subspots-bar">
            <span style="font-size:12px;font-weight:700;color:var(--ink-muted)">${{t.subspotsNavLabel}}</span>
            ${{subspotsNavHtml}}
          </div>
        </div>

        <div class="sheet-desc">
          ${{descList.map(p => `<p>${{p}}</p>`).join('')}}
        </div>

        <div class="info-block"><strong>${{t.labelTransport}}</strong>${{transport}}</div>
        <div class="info-block"><strong>${{t.labelDifficulty}}</strong>${{diff}}</div>

        <div style="margin-top:10px">${{groupsHtml}}</div>

        <div class="sheet-tips"><strong>${{t.labelTip}}</strong>${{tips}}</div>

        <div class="sheet-actions">
          <a class="btn-primary" href="${{qqNavUrl}}" target="_blank" rel="noopener">${{t.btnTencent}}</a>
          <a class="btn-amap" href="${{amapNavUrl}}" target="_blank" rel="noopener">${{t.btnAmap}}</a>
        </div>
      `;

      syncLocalMapModeUI();
      applySvgLanguage(document.getElementById('localSvgContainer'));
      document.getElementById('cardBackdrop').classList.add('open');
      sheet.classList.add('open');
    }}

    function closeCard() {{
      currentOpenSpotId = null;
      document.getElementById('cardBackdrop').classList.remove('open');
      document.getElementById('spotSheet').classList.remove('open');
    }}

    function setLanguage(lang) {{
      currentLang = lang;
      renderHeaderAndLegend();
      renderTable();
      if (currentOpenSpotId !== null) {{
        selectSpot(currentOpenSpotId);
      }}
    }}

    renderHeaderAndLegend();
    renderTable();
  </script>
</body>
</html>
'''

for fname, dlang in [("index3.html", "zh"), ("index3cn.html", "zh"), ("index3en.html", "en")]:
    out_p = os.path.join(OUT_DIR, fname)
    with open(out_p, "w", encoding="utf-8") as f:
        f.write(build_bilingual_page(dlang))
    print(f"Generated {out_p} ({os.path.getsize(out_p)} bytes, default={dlang})")
