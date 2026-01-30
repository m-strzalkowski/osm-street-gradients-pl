#!/usr/bin/env bash
set -euo pipefail

source config.sh
export PGPASSWORD

psql \
  -h "${PGHOST}" \
  -p "${PGPORT}" \
  -U "${PGUSER}" \
  -d "${PGDATABASE}" \
  -tAc "
select
    json_build_object(
        'type',
        'FeatureCollection',
        'features',
        json_agg(
            ST_AsGeoJSON(
                s.*,
                id_column => 'segment_id'
            )::json
        )
    )
from (select segment_id, ST_Transform(geom, 4326) as geom, slope, name from slope_static) s
"
