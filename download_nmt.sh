#!/usr/bin/env bash
set -euo pipefail

# Database connection details
source config.sh
export PGPASSWORD

# === CREATE EXTENSION IF DON'T EXIST
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" -c "CREATE EXTENSION IF NOT EXISTS postgis_raster;"


# Temporary file names
#RASTER_FILE="/tmp/dtm.asc"
RASTER_TABLE="dtm"

# ========================================
# ARGUMENTS
# ========================================
if [ "$#" -ne 5 ]; then
  echo "Usage: $0 <lat_min> <lat_max> <lon_min> <lon_max> <table_name>"
  exit 1
fi
# EXAMPLE: ./download_nmt.sh 50.047 50.072 19.92 19.95 dtm
#./download_nmt.sh 50.051961 50.057236 19.932168 19.938013 dtm
LAT_MIN="$1"
LAT_MAX="$2"
LON_MIN="$3"
LON_MAX="$4"
RASTER_TABLE="$5"

# LAT_MIN="50.04786869296248"
# LAT_MAX="50.07265631114086"
# LON_MIN="19.92424571666919"
# LON_MAX="19.954312066931237"

# LAT_MIN="50.04786869296248"
# LAT_MAX="50.05265631114086"
# LON_MIN="19.92424571666919"
# LON_MAX="19.934312066931237"


echo " Fetching raster for bounding box:"
echo "  lat_min=${LAT_MIN}, lat_max=${LAT_MAX}"
echo "  lon_min=${LON_MIN}, lon_max=${LON_MAX}"

# Transform bbox from EPSG:4326 (lon/lat) to EPSG:2180 (x/y)
read ULX ULY <<< $(echo "${LON_MIN} ${LAT_MAX}" | gdaltransform -s_srs EPSG:4326 -t_srs EPSG:2180 | awk '{print $1, $2}')
read LRX LRY <<< $(echo "${LON_MAX} ${LAT_MIN}" | gdaltransform -s_srs EPSG:4326 -t_srs EPSG:2180 | awk '{print $1, $2}')

echo " Bounding box transformed to EPSG:2180:"
echo "  ULX=${ULX}, ULY=${ULY}"
echo "  LRX=${LRX}, LRY=${LRY}"

addr=\
"https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMT/GRID1/WCS/DigitalTerrainModelFormatTIFF"\
"?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage"\
"&COVERAGEID=DTM_PL-KRON86-NH_TIFF"\
"&FORMAT=image/tiff"\
"&SUBSETTINGCRS=EPSG:2180"\
"&SUBSET=x($ULX,$LRX)&SUBSET=y($LRY,$ULY)"
wget $addr -O nmt.tif
RASTER_FILE="nmt.tif"

# Z kolei .asc sa rozciągnięte na osi y po załadowaniu do Postgresa
# addr=\
# "https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMT/GRID1/WCS/DigitalTerrainModel"\
# "?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage"\
# "&COVERAGEID=DTM_PL-EVRF2007-NH"\
# "&FORMAT=image/x-aaigrid"\
# "&SUBSETTINGCRS=EPSG:2180"\
# "&SUBSET=x($ULX,$LRX)&SUBSET=y($LRY,$ULY)"

# echo "Downloading digital terrain model"

# wget $addr -O nmt1.asc

# echo "Downloaded, cutting out the first part"
# sed '1,/^Content-Disposition: INLINE;/d; /^--wcs/,$d;  /^\r*$/d; p' <nmt1.asc >nmt2.asc
# ##gdal_translate -a_srs EPSG:2180 nmt2.asc temp.tif
# ##gdalwarp -t_srs EPSG:2180 -r bilinear temp.tif nmt_corrected.tif

# RASTER_FILE="nmt_corrected.tif"

export PGPASSWORD;
echo "Dropping the target table $RASTER_TABLE if exists"
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" -c "DROP TABLE IF EXISTS $RASTER_TABLE;"

echo "Creating table and loading into it the raster file"
raster2pgsql -s 2180 -I -C -M -t auto "${RASTER_FILE}" "public.${RASTER_TABLE}" | \
  psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}"

echo "Finished"

# 1. Open QGIS → Browser Panel → PostGIS → New Connection
# 2. Enter:
#      Host: ${PGHOST}
#      Port: ${PGPORT}
#      Database: ${PGDATABASE}
#      User: ${PGUSER}
#      Password: ${PGPASSWORD}
# 3. Connect and expand the database.
# 4. Find the table: public.${RASTER_TABLE}
# 5. Drag it onto the map canvas — you should see your terrain raster.
