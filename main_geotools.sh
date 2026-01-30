#!/usr/bin/env bash
set -euo pipefail
source config.sh

if [ $# -eq 4 ]; then
    bbox="$*"
elif [ $# -eq 0 ] && [ -n "${LAT_MIN:-}" ] && [ -n "${LAT_MAX:-}" ] && [ -n "${LON_MIN:-}" ] && [ -n "${LON_MAX:-}" ]; then
    bbox="$LAT_MIN $LAT_MAX $LON_MIN $LON_MAX"
else
    echo "Usage: $0 <lat_min> <lat_max> <lon_min> <lon_max>"
    echo "Alternatively, set LAT_MIN, LAT_MAX, LON_MIN, LON_MAX environment variables"
    exit 1
fi

echo "bbox: $bbox"

MODEL=NMT python3 download_model.py $bbox
MODEL=NMPT python3 download_model.py $bbox
bash ./download_ways.sh $bbox
bash ./compute_slope_static.sh
