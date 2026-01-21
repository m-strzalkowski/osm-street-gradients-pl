set -euo pipefail
#source bbox_debniki.sh
source bbox_wieksze_centrum.sh
source config.sh
bbox="$LAT_MIN $LAT_MAX $LON_MIN $LON_MAX"
echo "bbox:" $bbox
# ./download_nmt.sh $bbox
MODEL=NMT python3 download_model.py $bbox
MODEL=NMPT python3 download_model.py $bbox
bash ./download_ways.sh $bbox
bash ./compute_slope_static.sh
#bash ./compute_gradients.sh