#!/usr/bin/env python3

import math
import os
import subprocess
import sys
from urllib.parse import urlencode
from urllib.request import urlretrieve
import re
import time
from osgeo import osr
log = print
silent = lambda *a, **k :None

#Internal imports
from utils import  run_command
from extract_multipart import extract_multipart
from treefinder import treefiend



# PARAMETERS

if len(sys.argv) == 1:
    #Centrum Krakowa
    # LAT_MIN = float(os.getenv('LAT_MIN',50.04786869296248))
    # LAT_MAX = float(os.getenv('LAT_MAX', 50.05265631114086))
    # LON_MIN = float(os.getenv('LON_MIN',19.92424571666919))
    # LON_MAX = float(os.getenv('LON_MAX',19.934312066931237))

    # #Kraków ograniczony obwodnicami
    # LAT_MIN = float(os.getenv('LAT_MIN',49.98990084121155))
    # LAT_MAX = float(os.getenv('LAT_MAX', 50.120513852136696))
    # LON_MIN = float(os.getenv('LON_MIN',19.798920671943563))
    # LON_MAX = float(os.getenv('LON_MAX',20.07638014022811))

    #Południe Krakowa - tam gdzie podjazdy
    # LAT_MIN = float(os.getenv('LAT_MIN',49.98944742300455))
    # LAT_MAX = float(os.getenv('LAT_MAX',50.069140407423106))
    # LON_MIN = float(os.getenv('LON_MIN',19.807477376085956))
    # LON_MAX = float(os.getenv('LON_MAX',19.998048150356652))

    #podjazd pod zoo
    
    LAT_MIN = float(os.getenv('LAT_MIN', 50.04183857007973))
    LAT_MAX = float(os.getenv('LAT_MAX', 50.06514819273997))
    LON_MIN = float(os.getenv('LON_MIN', 19.828946554412852))
    LON_MAX = float(os.getenv('LON_MAX', 19.871964006870684))


    print('Using default coords')
elif len(sys.argv) == 5:
    LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = [float(x) for x in sys.argv[1:5]]
else:
    print('usage: download_nmpt <lat_min> <lat_max> <lon_min> <lon_max')
    exit(1)

#Will insert only these tiles which are already in the directory (useful if one want to see some results in db out without waiting too long for all files to download)
SKIP_DOWNLOAD = bool(os.getenv('SKIP_DOWNLOAD', False))

TILE_SIZE = 1000  # meters
SCALE_FACTOR = 1.0

MODEL = os.getenv("MODEL", 'NMPT')
if MODEL == 'NMT':
    WCS_BASE = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMT/GRID1/WCS/DigitalTerrainModelFormatTIFF"
    RESPONSE_FORMAT = "image/tiff"
    COVERAGE_ID = "DTM_PL-KRON86-NH_TIFF"
    OUT_DIR = "tiles/nmt"
if MODEL == "NMPT":
    WCS_BASE = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMPT/GRID1/WCS/DigitalSurfaceModel"
    RESPONSE_FORMAT = "image/x-aaigrid"
    COVERAGE_ID = "DSM_PL-KRON86-NH"
    OUT_DIR = "tiles/nmpt"

log('=== NMT/NMPT TILES DOWNLOAD AND IMPORT ===')
log(f"MODEL:{MODEL}")
log(f"WCS_BASE:{WCS_BASE}")
log(f"RESPONSE_FORMAT:{RESPONSE_FORMAT}")
log(f"OUT_DIR:{OUT_DIR}")
log(f"LAT_MIN LAT_MAX LON_MIN LON_MAX")
log(f"{LAT_MIN} {LAT_MAX} {LON_MIN} {LON_MAX}")
log()


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

if uly<0 or ulx<0 or lrx<0 or lry<0:
    raise Exception("Incorrect bbox (negatove coords)")


def tile_generator(ulx, uly, lrx, lry, TILE_SIZE=TILE_SIZE, log=log):
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

tif_path_of = lambda OUT_DIR, TILE_SIZE, SCALE_FACTOR, xmin, ymin : f"{OUT_DIR}/tile_{xmin}_{ymin}_{TILE_SIZE}_{SCALE_FACTOR}.tif"
doubt_tif_path_of = lambda OUT_DIR, TILE_SIZE, SCALE_FACTOR, xmin, ymin : f"{OUT_DIR}/tile_{xmin}_{ymin}_{TILE_SIZE}_{SCALE_FACTOR}.doubt.tif"
downloaded_tiles = []

