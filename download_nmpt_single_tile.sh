#!/usr/bin/env bash
set -euo pipefail

# Database connection details
source config.sh
export PGPASSWORD

# === CREATE EXTENSION IF DON'T EXIST
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" -c "CREATE EXTENSION IF NOT EXISTS postgis_raster;"


# Temporary file names
RASTER_TABLE="dtcm"

# # ========================================
# # ARGUMENTS
# # ========================================
# if [ "$#" -ne 5 ]; then
#   echo "Usage: $0 <lat_min> <lat_max> <lon_min> <lon_max> <table_name>"
#   exit 1
# fi


# LAT_MIN="$1"
# LAT_MAX="$2"
# LON_MIN="$3"
# LON_MAX="$4"
# RASTER_TABLE="$5"

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
ulx=$(echo $ULX | sed  -r 's/^([0-9]+).*/\1/')
uly=$(echo $ULY | sed  -r 's/^([0-9]+).*/\1/')
lrx=$(echo $LRX | sed  -r 's/^([0-9]+).*/\1/')
lry=$(echo $LRY | sed  -r 's/^([0-9]+).*/\1/')

echo " Bounding box transformed to EPSG:2180:"
echo "  ULX=${ULX}, ULY=${ULY}"
echo "  LRX=${LRX}, LRY=${LRY}"


ULX=566000.0
LRX=567000.0
LRY=242000.0
ULY=243000.0

addr="https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMPT/GRID1/WCS/DigitalSurfaceModel"\
"?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage"\
"&COVERAGEID=DSM_PL-KRON86-NH"\
"&FORMAT=image/x-aaigrid"\
"&SUBSETTINGCRS=EPSG:2180"\
"&SUBSET=x($ULX,$LRX)"\
"&SUBSET=y($LRY,$ULY)"
wget $addr -O nmpt_even.asc

gdal_translate -of GTiff -co COMPRESS=LZW result.asc result.tif
RASTER_FILE="result.tif"


export PGPASSWORD;
echo "Dropping the target table $RASTER_TABLE if exists"
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" -c "DROP TABLE IF EXISTS $RASTER_TABLE CASCADE;"

echo "Creating table and loading into it the raster file"
raster2pgsql -s 2180 -Y -I -C -M -t auto "${RASTER_FILE}" "public.${RASTER_TABLE}" | \
  psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}"
#NASTĘPNE : BEZ -I -M
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
