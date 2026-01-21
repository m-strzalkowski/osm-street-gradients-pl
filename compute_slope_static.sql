DROP TABLE IF EXISTS slope_static;
CREATE TABLE slope_static (
    segment_id BIGINT NOT NULL,
    way_id    BIGINT NOT NULL,
    name      TEXT,
    geom      geometry(LineString, 2180) NOT NULL,
    slope     DOUBLE PRECISION NOT NULL,
    nmt_h_a  DOUBLE PRECISION,
    nmt_h_b  DOUBLE PRECISION,
    nmpt_h_a  DOUBLE PRECISION,
    nmpt_h_b  DOUBLE PRECISION,
    nmpt_doubt_a  DOUBLE PRECISION,
    nmpt_doubt_b  DOUBLE PRECISION,
    nmt_used_a INT,
    nmt_used_b INT
);

-- Recommended but optional
CREATE INDEX IF NOT EXISTS slope_static_geom_idx
    ON slope_static
    USING GIST (geom);

CREATE INDEX IF NOT EXISTS slope_static_way_id_idx
    ON slope_static (way_id);


CREATE OR REPLACE PROCEDURE compute_slope_static()
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    cur REFCURSOR;

    total_ways_count BIGINT;
    processed_ways   BIGINT := 0;
    processed_percent    NUMERIC;
    previous_way_id BIGINT:=-1;
    segment_counter BIGINT :=1;

    h_nmt_start DOUBLE PRECISION;
    h_nmt_end   DOUBLE PRECISION;
    h_nmpt_start DOUBLE PRECISION;
    h_nmpt_end   DOUBLE PRECISION;
    doubt_nmpt_start DOUBLE PRECISION;
    doubt_nmpt_end DOUBLE PRECISION;
    nmt_used_start INT;
    nmt_used_end INT;
    h_start DOUBLE PRECISION;
    h_end DOUBLE PRECISION;

