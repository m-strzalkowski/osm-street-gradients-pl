#!/usr/bin/env bash
set -euo pipefail

source config.sh
export PGPASSWORD

psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" << EOF
    drop materialized view if exists slope;
    create materialized view slope as
    select
        q.way_id,
        q.name,
        q.geom,
        abs(st_nearestvalue(d1.rast, st_startpoint(q.geom)) - st_nearestvalue(d2.rast, st_endpoint(q.geom))) / st_length(q.geom) as slope,
        st_nearestvalue(d1.rast, st_startpoint(q.geom)) as height_a,
        st_nearestvalue(d2.rast, st_endpoint(q.geom)) as height_b
    from
        (
        select
            ways.way_id,
            ways.name,
            (
                st_dumpsegments(
                    st_segmentize(
                        st_simplifypreservetopology(st_transform(ways.geom, 2180), 2::double precision),
                        50::double precision
                    )
                )
            ).geom as geom
        from
            ways
        where
            ways.name is not null
            and ways.layer is null
            and ways.bridge is null
            and kind in ('primary', 'secondary', 'tertiary', 'residential', 'living_street', 'unclassified', 'service')) q
    join dtm d1 on
        st_contains(st_envelope(d1.rast),
        st_startpoint(q.geom))
    join dtm d2 on
        st_contains(st_envelope(d2.rast),
        st_endpoint(q.geom))
EOF
