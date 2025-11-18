#!/usr/bin/env bash
set -euo pipefail

# Database connection details
source config.sh
export PGPASSWORD

# === CREATE EXTENSION IF DON'T EXIST
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" -c "CREATE EXTENSION IF NOT EXISTS postgis;"


# ========================================
# ARGUMENTS
# ========================================
if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <lat_min> <lat_max> <lon_min> <lon_max>"
  exit 1
fi
# EXAMPLE: ./download_ways.sh 50.047 50.072 19.92 19.95

LAT_MIN="$1"
LAT_MAX="$2"
LON_MIN="$3"
LON_MAX="$4"

addr=\
"http://overpass-api.de/api/interpreter"\
'?data=way["highway"]'\
"($LAT_MIN,$LON_MIN,$LAT_MAX,$LON_MAX);"\
"(._;>>;);"\
"out;"
wget $addr -O ways.osm

osm2pgsql -d $PGDATABASE -H $PGHOST -P $PGPORT -U postgres -O flex -S ways.lua ways.osm