BEGIN
    -- Optional but usually desired
    TRUNCATE TABLE slope_static;

    /*
     * Count total number of ways for progress reporting
     */
    SELECT COUNT(*) INTO total_ways_count
    FROM ways
    WHERE
        ways.name IS NOT NULL
        AND ways.layer IS NULL
        AND ways.bridge IS NULL
        AND kind IN (
            'primary', 'secondary', 'tertiary',
            'residential', 'living_street',
            'unclassified', 'service'
        );

    RAISE NOTICE 'Processing % ways', total_ways_count;

    /*
     * Cursor over segmentized ways
     */
    OPEN cur FOR
        SELECT
            ways.way_id,
            ways.layer,
            ways.bridge,
            ways.name,
            (st_dumpsegments(
                st_segmentize(
                    st_simplifypreservetopology(
                        st_transform(ways.geom, 2180),
                        2::double precision
                    ),
                    50::double precision
                )
            )).geom AS geom
        FROM ways
        WHERE
            ways.name IS NOT NULL
            -- AND ways.layer IS NULL
            -- AND ways.bridge IS NULL
            AND kind IN (
                'primary', 'secondary', 'tertiary',
                'residential', 'living_street',
                'unclassified', 'service'
            );

    LOOP
        FETCH cur INTO rec;
        EXIT WHEN NOT FOUND;

        /*
         * Sample raster at segment endpoints
         */
         --nmt
        SELECT st_nearestvalue(d1.rast, st_startpoint(rec.geom)) 
        INTO h_nmt_start FROM dtm d1 WHERE st_contains(st_envelope(d1.rast), st_startpoint(rec.geom)) LIMIT 1;
        IF h_nmt_start IS NULL THEN CONTINUE; END IF;

        SELECT st_nearestvalue(d1.rast, st_endpoint(rec.geom)) 
        INTO h_nmt_end FROM dtm d1 WHERE st_contains(st_envelope(d1.rast), st_endpoint(rec.geom)) LIMIT 1;
        IF h_nmt_end IS NULL THEN CONTINUE; END IF;

        --nmpt
        SELECT st_nearestvalue(d1.rast, st_startpoint(rec.geom)) 
        INTO h_nmpt_start FROM dtcm d1 WHERE st_contains(st_envelope(d1.rast), st_startpoint(rec.geom)) LIMIT 1;
        IF h_nmpt_start IS NULL THEN CONTINUE; END IF;

        SELECT st_nearestvalue(d1.rast, st_endpoint(rec.geom)) 
        INTO h_nmpt_end FROM dtcm d1 WHERE st_contains(st_envelope(d1.rast), st_endpoint(rec.geom)) LIMIT 1;
        IF h_nmpt_end IS NULL THEN CONTINUE; END IF;

        --doubt of nmpt
        SELECT st_nearestvalue(d1.rast, st_startpoint(rec.geom)) 
        INTO doubt_nmpt_start FROM dtcm_doubt d1 WHERE st_contains(st_envelope(d1.rast), st_startpoint(rec.geom)) LIMIT 1;
        IF doubt_nmpt_start IS NULL THEN CONTINUE; END IF;

        SELECT st_nearestvalue(d1.rast, st_endpoint(rec.geom)) 
        INTO doubt_nmpt_end FROM dtcm_doubt d1 WHERE st_contains(st_envelope(d1.rast), st_endpoint(rec.geom)) LIMIT 1;
        IF doubt_nmpt_end IS NULL THEN CONTINUE; END IF;

        --ignore tunnels
        IF rec.layer IS NOT NULL AND rec.layer < 0:
            THEN CONTINUE;
        END IF;

        --use NMPT if computed doubt is low or layer >0 is set or bridge explicitly
        --otherwise NMT, when NMPT cannot be trusted (mainly because of overhanging trees)
        IF doubt_nmpt_start < 1.0 OR rec.layer IS NOT NULL OR rec.bridge IS NOT NULL
            THEN h_start := h_nmpt_start; nmt_used_start := 0;
            ELSE h_start := h_nmt_start; nmt_used_start := 1;
        END IF;

        IF doubt_nmpt_end < 1.0 OR rec.layer IS NOT NULL OR rec.bridge IS NOT NULL
            THEN h_end := h_nmpt_end; nmt_used_end := 0;
            ELSE h_end := h_nmt_end; nmt_used_end := 1;
        END IF;


        /*
         * Insert computed values
         */
        INSERT INTO slope_static (
            segment_id,
            way_id,
            name,
            geom,
            slope,
            nmt_h_a,
            nmt_h_b,
            nmpt_h_a,
            nmpt_h_b,
            nmpt_doubt_a,
            nmpt_doubt_b
        )
        VALUES (
            segment_counter,
            rec.way_id,
            rec.name,
            rec.geom,
            abs(h_start - h_end) / st_length(rec.geom),
            h_nmt_start,
            h_nmt_end,
            h_nmpt_start,
            h_nmpt_end,
            doubt_nmpt_start,
            doubt_nmpt_end
        );

        RAISE NOTICE '% way_id % slope % geom %',segment_counter, rec.way_id, h_nmt_start, ST_AsText(rec.geom);

        IF rec.way_id != previous_way_id /*I hate <>, != also works*/
            THEN 
            processed_ways := processed_ways + 1;
            processed_percent := (processed_ways::NUMERIC / total_ways_count)*100;

            -- RAISE NOTICE '\r% (%/% ways)',
            --     processed_percent,/*to_char(processed_percent, 'FM90D00'),*/
            --     processed_ways,
            --     total_ways_count;
            RAISE NOTICE '% %% (% of % ways)', processed_percent, processed_ways, total_ways_count;
            previous_way_id := rec.way_id;
        END IF;
        segment_counter := segment_counter + 1;
    END LOOP;

    CLOSE cur;

    processed_ways := processed_ways + 1;
    RAISE NOTICE '\nDone. Computed slopes for % ways', processed_ways;
END;
$$;
