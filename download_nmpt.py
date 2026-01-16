#!/usr/bin/env python3

import math
import os
import subprocess
import sys
from urllib.parse import urlencode
from urllib.request import urlretrieve
import re
from osgeo import osr

from utils import  run_command
from extract_multipart import extract_multipart

# =========================
# USER INPUT
# =========================

if len(sys.argv) == 1:
    LAT_MIN = 50.04786869296248
    LAT_MAX = 50.05265631114086
    LON_MIN = 19.92424571666919
    LON_MAX = 19.934312066931237
    # #Kraków ograniczony obwodnicami
    # LAT_MIN = 49.98990084121155
    # LAT_MAX = 50.120513852136696
    # LON_MIN = 19.798920671943563
    # LON_MAX = 20.07638014022811
    print('Using default coords')
elif len(sys.argv) == 5:
    LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = sys.argv[1:5]
else:
    print('usage: download_nmpt <lat_min> <lat_max> <lon_min> <lon_max')
    exit(1)
#Will insert only these tiles which are already in the directory
SKIP_DOWNLOAD = bool(os.getenv('SKIP_DOWNLOAD', False))

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
tile_num=0
for xmin, xmax, ymin, ymax in tile_generator(ulx, uly, lrx, lry):
    tile_num+=1
    print('tile:', tile_num, (xmin, xmax, ymin, xmax))
    tif_path = f"{OUT_DIR}/tile_{xmin}_{ymin}.tif"

    if os.path.exists(tif_path):
        log(f"Tile {tif_path} already exists, skipping download.")
        downloaded_tiles.append(tif_path)
        continue
    if SKIP_DOWNLOAD:
        log(f'SKIP_DOWNLOAD is set to 1: Skip tile {tif_path} entirely')
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
        urlretrieve(url, multipart_body_file)
        log("  Download OK")
    except Exception as e:
        log(f"  ERROR downloading tile: {e}")
    asc_file, _, prj_file = extract_multipart(multipart_body_file, OUT_DIR, expected_parts=['result.asc', 'result.asc.aux.xml', 'result.prj'])
    
    #Convert to GeoTiff    
    run_command(f"gdal_translate -of GTiff -co COMPRESS=LZW {asc_file} {tif_path}")
    #Ensure it is a proper GeoTiff
    tif_info = run_command(f'gdalinfo {tif_path} | tail -n 6')#This fails if file is malformed
    if not re.search(r'Upper Left *\( *'+str(xmin)+r'\.?0*, *'+str(ymax)+r'\.?0*\)', tif_info):
        os.rename(tif_path, tif_path+'_MALFORMED')
        raise Exception("Upper left corner of tiff doesn't match expected:", xmin, ymax)
    if not re.search(r'Lower Right *\( *'+str(xmax)+r'\.?0*, *'+str(ymin)+r'\.?0*\)', tif_info):
        os.rename(tif_path, tif_path+'_MALFORMED')
        raise Exception("Lower Right corner of tiff doesn't match expected:", xmax, ymin)  
    downloaded_tiles.append(tif_path)
    log('Finished with tile ', tif_path)
    log()
    

log(f'Downloaded {len(downloaded_tiles)} tiles')
# upload to postgis
# clean old rasters
PGHOST=os.getenv('PGHOST', 'localhost')
PGPORT=int(os.getenv('PGPORT', '5439'))
PGUSER=os.getenv('PGUSER','postgres')
PGDATABASE=os.getenv('PGDATABASE', 'osm')
PGPASSWORD=os.getenv('PGPASSWORD', 'postgres')
RASTER_TABLE='dtcm'
os.environ['PGPASSWORD'] = PGPASSWORD

log(f"Dropping the target table ${RASTER_TABLE} if exists")
run_command(f' psql -h "{PGHOST}" -p "{PGPORT}" -U "{PGUSER}" -d "{PGDATABASE}" -c "DROP TABLE IF EXISTS {RASTER_TABLE} CASCADE;"')
for i in 2,4,8,16:
    run_command(f' psql -h "{PGHOST}" -p "{PGPORT}" -U "{PGUSER}" -d "{PGDATABASE}" -c "DROP TABLE IF EXISTS o_{i}_{RASTER_TABLE} CASCADE;"')

#loading rasters
i=0
for raster_file in downloaded_tiles:
    ini_opt = '-I ' if i==0 else '-a '
    run_command(f'raster2pgsql -s 2180 -Y -M -l 2,4,8,16 {ini_opt}-t auto "{raster_file}" "public.{RASTER_TABLE}"'+
                f' | psql -h "{PGHOST}" -p "{PGPORT}" -U "{PGUSER}" -d "{PGDATABASE}"')
    i+=1
log('Finished.')