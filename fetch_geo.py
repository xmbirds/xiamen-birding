import json
import math
import os
import subprocess
import urllib.request

OUT_DIR = "/Users/libo/xmbirds/birdspoint"

def lonlat_to_tile_xy(lon, lat, z):
    n = 2.0 ** z
    x = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y

z = 11
min_lon, max_lon = 117.88, 118.46
min_lat, max_lat = 24.41, 24.91

x0_f, y0_f = lonlat_to_tile_xy(min_lon, max_lat, z)
x1_f, y1_f = lonlat_to_tile_xy(max_lon, min_lat, z)

tx0, ty0 = int(math.floor(x0_f)), int(math.floor(y0_f))
tx1, ty1 = int(math.floor(x1_f)), int(math.floor(y1_f))

tile_dir = os.path.join(OUT_DIR, "_tiles")
os.makedirs(tile_dir, exist_ok=True)

cols = tx1 - tx0 + 1
rows = ty1 - ty0 + 1

for ty in range(ty0, ty1 + 1):
    for tx in range(tx0, tx1 + 1):
        png_path = os.path.join(tile_dir, f"t_{tx}_{ty}.png")
        bmp_path = os.path.join(tile_dir, f"t_{tx}_{ty}.bmp")
        if not os.path.exists(png_path):
            url = f"https://basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{tx}/{ty}@2x.png"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                with open(png_path, "wb") as out:
                    out.write(r.read())
        if not os.path.exists(bmp_path):
            subprocess.run(["sips", "-s", "format", "bmp", png_path, "--out", bmp_path], check=True, stdout=subprocess.DEVNULL)

def read_bmp(path):
    with open(path, "rb") as f:
        buf = f.read()
    pixel_offset = int.from_bytes(buf[10:14], "little")
    width = int.from_bytes(buf[18:22], "little", signed=True)
    height = int.from_bytes(buf[22:26], "little", signed=True)
    bpp = int.from_bytes(buf[28:30], "little")
    top_down = height < 0
    height = abs(height)
    bytes_per_pixel = bpp // 8
    row_stride = ((width * bytes_per_pixel + 3) // 4) * 4
    rows_data = []
    for r in range(height):
        start = pixel_offset + r * row_stride
        row_bytes = buf[start : start + width * bytes_per_pixel]
        if bytes_per_pixel == 4:
            # Slice out BGR channels rapidly using memoryview
            bgr = bytearray(width * 3)
            bgr[0::3] = row_bytes[0::4]
            bgr[1::3] = row_bytes[1::4]
            bgr[2::3] = row_bytes[2::4]
            rows_data.append(bytes(bgr))
        else:
            rows_data.append(row_bytes[:width * 3])
    if not top_down:
        rows_data.reverse()
    return width, height, rows_data

sample_w, sample_h, _ = read_bmp(os.path.join(tile_dir, f"t_{tx0}_{ty0}.bmp"))
tile_size = sample_w
print(f"Detected tile_size = {tile_size}x{sample_h}")

full_w = cols * tile_size
full_h = rows * tile_size
full_rows = [bytearray() for _ in range(full_h)]

for r_idx, ty in enumerate(range(ty0, ty1 + 1)):
    for c_idx, tx in enumerate(range(tx0, tx1 + 1)):
        bmp_path = os.path.join(tile_dir, f"t_{tx}_{ty}.bmp")
        w, h, rdata = read_bmp(bmp_path)
        for y in range(h):
            full_rows[r_idx * tile_size + y].extend(rdata[y])

px0 = int((x0_f - tx0) * tile_size)
py0 = int((y0_f - ty0) * tile_size)
px1 = int((x1_f - tx0) * tile_size)
py1 = int((y1_f - ty0) * tile_size)

crop_w = px1 - px0
crop_h = py1 - py0

cropped_rows = [bytes(full_rows[y][px0 * 3 : px1 * 3]) for y in range(py0, py1)]

out_bmp = os.path.join(tile_dir, "stitched.bmp")
row_stride = ((crop_w * 3 + 3) // 4) * 4
pad = b"\x00" * (row_stride - crop_w * 3)
img_size = row_stride * crop_h
file_size = 54 + img_size

header = bytearray(54)
header[0:2] = b"BM"
header[2:6] = file_size.to_bytes(4, "little")
header[10:14] = (54).to_bytes(4, "little")
header[14:18] = (40).to_bytes(4, "little")
header[18:22] = crop_w.to_bytes(4, "little", signed=True)
header[22:26] = crop_h.to_bytes(4, "little", signed=True)
header[26:28] = (1).to_bytes(2, "little")
header[28:30] = (24).to_bytes(2, "little")
header[34:38] = img_size.to_bytes(4, "little")

with open(out_bmp, "wb") as f:
    f.write(header)
    for row in reversed(cropped_rows):
        f.write(row)
        f.write(pad)

out_jpg = os.path.join(OUT_DIR, "xiamen_base.jpg")
subprocess.run(["sips", "-Z", "1280", "-s", "format", "jpeg", "-s", "formatOptions", "76", out_bmp, "--out", out_jpg], check=True, stdout=subprocess.DEVNULL)

meta = {
    "min_lon": min_lon, "max_lon": max_lon,
    "min_lat": min_lat, "max_lat": max_lat,
    "z": z, "tx0": tx0, "ty0": ty0,
    "px0": px0, "py0": py0, "px1": px1, "py1": py1,
    "crop_w": crop_w, "crop_h": crop_h,
    "tile_size": tile_size
}
with open(os.path.join(OUT_DIR, "map_meta.json"), "w") as f:
    json.dump(meta, f, indent=2)

print(f"Saved xiamen_base.jpg ({crop_w}x{crop_h} -> resized), size={os.path.getsize(out_jpg)} bytes")
