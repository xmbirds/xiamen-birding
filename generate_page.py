import json
import math
import os
import subprocess
import urllib.request

OUT_DIR = "/Users/libo/xmbirds/birdspoint"
TILE_DIR = os.path.join(OUT_DIR, "tiles")
os.makedirs(TILE_DIR, exist_ok=True)

CARTO_KEY = os.environ.get("CARTO_API_KEY", "")

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

tx0, ty0 = int(math.floor(x0_f)), int(math.floor(y0_f))
tx1, ty1 = int(math.floor(x1_f)), int(math.floor(y1_f))

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

# 1. Download authentic Carto Voyager (@2x high-res with API key, zero watermark!) + Esri Relief/Topo tiles
carto_tile_elements = []
relief_tile_elements = []
topo_tile_elements = []

for ty in range(ty0, ty1 + 1):
    for tx in range(tx0, tx1 + 1):
        # Carto Voyager No-Labels @2x with API Key
        carto_png = os.path.join(TILE_DIR, f"carto_{z}_{tx}_{ty}.png")
        carto_jpg_name = f"carto_{z}_{tx}_{ty}.jpg"
        carto_jpg = os.path.join(TILE_DIR, carto_jpg_name)
        if not os.path.exists(carto_jpg):
            url = f"https://basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{tx}/{ty}@2x.png?key={CARTO_KEY}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                with open(carto_png, "wb") as out:
                    out.write(r.read())
            subprocess.run(
                ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "82", carto_png, "--out", carto_jpg],
                check=True, stdout=subprocess.DEVNULL
            )
            if os.path.exists(carto_png):
                os.remove(carto_png)

        relief_name = f"relief_{z}_{tx}_{ty}.jpg"
        topo_name = f"topo_{z}_{tx}_{ty}.jpg"

        sx0, sy0 = tile_xy_to_svg(tx, ty)
        sx1, sy1 = tile_xy_to_svg(tx + 1, ty + 1)
        w = sx1 - sx0 + 0.6
        h = sy1 - sy0 + 0.6

        carto_tile_elements.append(
            f'              <image href="tiles/{carto_jpg_name}" x="{sx0:.1f}" y="{sy0:.1f}" width="{w:.1f}" height="{h:.1f}" preserveAspectRatio="none"/>'
        )
        relief_tile_elements.append(
            f'              <image href="tiles/{relief_name}" x="{sx0:.1f}" y="{sy0:.1f}" width="{w:.1f}" height="{h:.1f}" preserveAspectRatio="none"/>'
        )
        topo_tile_elements.append(
            f'              <image href="tiles/{topo_name}" x="{sx0:.1f}" y="{sy0:.1f}" width="{w:.1f}" height="{h:.1f}" preserveAspectRatio="none"/>'
        )

svg_carto_tiles_str = "\n".join(carto_tile_elements)
svg_relief_tiles_str = "\n".join(relief_tile_elements)
svg_topo_tiles_str = "\n".join(topo_tile_elements)

# 2. Parse OSM nodes and ways
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

# 3. Stitch high-precision OSM coastline
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

for chain in open_chains:
    pts = nodes_to_svg_pts(chain, min_dist=0.55)
    if len(pts) < 3:
        continue
    coastline_stroke_parts.append(pts_to_path_d(pts, close=False))
    p0 = nodes[chain[0]]
    p1 = nodes[chain[-1]]
    if p0[0] < 118.00 and p1[0] > 118.40:
        closed_pts = pts + [(SVG_W + 30, pts[-1][1]), (SVG_W + 30, -30), (-30, -30), (-30, pts[0][1])]
        land_path_parts.append(pts_to_path_d(closed_pts, close=True))
    elif p0[0] > 118.40 and p1[1] < 24.41:
        closed_pts = pts + [(pts[-1][0], SVG_H + 30), (SVG_W + 30, SVG_H + 30), (SVG_W + 30, pts[0][1])]
        land_path_parts.append(pts_to_path_d(closed_pts, close=True))
    elif p0[0] < 118.08 and p1[0] < 118.08 and p0[1] < 24.43:
        closed_pts = pts + [(-30, pts[-1][1]), (-30, SVG_H + 30), (pts[0][0], SVG_H + 30)]
        land_path_parts.append(pts_to_path_d(closed_pts, close=True))

for ring in closed_rings:
    pts = nodes_to_svg_pts(ring, min_dist=0.5)
    if len(pts) >= 3:
        d_str = pts_to_path_d(pts, close=True)
        land_path_parts.append(d_str)
        coastline_stroke_parts.append(d_str)

svg_exact_land_d = " ".join(land_path_parts)
svg_exact_coast_d = " ".join(coastline_stroke_parts)

# 4. Real inland water bodies
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

# 5. Real Forest / Park polygons & Major Highways/Bridges
real_green_parts = []
real_road_parts = []
if osm_extra:
    extra_nodes = {el["id"]: (el["lon"], el["lat"]) for el in osm_extra["elements"] if el["type"] == "node"}
    extra_ways = {el["id"]: el for el in osm_extra["elements"] if el["type"] == "way"}
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

# 6. Separate Xiamen Outer City Boundary (市界) vs Internal District Boundaries (区界)
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

district_colors_warm = {
    "思明区": "#f9f1dc",
    "湖里区": "#f4ead2",
    "集美区": "#f7f0de",
    "海沧区": "#f2ebd8",
    "同安区": "#f8f3e4",
    "翔安区": "#f4ede0",
}
district_colors_blue = {
    "思明区": "#f8f6ee",
    "湖里区": "#f3f0e6",
    "集美区": "#f6f3ea",
    "海沧区": "#f2efe5",
    "同安区": "#f7f5ed",
    "翔安区": "#f4f1e8",
}

