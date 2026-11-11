import json
import os
import urllib.parse
import urllib.request

OUT_DIR = "/Users/libo/xmbirds/birdspoint"

BBOXES = [
    (24.471, 118.068, 24.483, 118.086),  # 1 Yundang Lake Xidi Sluice
    (24.458, 118.114, 24.478, 118.144),  # 2 Dongping Mountain Park
    (24.507, 118.179, 24.520, 118.196),  # 3 Wutong Pukou
    (24.499, 118.126, 24.512, 118.146),  # 4 Hutoushan Park
    (24.568, 117.892, 24.606, 117.944),  # 5 Tianzhu Mountain Forest Park
    (24.538, 117.954, 24.576, 118.015),  # 6 Maluan Bay
    (24.566, 118.040, 24.607, 118.088),  # 7 Xinglin Bay
    (24.805, 118.005, 24.840, 118.055),  # 8 Xiaoping Forest Park
    (24.550, 118.250, 24.576, 118.286),  # 9 Oucuo-Caicuo Mudflats
]

q_parts = []
for s, w, n, e in BBOXES:
    b = f"{s},{w},{n},{e}"
    q_parts.append(f'way["highway"]({b});')
    q_parts.append(f'way["waterway"]({b});')
    q_parts.append(f'way["natural"~"water|wetland|beach|shoal|mud|wood"]({b});')
    q_parts.append(f'way["leisure"~"park|nature_reserve|garden"]({b});')
    q_parts.append(f'way["landuse"~"forest|grass|meadow|reservoir|basin|aquaculture"]({b});')

overpass_query = f"""
[out:json][timeout:35];
(
  {"".join(q_parts)}
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

out_path = os.path.join(OUT_DIR, "osm_spots_detail.json")
for ep in endpoints:
    try:
        print(f"Fetching local spot details from {ep} ...")
        data_bytes = urllib.parse.urlencode({"data": overpass_query}).encode("utf-8")
        req = urllib.request.Request(ep, data=data_bytes, headers={"User-Agent": "XiamenBirdMap/1.0"})
        with urllib.request.urlopen(req, timeout=35) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data and "elements" in data:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            print(f"Saved {len(data['elements'])} elements to {out_path}")
            break
    except Exception as ex:
        print(f"Failed {ep}: {ex}")
