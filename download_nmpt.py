#!/usr/bin/env python3

import math
import os
import subprocess
import sys
from urllib.parse import urlencode
from urllib.request import urlretrieve

from osgeo import osr

# =========================
# USER INPUT
# =========================

LAT_MIN = 50.04786869296248
LAT_MAX = 50.05265631114086
LON_MIN = 19.92424571666919
LON_MAX = 19.934312066931237

TILE_SIZE = 1000  # meters
OUT_DIR = "tiles"

WCS_BASE = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMPT/GRID1/WCS/DigitalSurfaceModel"
COVERAGE_ID = "DSM_PL-KRON86-NH"

log = print


# CRS TRANSFORM
log("Creating coordinate transformation EPSG:4326 => EPSG:2180")

src = osr.SpatialReference()
src.ImportFromEPSG(4326)

dst = osr.SpatialReference()
dst.ImportFromEPSG(2180)

transform = osr.CoordinateTransformation(src, dst)


uly,ulx, _ = transform.TransformPoint(LAT_MAX, LON_MIN)

lry,lrx, _ = transform.TransformPoint(LAT_MIN, LON_MAX)

log(f"Raw transformed bbox:")
log(f"  ULX={ulx}, ULY={uly}")
log(f"  LRX={lrx}, LRY={lry}")

def tile_generator(ulx, uly, lrx, lry, TILE_SIZE=TILE_SIZE):
    # SNAP TO TILE GRID

    def snap_down(val, size):
        return math.floor(val / size) * size

    def snap_up(val, size):
        return math.ceil(val / size) * size

    ulx_s = snap_down(ulx, TILE_SIZE)
    uly_s = snap_up(uly, TILE_SIZE)
    lrx_s = snap_up(lrx, TILE_SIZE)
    lry_s = snap_down(lry, TILE_SIZE)

    log("Snapped bbox to 1000m grid:")
    log(f"  ULX={ulx_s}, ULY={uly_s}")
    log(f"  LRX={lrx_s}, LRY={lry_s}")

    # =========================
    # TILE GRID
    # =========================

    x_tiles = int((lrx_s - ulx_s) / TILE_SIZE)
    y_tiles = int((uly_s - lry_s) / TILE_SIZE)

    log(f"Tile grid size:")
    log(f"  x_tiles={x_tiles}")
    log(f"  y_tiles={y_tiles}")

    os.makedirs(OUT_DIR, exist_ok=True)


    # =========================
    # DOWNLOAD LOOP
    # =========================

    tile_index = 0

    for ix in range(x_tiles):
        for iy in range(y_tiles):

            tile_index += 1

            xmin = ulx_s + ix * TILE_SIZE
            xmax = xmin + TILE_SIZE
            ymax = uly_s - iy * TILE_SIZE
            ymin = ymax - TILE_SIZE

            log(f"Tile {tile_index}:")
            log(f"  ix={ix}, iy={iy}")
            log(f"  xmin={xmin}, xmax={xmax}")
            log(f"  ymin={ymin}, ymax={ymax}")
            yield xmin, xmax, ymin, ymax
    return

downloaded_tiles = []
for tile_num, (xmin, xmax, ymin, ymax) in enumerate(tile_generator(ulx, uly, lrx, lry)):
    print('tile:', tile_num, (xmin, xmax, ymin, xmax))
    tif_path = f"{OUT_DIR}/tile_{xmin}_{ymin}.asc"

    if os.path.exists(tif_path):
        log(f"Tile {tif_path} already exists, skipping download.")
        downloaded_tiles.append(tif_path)
        continue
    params = {
        "SERVICE": "WCS",
        "VERSION": "2.0.1",
        "REQUEST": "GetCoverage",
        "COVERAGEID": COVERAGE_ID,
        "FORMAT": "image/x-aaigrid",
        "SUBSETTINGCRS": "EPSG:2180",
        "SUBSET": [
            f"x({xmin},{xmax})",
            f"y({ymin},{ymax})"
        ]
    }

    #urlencode with repeated SUBSET keys
    query = urlencode(params, doseq=True)
    url = f"{WCS_BASE}?{query}"

    multipart_body_file = "buffer.txt"#  aaigrid files are very large, we won't keep all of them
    log(f"  URL={url}")
    log(f"  will write to to {multipart_body_file}")

    try:
        #urlretrieve(url, out_file)
        log("  Download OK")
    except Exception as e:
        log(f"  ERROR downloading tile: {e}")
    from utils import  run_command

    #Convert to GeoTiff
    
    
    from extract_multipart import extract_multipart
    extract_multipart(tif_path, OUT_DIR)
    asc_file = OUT_DIR+"/result.tif"
    run_command(f"gdal_translate -of GTiff -co COMPRESS=LZW {asc_file} {tif_path}")
    run_command('gdalinfo {} | tail -n 6')#This fails if file is malformed
    downloaded_tiles.append(tif_path)