import json
import urllib.request
import urllib.parse
import os

OUT_DIR = "/Users/libo/xmbirds/birdspoint"

# Fetch real parks, forests, nature reserves, and major highways/bridges in Xiamen
overpass_query = """
[out:json][timeout:45];
(
  way["leisure"~"park|nature_reserve"](24.42,117.90,24.86,118.40);
  relation["leisure"~"park|nature_reserve"](24.42,117.90,24.86,118.40);
  way["natural"="wood"](24.42,117.90,24.86,118.40);
  way["landuse"="forest"](24.42,117.90,24.86,118.40);
  way["highway"~"motorway|trunk"](24.42,117.92,24.82,118.40);
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

osm_extra = None
for ep in endpoints:
    try:
        print(f"Fetching real parks & bridges from {ep} ...")
        data_bytes = urllib.parse.urlencode({"data": overpass_query}).encode("utf-8")
        req = urllib.request.Request(ep, data=data_bytes, headers={"User-Agent": "XiamenBirdMap/1.0"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            osm_extra = json.loads(resp.read().decode("utf-8"))
        if osm_extra and "elements" in osm_extra:
            print(f"Success! Downloaded {len(osm_extra['elements'])} elements.")
            break
    except Exception as e:
        print(f"Endpoint {ep} failed: {e}")

if osm_extra:
    with open(os.path.join(OUT_DIR, "osm_xiamen_extra.json"), "w", encoding="utf-8") as f:
        json.dump(osm_extra, f)
    ways = [el for el in osm_extra["elements"] if el["type"] == "way"]
    green = [w for w in ways if any(k in w.get("tags", {}) for k in ("leisure", "natural", "landuse"))]
    roads = [w for w in ways if "highway" in w.get("tags", {})]
    print(f"Green polygons: {len(green)}, Major road/bridge ways: {len(roads)}")
