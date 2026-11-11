import json
import math
import os

OUT_DIR = "/Users/libo/xmbirds/birdspoint"

with open(os.path.join(OUT_DIR, "osm_xiamen_raw.json"), "r", encoding="utf-8") as f:
    osm = json.load(f)

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

# Stitch coastline ways
coast_ways = [w["nodes"] for w in ways.values() if w.get("tags", {}).get("natural") == "coastline" and len(w.get("nodes", [])) >= 2]

start_map = {}
for idx, nlist in enumerate(coast_ways):
    start_map.setdefault(nlist[0], []).append(idx)

used = set()
closed_rings = []
open_chains = []

# First build open chains starting from nodes that are not the end of any way
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

# Then remaining cycles (closed islands!)
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

print(f"Closed island rings: {len(closed_rings)}, Open mainland coastline chains: {len(open_chains)}")
closed_rings.sort(key=len, reverse=True)
for i, r in enumerate(closed_rings[:10]):
    c_lon = sum(nodes[nid][0] for nid in r) / len(r)
    c_lat = sum(nodes[nid][1] for nid in r) / len(r)
    print(f"  Island #{i+1}: {len(r)} pts, center=({c_lon:.4f}, {c_lat:.4f})")

for i, c in enumerate(open_chains):
    p0 = nodes[c[0]]
    p1 = nodes[c[-1]]
    print(f"  Open chain #{i+1}: {len(c)} pts, start=({p0[0]:.4f}, {p0[1]:.4f}) -> end=({p1[0]:.4f}, {p1[1]:.4f})")