district_tint_warm_els = []
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
    district_tint_warm_els.append(f'              <path d="{d_joined}" fill="{district_colors_warm.get(name, "#f6f1e2")}" />')
    district_tint_blue_els.append(f'              <path d="{d_joined}" fill="{district_colors_blue.get(name, "#f6f4ec")}" />')

svg_district_tints_warm = "\n".join(district_tint_warm_els)
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

# 12 curated Xiamen Birding Hotspots
bird_spots = [
    {
        "id": 1,
        "num": "①",
        "name": "五缘湾湿地公园（栗喉蜂虎保护区）",
        "district": "湖里区",
        "habitat": "河口湿地 / 沙崖林地",
        "habitat_tag": "wetland",
        "lon": 118.1685,
        "lat": 24.5215,
        "season": "4月—9月（夏候鸟繁殖季）、10月—3月（冬候鸟）",
        "birds": ["栗喉蜂虎", "白胸翡翠", "黄苇鳽", "黑水鸡", "红嘴蓝鹊", "褐翅鸦鹃"],
        "summary": "厦门最著名的城市湿地观鸟点，设有专门的栗喉蜂虎沙崖繁殖保护区与迷宫栈道。",
        "detail": "本区位于厦门本岛东北角的五缘湾核心区，生态环境涵盖红树林潮间带、淡水芦苇塘、睡莲池及人工营建的沙质土崖。每年4月中旬至9月，上百只被誉为「中国最美小鸟」的栗喉蜂虎在此掘洞繁殖；骑马山亲水栈道及湿地迷宫周边则常见黄苇鳽、黑水鸡、白胸翡翠及多种林鸟，非常适合公众科普与摄影。",
        "tips": "地铁2号线「五缘湾站」或「湿地公园站」步行可达；拍摄蜂虎建议上午顺光时段前往骑马山观鸟台。"
    },
    {
        "id": 2,
        "num": "②",
        "name": "筼筜湖及白鹭洲公园（西堤闸口）",
        "district": "思明区",
        "habitat": "城市泻湖 / 红树林",
        "habitat_tag": "wetland",
        "lon": 118.0882,
        "lat": 24.4795,
        "season": "全年皆宜（11月—3月普通鸬鹚越冬大群）",
        "birds": ["白鹭", "大白鹭", "夜鹭", "普通鸬鹚", "普通翠鸟", "苍鹭", "黑腹滨鹬"],
        "summary": "厦门城市中心「客厅」，西堤闸口纳潮放水时万鸟翔集，冬季数千只鸬鹚在此栖息。",
        "detail": "筼筜湖为厦门岛内最大的海水泻湖，湖心生态岛种植有大片红树林，是市鸟白鹭、夜鹭与池鹭的核心夜栖地。西堤海水纳潮闸口每天随潮汐开闸换水时，大量鱼虾涌入，吸引成群白鹭、大白鹭低空掠水捕食；每年冬季更有上千只普通鸬鹚列队飞越湖面，场面蔚为壮观。",
        "tips": "关注筼筜湖纳潮排涝开闸时间，在西堤咖啡一条街旁的闸口桥上观赏距离最近。"
    },
    {
        "id": 3,
        "num": "③",
        "name": "东坪山公园及万石植物园",
        "district": "思明区",
        "habitat": "常绿阔叶林 / 溪谷",
        "habitat_tag": "forest",
        "lon": 118.1175,
        "lat": 24.4580,
        "season": "全年（春秋季迁徙林鸟、冬季太阳鸟盛花期）",
        "birds": ["叉尾太阳鸟", "白鹇", "赤红山椒鸟", "黑领噪鹛", "紫啸鸫", "橙腹叶鹎", "发冠卷尾"],
        "summary": "岛内最大山林绿肺，蝶谷至梅海岭一带林木茂密，是观察留鸟与林鸟的绝佳路线。",
        "detail": "位于厦门岛南部山体核心，连接万石植物园与东坪山社。沿东山水库、蝶谷步道漫步，溪涧潺潺、次生阔叶林保存完好。冬季美丽异木棉与炮仗花盛开时，极易近距离观察叉尾太阳鸟、暗绿绣眼鸟与朱背啄花鸟；密林深处常有国家二级保护鸟类白鹇及成群赤红山椒鸟活动。",
        "tips": "建议清晨6:30—9:30沿东坪山路—蝶谷步道慢行，携带双筒望远镜搜索树冠层。"
    },
    {
        "id": 4,
        "num": "④",
        "name": "狐尾山公园（海上明珠至气象台步道）",
        "district": "思明区",
        "habitat": "城市丘陵密林",
        "habitat_tag": "forest",
        "lon": 118.0845,
        "lat": 24.4912,
        "season": "4月—5月、9月—10月（候鸟过境黄金驿站）",
        "birds": ["仙八色鸫", "寿带", "紫寿带", "白腹鸫", "灰背鸫", "北红尾鸲", "白眉姬鹟"],
        "summary": "春秋季迁徙林鸟跨海后进入厦门岛的重要落脚点，常有罕见地面鸫类与八色鸫记录。",
        "detail": "狐尾山紧邻西海域，山体幽静、乔灌草层次丰富，是东亚—澳大利西亚迁徙通道上林鸟过境厦门本岛的第一站。每年4—5月春迁与9—10月秋迁期间，山腰背风湿润的林下沟谷常有仙八色鸫、日本歌鸲、白眉姬鹟、紫寿带及多种柳莺、鸫类停歇补给。",
        "tips": "山海健康步道狐尾山段交通便利，观察地面隐秘鸟类时请保持安静、切勿追逐惊扰。"
    },
    {
        "id": 5,
        "num": "⑤",
        "name": "虎头山公园",
        "district": "湖里区",
        "habitat": "疏林草地 / 次生林",
        "habitat_tag": "forest",
        "lon": 118.1320,
        "lat": 24.5085,
        "season": "10月—次年4月（迁徙季与越冬期）",
        "birds": ["黄眉柳莺", "红胁蓝尾鸲", "铜蓝鹟", "斑姬啄木鸟", "灰背鸫", "乌鸫"],
        "summary": "被厦门鸟友称为「迁徙林鸟魔术盒」，小巧精致却屡出珍稀过境鸟种记录。",
        "detail": "位于湖里区中心地带的低矮山体公园，因周边高楼环绕形成独特的「城市绿岛效应」，过境候鸟极易在此集中停歇。公园内落叶树与常绿树混交，林缘开阔、视线极佳，每年秋冬季节鸫类、鹟类、柳莺及鹀类密度极高，非常适合新老鸟友开展日常巡山。",
        "tips": "可从公园南门或东门进入，重点留心半山亭周边的灌木丛与松林。"
    },
    {
        "id": 6,
        "num": "⑥",
        "name": "厦门园博苑（杏林湾湿地及生态岛）",
        "district": "集美区",
        "habitat": "大型淡水湾 / 芦苇洲岛",
        "habitat_tag": "wetland",
        "lon": 118.0615,
        "lat": 24.5780,
        "season": "10月—次年4月（冬候鸟水禽高峰期）",
        "birds": ["紫水鸡", "普通鸬鹚", "凤头潜鸭", "琵嘴鸭", "反嘴鹬", "黑翅长脚鹬", "骨顶鸡"],
        "summary": "杏林湾广阔水域与生态小岛交织，是观察最美水鸟「紫水鸡」与越冬野鸭的核心区。",
        "detail": "园博苑坐落于集美杏林湾，水域面积逾数千亩，湾内保留有多座原生态芦苇湿地岛屿。在水生植物繁茂的浅滩边缘，常年栖息着羽色绚丽的紫水鸡家族；入冬后，开阔水面聚集大批凤头潜鸭、赤颈鸭、琵嘴鸭，以及上千只在此夜栖的普通鸬鹚。",
        "tips": "地铁1号线「园博苑站」直达；推荐租借园区自行车或步行前往民族风情园北侧水岸及杏林湾绿道观察。"
    },
    {
        "id": 7,
        "num": "⑦",
        "name": "集美灌口坂头水库及双岭",
        "district": "集美区",
        "habitat": "山地水库 / 农田溪流",
        "habitat_tag": "mountain",
        "lon": 117.9920,
        "lat": 24.6420,
        "season": "全年（春秋季猛禽过境、冬季山林留鸟）",
        "birds": ["蛇雕", "林雕", "凤头鹰", "灰脸鵟鹰", "小鸊鷉", "山鹡鸰", "红尾水鸲"],
        "summary": "依傍西北部连绵群山与坂头水库，生境原始多样，猛禽与山涧溪鸟资源极为丰富。",
        "detail": "本区位于集美西北部山区，涵盖坂头水库、石兜水库上游溪流及双岭农林交错带。晴朗上午气流上升时，常可见蛇雕、凤头鹰甚至林雕在山脊上空盘旋鸣叫；溪谷乱石间易见红尾水鸲、白顶溪鸲与翠鸟，田野疏林中则有山鹡鸰、棕背伯劳与多种山雀。",
        "tips": "适合自驾或结伴包车前往，建议携带高倍双筒或单筒望远镜观察高空盘旋猛禽。"
    },
    {
        "id": 8,
        "num": "⑧",
        "name": "天竺山国家森林公园",
        "district": "海沧区",
        "habitat": "深山阔叶林 / 幽谷溪流",
        "habitat_tag": "mountain",
        "lon": 117.9260,
        "lat": 24.5950,
        "season": "全年皆宜（春季繁殖鸟鸣最盛）",
        "birds": ["红头咬鹃", "斑头鸺鹠", "灰树鹊", "栗背短脚鹎", "黑短脚鹎", "发冠卷尾", "画眉"],
        "summary": "厦门西部森林覆盖率最高的山林秘境，两二湖与百竹园一带可邂逅红头咬鹃等深山林鸟。",
        "detail": "天竺山素有「厦门后花园」之称，森林覆盖率超96%，内有天竺湖、皓月湖、两二湖及多条原始峡谷步道。高大乔木与藤本植物为典型森林鸟类提供了绝佳庇护，不仅能听到斑头鸺鹠、领角鸮的叫声，更有机会偶遇羽色艳丽的红头咬鹃、赤红山椒鸟、灰树鹊及成群短脚鹎混合鸟浪。",
        "tips": "地铁2号线终点站「天竺山站」直达；推荐从东线四季花谷或西线两二湖步道徒步观鸟。"
    },
    {
        "id": 9,
        "num": "⑨",
        "name": "大屏山郊野公园及海沧湾岸线",
        "district": "海沧区",
        "habitat": "滨海山地 / 潮间带红树林",
        "habitat_tag": "coastal",
        "lon": 118.0410,
        "lat": 24.4820,
        "season": "9月—次年4月",
        "birds": ["黑鸢", "游隼", "蓝矶鸫", "黄足鹬", "白腰杓鹬", "褐柳莺", "暗绿绣眼鸟"],
        "summary": "山海相接，既可在山顶看黑鸢乘海风滑翔，又能在海沧湾退潮滩涂观察鸻鹬与鹭类。",
        "detail": "大屏山雄踞海沧大桥西引桥畔，与厦门本岛隔海相望。山体步道视野开阔，常有黑鸢、红隼及游隼利用海风地形气流悬停巡弋；山脚下的海沧湾公园沿海滩涂及红树林带，在退潮时裸露出大片泥滩，吸引白腰杓鹬、青脚鹬、矶鹬及各类鹭鸟觅食。",
        "tips": "可在海沧湾公园地铁站出站后沿海岸步道观察，再登大屏山俯瞰西海域全景。"
    },
    {
        "id": 10,
        "num": "⑩",
        "name": "大嶝岛（阳塘滩涂与东侧鱼塘区）",
        "district": "翔安区",
        "habitat": "沿海潮间带 / 鱼塭养殖池",
        "habitat_tag": "coastal",
        "lon": 118.3180,
        "lat": 24.5680,
        "season": "9月—次年5月（迁徙鸻鹬与越冬水鸟巅峰）",
        "birds": ["黑脸琵鹭", "勺嘴鹬", "黑腹滨鹬", "红颈滨鹬", "环颈鸻", "铁嘴沙鸻", "红嘴巨鸥"],
        "summary": "与金门慈湖仅一水之隔！咸淡水交接的滩涂与鱼塘是厦门鸻鹬类与珍稀水鸟的王牌鸟点。",
        "detail": "本区与金门本岛西北侧的慈湖赏鸟区隔海相望，共享同一片海域生态圈。生态环境完全由沿海牡蛎滩涂、河口泥滩、高潮位鱼塭养殖池及农耕旱地组成。退潮时在阳塘外侧滩涂可见数以千计的滨鹬、沙鸻群飞如浪；涨潮时水鸟退入内侧干涸或浅水鱼塘停歇，常有黑脸琵鹭、白琵鹭、红嘴巨鸥乃至极危物种勺嘴鹬现身！",
        "tips": "务必提前查询厦门潮汐表！最佳观鸟时机为「大潮涨潮前后2小时」（水鸟被潮水推近岸边或转入内侧鱼塘），必备单筒望远镜。"
    },
    {
        "id": 11,
        "num": "⑪",
        "name": "翔安九溪口及张埭桥水库片区",
        "district": "翔安区",
        "habitat": "河口湿地 / 农耕旱地",
        "habitat_tag": "coastal",
        "lon": 118.2480,
        "lat": 24.6360,
        "season": "10月—次年4月",
        "birds": ["灰头麦鸡", "金眶鸻", "黑翅长脚鹬", "红胸田鸡", "栗耳鹀", "红隼", "黑卷尾"],
        "summary": "翔安母亲河九溪入海口与周边的农田、水库交错，鸻鹬、麦鸡与农田鹀类十分活跃。",
        "detail": "九溪流域自北向南汇入翔安湾，形成了咸淡水交汇的河口沙洲、溪岸芦苇丛及周边广阔的花生与蔬菜农耕地。秋冬季节，干涸菜地与浅水洼地中常聚集数十只灰头麦鸡、金眶鸻与扇尾沙锥；高压线塔与田间木桩上则常见红隼、黑翅鸢及棕背伯劳驻守。",
        "tips": "片区视野开阔、遮蔽较少，建议以车代步作为移动掩体，避免下车惊飞近岸水鸟。"
    },
    {
        "id": 12,
        "num": "⑫",
        "name": "同安汀溪水库及小坪森林公园",
        "district": "同安区",
        "habitat": "大型山谷水库 / 高山阔叶林",
        "habitat_tag": "mountain",
        "lon": 118.1250,
        "lat": 24.8120,
        "season": "全年（冬季水库鸳鸯、春季高山林鸟）",
        "birds": ["鸳鸯", "普通秋沙鸭", "灰林鵖", "蓝喉蜂虎", "白额燕尾", "橙背鸦雀", "领鸺鹠"],
        "summary": "厦门北部群山环抱的生态水源地，冬季有野生鸳鸯越冬，山林溪涧常见燕尾与高山林鸟。",
        "detail": "汀溪水库位于同安区西北部群山之中，水质清冽、库湾幽深，沿岸人迹罕至，每年冬季均有野生鸳鸯群、绿翅鸭等在此越冬。继续向北登临海拔较高的小坪森林公园与莲花山脉，茶园、竹海与天然次生林交织，夏季有蓝喉蜂虎繁殖，山涧溪流中则常有白额燕尾、斑背燕尾与河乌的身影。",
        "tips": "距离岛内约1小时车程，可串联汀溪水库观景台与小坪森林公园一日生态观鸟游。"
    }
]

