import json
import urllib.request
import urllib.parse
import os

OUT_DIR = "/Users/libo/xmbirds/birdspoint"

# Query Overpass API for:
# 1. Exact coastline ways in Xiamen & Kinmen bay area (24.41,117.88,24.90,118.45)
# 2. District administrative boundaries (admin_level=6 in Xiamen)
# 3. Major water bodies (Yundang Lake, Wuyuan Bay, Xinglin Bay, Maluan Bay, Tingxi Reservoir, Shidou/Bantou Reservoir)
overpass_query = """
[out:json][timeout:45];
(
  way["natural"="coastline"](24.40,117.88,24.90,118.46);
  relation["boundary"="administrative"]["admin_level"="6"](24.42,117.90,24.88,118.42);
  way["natural"="water"](24.43,117.90,24.85,118.40);
  relation["natural"="water"](24.43,117.90,24.85,118.40);
);
out body;
>;
out skel qt;
"""

endpoints = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

osm_data = None
for ep in endpoints:
    try:
        print(f"Fetching from {ep} ...")
        data_bytes = urllib.parse.urlencode({"data": overpass_query}).encode("utf-8")
        req = urllib.request.Request(ep, data=data_bytes, headers={"User-Agent": "XiamenBirdMap/1.0"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            osm_data = json.loads(resp.read().decode("utf-8"))
        if osm_data and "elements" in osm_data:
            print(f"Success! Downloaded {len(osm_data['elements'])} OSM elements.")
            break
    except Exception as e:
        print(f"Endpoint {ep} failed: {e}")

if not osm_data:
    raise RuntimeError("Failed to fetch from Overpass API")

out_path = os.path.join(OUT_DIR, "osm_xiamen_raw.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(osm_data, f)

# Inspect counts
nodes = {el["id"]: (el["lon"], el["lat"]) for el in osm_data["elements"] if el["type"] == "node"}
ways = [el for el in osm_data["elements"] if el["type"] == "way"]
coast_ways = [w for w in ways if w.get("tags", {}).get("natural") == "coastline"]
water_ways = [w for w in ways if w.get("tags", {}).get("natural") == "water"]
rels = [el for el in osm_data["elements"] if el["type"] == "relation"]

coast_pts = sum(len(w.get("nodes", [])) for w in coast_ways)
print(f"Total nodes: {len(nodes)}, Coastline ways: {len(coast_ways)} ({coast_pts} points!), Water ways: {len(water_ways)}, Relations: {len(rels)}")
for r in rels:
    tags = r.get("tags", {})
    if tags.get("boundary") == "administrative":
        print("Admin relation:", tags.get("name"))