## Download tiles
log("== DOWNLOADING TILES ==")
tile_num=0
for xmin, xmax, ymin, ymax in tile_generator(ulx, uly, lrx, lry, log=silent):
    tile_num+=1
    print('tile:', tile_num, (xmin, xmax, ymin, xmax))
    tif_path = tif_path_of(OUT_DIR, TILE_SIZE, SCALE_FACTOR, xmin, ymin)

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
        "FORMAT": RESPONSE_FORMAT,
        "SUBSETTINGCRS": "EPSG:2180",
        "SCALEFACTOR":str(SCALE_FACTOR),
        "SUBSET": [
            f"x({xmin},{xmax})",
            f"y({ymin},{ymax})"
        ]
    }

    #urlencode with repeated SUBSET keys
    query = urlencode(params, doseq=True)
    url = f"{WCS_BASE}?{query}"

    response_body_file = OUT_DIR+"/buffer.txt"#  aaigrid files are very large, we won't keep all of them
    log(f"  URL={url}")
    log(f"  will write to to {response_body_file}")

    retry_times_sec = [30, 60, 3*60, 15*60, 60*60]
    retry_num = 0
    retrieved = False
    while(not retrieved and retry_num < len(retry_times_sec)):
        try:
            log(f'Commence download {url} to {response_body_file}')
            urlretrieve(url, response_body_file)
            log("  Download OK")
            retrieved = True
        except Exception as e:
            log(f"  ERROR downloading tile: {e}")
            log(f"Will wait {retry_times_sec[retry_num]} seconds and retry")
            time.sleep(retry_times_sec[retry_num])
            retry_num +=1
    if not retrieved:
        raise Exception("Reasonable number of retries exceeded.")
    
    if RESPONSE_FORMAT == "image/x-aaigrid":
        #response has 3 files in it...
        asc_file, _, prj_file = extract_multipart(response_body_file, OUT_DIR, expected_parts=['result.asc', 'result.asc.aux.xml', 'result.prj'])
        #Convert to GeoTiff
        #It apparently implicitly using prj file which is located within the same directory 
        run_command(f"gdal_translate -of GTiff -co COMPRESS=LZW {asc_file} {tif_path}")
    elif RESPONSE_FORMAT == "image/tiff":
        #Just move, nothing to be done
        run_command(f"mv {response_body_file} {tif_path}")
    else:
        raise Exception(f"wrong format:{RESPONSE_FORMAT}")
    
    #Ensure it is a proper GeoTiff, with matching bounding box
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


if MODEL == "NMPT":
    log(f"== COMPUTING DOUBT MAPS FOR NMPT ==")
    generated_doubt_tiles = []
    tile_num=0
    for xmin, xmax, ymin, ymax in tile_generator(ulx, uly, lrx, lry, log=silent):
        tile_num+=1
        print('tile:', tile_num, (xmin, xmax, ymin, xmax))
        tif_path = tif_path_of(OUT_DIR, TILE_SIZE, SCALE_FACTOR, xmin, ymin)
        doubt_tif_path = doubt_tif_path_of(OUT_DIR, TILE_SIZE, SCALE_FACTOR, xmin, ymin)

        #Skip tile if doubt tile (derivate) is younger than the original tif
        if os.path.exists(doubt_tif_path) and os.path.getmtime(doubt_tif_path) > os.path.getmtime(tif_path):
            log(f"Skipping generating roughness to {doubt_tif_path} since it younger than input file {tif_path}")
            generated_doubt_tiles.append(doubt_tif_path)
            continue

        treefiend.generate_roughness(tif_path, doubt_tif_path, save_also_png = False)
        log('Generated ', doubt_tif_path)
        generated_doubt_tiles.append(doubt_tif_path)
    log("generated all doubt maps for NMPT model")

# upload to postgis
# clean old rasters
PGHOST=os.getenv('PGHOST', 'localhost')
PGPORT=int(os.getenv('PGPORT', '5439'))
PGUSER=os.getenv('PGUSER','postgres')
PGDATABASE=os.getenv('PGDATABASE', 'osm')
PGPASSWORD=os.getenv('PGPASSWORD', 'postgres')
os.environ['PGPASSWORD'] = PGPASSWORD

if MODEL == "NMPT":
    RASTER_TABLE='dtcm'
elif MODEL == "NMT":
    RASTER_TABLE="dtm"

def upload_rasters_to_db(RASTER_TABLE:str, tiles:list):
    log(f"== UPLOADING {len(tiles)} TILES TO TABLE {RASTER_TABLE} ==")
    run_command(f'psql -h "{PGHOST}" -p "{PGPORT}" -U "{PGUSER}" -d "{PGDATABASE}" -c "CREATE EXTENSION IF NOT EXISTS postgis;"')
    run_command(f'psql -h "{PGHOST}" -p "{PGPORT}" -U "{PGUSER}" -d "{PGDATABASE}" -c "CREATE EXTENSION IF NOT EXISTS postgis_raster;"')

    log(f"Dropping the target table ${RASTER_TABLE} if exists")
    run_command(f' psql -h "{PGHOST}" -p "{PGPORT}" -U "{PGUSER}" -d "{PGDATABASE}" -c "DROP TABLE IF EXISTS {RASTER_TABLE} CASCADE;"')
    # for i in 2,4,8,16:
    #     run_command(f' psql -h "{PGHOST}" -p "{PGPORT}" -U "{PGUSER}" -d "{PGDATABASE}" -c "DROP TABLE IF EXISTS o_{i}_{RASTER_TABLE} CASCADE;"')

    #loading rasters
    i=0
    for raster_file in tiles:
        ini_opt = '-I ' if i==0 else '-a '
        pyramids = ""#"-l 2,4,8,16 "
        run_command(f'raster2pgsql -s 2180 -Y -M {pyramids}{ini_opt}-t auto "{raster_file}" "public.{RASTER_TABLE}"'+
                    f' | psql -h "{PGHOST}" -p "{PGPORT}" -U "{PGUSER}" -d "{PGDATABASE}"')
        i+=1
    log('Finished.')
upload_rasters_to_db(RASTER_TABLE, downloaded_tiles)

if MODEL == "NMPT":
    upload_rasters_to_db("dtcm_doubt", generated_doubt_tiles)