for spot in bird_spots:
    sx, sy = lonlat_to_svg(spot["lon"], spot["lat"])
    spot["sx"] = sx
    spot["sy"] = sy

district_labels = [
    ("同 安 区", 118.135, 24.735, "xm"),
    ("翔 安 区", 118.275, 24.675, "xm"),
    ("集 美 区", 118.035, 24.605, "xm"),
    ("海 沧 区", 117.975, 24.530, "xm"),
    ("湖 里 区", 118.135, 24.532, "xm"),
    ("思 明 区", 118.148, 24.472, "xm"),
    ("金 门 岛", 118.380, 24.455, "other"),
]
svg_labels_str = "\n".join([
    f'            <text x="{lonlat_to_svg(lon, lat)[0]}" y="{lonlat_to_svg(lon, lat)[1]}" class="district-label {"xm-label" if kind=="xm" else "other-label"}">{name}</text>'
    for name, lon, lat, kind in district_labels
])

routes = [
    [(118.155, 24.518), (118.1685, 24.5215), (118.179, 24.528)],
    [(118.098, 24.455), (118.1175, 24.4580), (118.138, 24.465)],
    [(118.295, 24.562), (118.3180, 24.5680), (118.342, 24.558)],
    [(117.915, 24.580), (117.9260, 24.5950), (117.938, 24.612)],
]
svg_routes_str = ""
for r_pts in routes:
    pts_str = " ".join([f"{lonlat_to_svg(p[0], p[1])[0]},{lonlat_to_svg(p[0], p[1])[1]}" for p in r_pts])
    svg_routes_str += f'            <polyline points="{pts_str}" fill="none" stroke="#b5382a" stroke-width="2.8" stroke-linecap="round" stroke-dasharray="1,6" class="bird-route"/>\n'

habitat_pin_colors = {
    "wetland": "#1565C0",
    "forest": "#388E3C",
    "mountain": "#1B5E20",
    "coastal": "#1565C0",
}

label_placement = {
    1: (16, 4, "start"),
    2: (16, 8, "start"),
    3: (0, 23, "middle"),
    4: (-15, -5, "end"),
    5: (16, 4, "start"),
    6: (-16, 4, "end"),
    7: (16, 4, "start"),
    8: (16, 4, "start"),
    9: (-16, 5, "end"),
    10: (16, 4, "start"),
    11: (16, 4, "start"),
    12: (16, 4, "start"),
}

svg_markers_list = []
for s in bird_spots:
    c = habitat_pin_colors.get(s["habitat_tag"], "#b5382a")
    sx, sy = s["sx"], s["sy"]
    label_dx, label_dy, text_anchor = label_placement.get(s["id"], (16, 4, "start"))
    short_name = s["name"].split("（")[0]

    svg_markers_list.append(f'''            <g class="spot-marker" data-id="{s['id']}" tabindex="0" role="button" aria-label="{s['num']} {s['name']}" onclick="selectSpot({s['id']})">
              <circle class="pulse-ring" cx="{sx}" cy="{sy}" r="19" fill="none" stroke="{c}" stroke-width="2.6"/>
              <circle class="pin-bg" cx="{sx}" cy="{sy}" r="13.5" fill="{c}" stroke="#fffdf7" stroke-width="2.2"/>
              <text x="{sx}" y="{sy + 4.5}" text-anchor="middle" fill="#ffffff" font-size="13" font-weight="700" font-family="-apple-system, sans-serif">{s['id']}</text>
              <g class="pin-tag" transform="translate({sx + label_dx}, {sy + label_dy})">
                <text x="0" y="0" text-anchor="{text_anchor}" class="pin-label-stroke">{short_name}</text>
                <text x="0" y="0" text-anchor="{text_anchor}" fill="{c}" class="pin-label-text">{short_name}</text>
              </g>
            </g>''')

svg_markers_str = "\n".join(svg_markers_list)

def build_html(theme="blue"):
    if theme == "blue":
        root_vars = """      --page-bg: #edf4f9;
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
      --dist-border-color: #245d82;"""
        xm_label_fill = "rgba(24, 54, 80, 0.8)"
        xm_label_stroke = "rgba(255, 255, 255, 0.92)"
        surrounding_land_fill = "#e2dfd5"
        district_tints_svg = svg_district_tints_blue
        real_green_fill = "#bedfc0"
        real_green_opacity = "0.72"
    else:
        root_vars = """      --page-bg: #f6f2e6;
      --header-grad-top: #ede6d3;
      --header-border: #c9bea5;
      --card-bg: #fffdf8;
      --ink-dark: #2b312c;
      --ink-muted: #5e665f;
      --sea-fill: #cbe3ee;
      --accent-main: #2d6a4f;
      --accent-red: #b5382a;
      --border-color: #dcd3be;
      --frame-border: #c5b89b;
      --toolbar-border: #cbbd9f;
      --thead-bg: #eae2cf;
      --row-hover: #f5efe0;
      --chip-bg: #eef4eb;
      --chip-text: #2d5a40;
      --chip-border: #cbe0c3;
      --coast-stroke: #6293a8;
      --water-fill: #9fd0e3;
      --water-stroke: #76b2c9;
      --city-border-color: #8b2626;
      --dist-border-color: #355245;"""
        xm_label_fill = "rgba(58, 46, 33, 0.78)"
        xm_label_stroke = "rgba(255, 253, 246, 0.9)"
        surrounding_land_fill = "#e5dfd0"
        district_tints_svg = svg_district_tints_warm
        real_green_fill = "#c5dfb8"
        real_green_opacity = "0.62"

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=4.0, user-scalable=yes" />
  <title>厦门全域观鸟地图 · 厦门市观鸟协会导览</title>
  <style>
    :root {{
{root_vars}
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }}
    body {{
      background-color: var(--page-bg);
      color: var(--ink-dark);
      font-family: "PingFang SC", "Hiragino Sans GB", "Noto Serif SC", "Microsoft YaHei", sans-serif;
      line-height: 1.6;
      padding-bottom: 48px;
    }}

    .handbook-header {{
      max-width: 900px;
      margin: 0 auto;
      padding: 20px 18px 14px;
      border-bottom: 2px solid var(--header-border);
      background: linear-gradient(180deg, var(--header-grad-top) 0%, var(--page-bg) 100%);
    }}
    .badge-row {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 8px;
    }}
    .org-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--accent-main);
      color: #fff;
      font-size: 12px;
      font-weight: 600;
      padding: 3.5px 11px;
      border-radius: 5px;
      letter-spacing: 0.5px;
    }}
    .handbook-title {{
      font-family: "Songti SC", "STSong", "Noto Serif SC", serif;
      font-size: 26px;
      font-weight: 800;
      color: var(--ink-dark);
      letter-spacing: 1.5px;
      margin-bottom: 8px;
    }}
    .handbook-lead {{
      font-size: 14px;
      color: var(--ink-dark);
      opacity: 0.9;
      text-align: justify;
    }}

    .map-section {{
      max-width: 900px;
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
    }}
    .map-svg {{
      display: block;
      width: 100%;
      height: auto;
      user-select: none;
    }}

    #oceanBgRect {{
      fill: var(--sea-fill);
    }}
    #coastlineStrokePath {{
      stroke: var(--coast-stroke);
    }}
    #inlandWaterPath {{
      fill: var(--water-fill);
      stroke: var(--water-stroke);
    }}
    #cityBorderPath {{
      stroke: var(--city-border-color);
    }}
    #distBorderPath {{
      stroke: var(--dist-border-color);
    }}

    .district-label {{
      font-family: "Songti SC", "STSong", serif;
      font-weight: 800;
      text-anchor: middle;
      pointer-events: none;
      paint-order: stroke;
      stroke-linejoin: round;
    }}
    .district-label.xm-label {{
      font-size: 16.5px;
      fill: {xm_label_fill};
      stroke: {xm_label_stroke};
      stroke-width: 4px;
      letter-spacing: 3.5px;
    }}
    .district-label.other-label {{
      font-size: 14px;
      fill: rgba(90, 84, 72, 0.55);
      stroke: rgba(245, 240, 228, 0.78);
      stroke-width: 3px;
      letter-spacing: 2px;
    }}

    .spot-marker {{
      cursor: pointer;
    }}
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
      stroke-width: 3.8px;
      r: 15px;
    }}
    @keyframes pulseAnim {{
      0% {{ transform: scale(0.85); opacity: 0.95; }}
      100% {{ transform: scale(1.9); opacity: 0; }}
    }}
    .pin-label-stroke {{
      font-size: 13px;
      font-weight: 700;
      stroke: rgba(255, 253, 246, 0.95);
      stroke-width: 4.5px;
      stroke-linejoin: round;
      paint-order: stroke;
    }}
    .pin-label-text {{
      font-size: 13px;
      font-weight: 700;
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
    .legend-line-route {{
      width: 20px;
      border-top: 3px dotted #b5382a;
      display: inline-block;
    }}

    /* Table / List Section */
    .table-section {{
      max-width: 900px;
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
      font-family: "Songti SC", "STSong", serif;
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
      padding: 4px 11px;
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
    tbody tr:hover {{
      background: var(--row-hover);
    }}
    tbody tr.active-row {{
      background: #fff3d6;
    }}
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

    @media (max-width: 640px) {{
      .handbook-title {{ font-size: 22px; }}
      thead {{ display: none; }}
      th.col-habitat, td.col-habitat,
      th.col-birds, td.col-birds {{
        display: none;
      }}
      td {{
        padding: 13px 12px;
      }}
      td.col-num {{
        width: 42px;
        padding-right: 4px;
        vertical-align: top;
        padding-top: 15px;
      }}
      .mobile-birds-wrap {{
        display: block;
      }}
    }}

    .card-backdrop {{
      position: fixed;
      inset: 0;
      background: rgba(20, 28, 32, 0.45);
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
      max-width: 680px;
      max-height: 84vh;
      overflow-y: auto;
      background: var(--card-bg);
      border-top: 4px solid var(--accent-red);
      border-radius: 18px 18px 0 0;
      box-shadow: 0 -8px 30px rgba(0,0,0,0.22);
      padding: 20px 20px 26px;
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
      margin-bottom: 12px;
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
      font-family: "Songti SC", "STSong", serif;
      font-size: 20px;
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
      gap: 8px;
      margin-bottom: 12px;
    }}
    .meta-tag {{
      font-size: 12px;
      padding: 3px 9px;
      border-radius: 5px;
      background: var(--thead-bg);
      color: var(--ink-dark);
      font-weight: 600;
    }}
    .sheet-desc {{
      font-size: 14.5px;
      color: var(--ink-dark);
      background: var(--page-bg);
      border-left: 3.5px solid var(--accent-main);
      padding: 11px 13px;
      border-radius: 0 8px 8px 0;
      margin-bottom: 12px;
      text-align: justify;
    }}
    .sheet-subhead {{
      font-size: 13px;
      font-weight: 700;
      color: var(--ink-muted);
      margin: 10px 0 6px;
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
      margin-top: 16px;
    }}
    .btn-primary, .btn-amap {{
      flex: 1;
      min-width: 140px;
      text-align: center;
      padding: 11px 14px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 700;
      text-decoration: none;
      cursor: pointer;
      border: none;
    }}
    .btn-primary {{
      background: #1b6592;
      color: #ffffff;
    }}
    .btn-amap {{
      background: #2d6a4f;
      color: #ffffff;
    }}

    /* Editorial Credits Footer */
    .credits-section {{
      max-width: 900px;
      margin: 22px auto 0;
      padding: 0 14px;
    }}
    .credits-card {{
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-top: 3px solid var(--accent-main);
      border-radius: 10px;
      padding: 16px 18px 14px;
      box-shadow: 0 3px 10px rgba(0,0,0,0.04);
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
      font-family: "Songti SC", "STSong", serif;
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
      background: var(--page-bg);
      border: 1px solid var(--border-color);
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
      background: var(--card-bg);
      border: 1px solid var(--border-color);
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
      color: var(--chip-text);
      background: var(--chip-bg);
      border: 1px solid var(--chip-border);
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
      <span class="org-badge">🐦 厦门市观鸟协会 · 观鸟导览</span>
    </div>
    <h1 class="handbook-title">厦门全域赏鸟点导览图</h1>
    <p class="handbook-lead">
      厦门地处东亚—澳大利西亚候鸟迁徙通道重要节点，山海相拥，拥有河口红树林、滨海滩涂、鱼塭养殖池、城市泻湖及亚热带常绿阔叶林等多元生境。点击地图上的<strong>编号 ①—⑫</strong> 或下方<strong>鸟点列表</strong>，即可查看鸟点详情与导航。
    </p>
  </header>

  <main id="mainOverview">
    <section class="map-section">
      <div class="map-frame">
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

          <!-- Ocean background -->
          <rect id="oceanBgRect" width="{SVG_W}" height="{SVG_H}" />

          <!-- Pure Vector Land, Forests, Bridges & Water Bodies -->
          <g id="pureVectorBaseLayer">
            <use id="surroundingLandUse" href="#exactLandPath" fill="{surrounding_land_fill}" />

            <g clip-path="url(#exactLandClip)">
{district_tints_svg}
{svg_eco_str}
              <path d="{svg_real_green_d}" fill="{real_green_fill}" opacity="{real_green_opacity}" fill-rule="evenodd" />
            </g>

            <path id="majorRoadsPath" d="{svg_real_roads_d}" fill="none" stroke="#dfd5c0" stroke-width="1.0" opacity="0.65" pointer-events="none"/>

            <path id="inlandWaterPath" d="{svg_exact_water_d}" stroke-width="0.45" fill-rule="evenodd" />
          </g>

          <!-- Crisp Real OSM Coastline + Prominent City & District Boundaries -->
          <g id="crispCoastAndBordersLayer" pointer-events="none">
            <path id="coastlineStrokePath" d="{svg_exact_coast_d}" fill="none" stroke-width="1.05" stroke-linejoin="round" />

            <!-- Internal District Boundaries (区级边界) -->
            <path d="{svg_district_border_d}" fill="none" stroke="#fffdf7" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round" opacity="0.88" />
            <path id="distBorderPath" d="{svg_district_border_d}" fill="none" stroke-width="1.8" stroke-dasharray="6,4" stroke-linecap="round" stroke-linejoin="round" />

{svg_labels_str}
          </g>

          <!-- Red Dotted Birding Trails -->
          <g id="routesLayer">
{svg_routes_str}
          </g>

          <!-- Clickable Numbered Birding Hotspots -->
          <g id="markersLayer" filter="url(#softShadow)">
{svg_markers_str}
          </g>

          <!-- Compass Rose -->
          <g transform="translate({SVG_W - 52}, 52)" pointer-events="none">
            <circle cx="0" cy="0" r="22" fill="rgba(255,253,248,0.9)" stroke="#b5a88b" stroke-width="1.2"/>
            <polygon points="0,-16 -5,4 0,0 5,4" fill="#b5382a"/>
            <polygon points="0,14 -4,-2 0,0 4,-2" fill="#7c857e"/>
            <text x="0" y="-18" text-anchor="middle" font-size="9" font-weight="700" fill="#2b312c">N</text>
          </g>
        </svg>

        <div class="map-legend">
          <span class="legend-item"><i class="legend-line-dist"></i> <strong>区级边界</strong></span>
          <span class="legend-item"><i class="legend-dot" style="background:#1565C0"></i> 海滨滩涂/湿地</span>
          <span class="legend-item"><i class="legend-dot" style="background:#388E3C"></i> 城市公园</span>
          <span class="legend-item"><i class="legend-dot" style="background:#1B5E20"></i> 森林</span>
          <span class="legend-item"><i class="legend-line-route"></i> 赏鸟步道</span>
        </div>
      </div>
    </section>

    <section class="table-section">
      <div class="section-head">
        <h2 class="section-title">📋 厦门主要观鸟点一览</h2>
        <div class="filter-pills">
          <button class="filter-pill active" onclick="filterTable('all', this)">全部 (12)</button>
          <button class="filter-pill" onclick="filterTable('wetland', this)">湖泊湿地</button>
          <button class="filter-pill" onclick="filterTable('coastal', this)">滨海滩涂/鱼塘</button>
          <button class="filter-pill" onclick="filterTable('forest', this)">城市山林</button>
          <button class="filter-pill" onclick="filterTable('mountain', this)">郊野水库/高山</button>
        </div>
      </div>

      <div class="table-card">
        <table>
          <thead>
            <tr>
              <th style="width:54px">编号</th>
              <th>观鸟点</th>
              <th class="col-habitat" style="width:150px">生境类型</th>
              <th class="col-birds" style="width:260px">代表鸟种</th>
            </tr>
          </thead>
          <tbody id="spotsTableBody"></tbody>
        </table>
      </div>
    </section>

    <section class="credits-section">
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
    </section>
  </main>

  <div id="cardBackdrop" class="card-backdrop" onclick="closeCard()"></div>
  <aside id="spotSheet" class="spot-sheet" aria-live="polite"></aside>

  <script>
    const SPOTS = {json.dumps(bird_spots, ensure_ascii=False)};
    const PIN_COLORS = {json.dumps(habitat_pin_colors, ensure_ascii=False)};
    let currentFilter = 'all';

    function renderTable() {{
      const tbody = document.getElementById('spotsTableBody');
      const filtered = currentFilter === 'all'
        ? SPOTS
        : SPOTS.filter(s => s.habitat_tag === currentFilter);

      tbody.innerHTML = filtered.map(s => {{
        const c = PIN_COLORS[s.habitat_tag] || '#b5382a';
        const birdsHtml = s.birds.slice(0, 4).map(b => `<span class="bird-chip">${{b}}</span>`).join('');
        return `
          <tr id="row-${{s.id}}" onclick="selectSpot(${{s.id}})">
            <td class="col-num"><span class="num-badge" style="background:${{c}}">${{s.id}}</span></td>
            <td>
              <div class="spot-title-row">
                <span class="spot-link">${{s.name}}</span>
                <span class="row-arrow">›</span>
              </div>
              <div class="spot-submeta">${{s.district}} · ${{s.summary}}</div>
              <div class="mobile-birds-wrap">${{birdsHtml}}</div>
            </td>
            <td class="col-habitat" style="font-size:12.5px;color:var(--ink-muted)">${{s.habitat}}</td>
            <td class="col-birds">${{birdsHtml}}</td>
          </tr>
        `;
      }}).join('');
    }}

    function filterTable(tag, btn) {{
      currentFilter = tag;
      document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderTable();
    }}

    function selectSpot(id) {{
      const spot = SPOTS.find(s => s.id === id);
      if (!spot) return;

      document.querySelectorAll('.spot-marker').forEach(m => {{
        m.classList.toggle('active', Number(m.dataset.id) === id);
      }});
      document.querySelectorAll('#spotsTableBody tr').forEach(r => {{
        r.classList.toggle('active-row', r.id === `row-${{id}}`);
      }});

      const c = PIN_COLORS[spot.habitat_tag] || '#b5382a';
      const birdsHtml = spot.birds.map(b => `<span class="bird-chip">${{b}}</span>`).join('');
      const amapNavUrl = `https://uri.amap.com/marker?position=${{spot.lon}},${{spot.lat}}&name=${{encodeURIComponent(spot.name)}}&callnative=1`;
      const qqNavUrl = `https://apis.map.qq.com/uri/v1/marker?marker=coord:${{spot.lat}},${{spot.lon}};title:${{encodeURIComponent(spot.name)}};addr:${{encodeURIComponent('厦门市' + spot.district)}}&referer=xmbirds`;

      const sheet = document.getElementById('spotSheet');
      sheet.style.borderTopColor = c;
      sheet.innerHTML = `
        <div class="sheet-header">
          <div class="sheet-title-wrap">
            <span class="sheet-num" style="background:${{c}}">${{spot.id}}</span>
            <div>
              <h3 class="sheet-title">${{spot.name}}</h3>
              <span style="font-size:12.5px;color:var(--ink-muted)">${{spot.district}} · 坐标 ${{spot.lon.toFixed(4)}}°E, ${{spot.lat.toFixed(4)}}°N</span>
            </div>
          </div>
          <button class="close-btn" onclick="closeCard()" aria-label="关闭">×</button>
        </div>
        <div class="meta-grid">
          <span class="meta-tag">🌿 生境：${{spot.habitat}}</span>
          <span class="meta-tag">📅 最佳季节：${{spot.season}}</span>
        </div>
        <div class="sheet-desc">${{spot.detail}}</div>
        <div class="sheet-subhead">🐦 常见及代表鸟种：</div>
        <div>${{birdsHtml}}</div>
        <div class="sheet-tips">💡 <strong>观鸟与交通贴士：</strong>${{spot.tips}}</div>
        <div class="sheet-actions">
          <a class="btn-primary" href="${{amapNavUrl}}" target="_blank" rel="noopener">🧭 高德地图导航 (推荐)</a>
          <a class="btn-amap" href="${{qqNavUrl}}" target="_blank" rel="noopener">🗺️ 腾讯地图导航</a>
        </div>
      `;

      document.getElementById('cardBackdrop').classList.add('open');
      sheet.classList.add('open');
    }}

    function closeCard() {{
      document.getElementById('cardBackdrop').classList.remove('open');
      document.getElementById('spotSheet').classList.remove('open');
    }}

    renderTable();
  </script>
</body>
</html>
'''

out_blue = os.path.join(OUT_DIR, "index1.html")
with open(out_blue, "w", encoding="utf-8") as f:
    f.write(build_html("blue"))
print(f"Generated {out_blue} ({os.path.getsize(out_blue)} bytes)")

out_warm = os.path.join(OUT_DIR, "index2.html")
with open(out_warm, "w", encoding="utf-8") as f:
    f.write(build_html("warm"))
print(f"Generated {out_warm} ({os.path.getsize(out_warm)} bytes)")
