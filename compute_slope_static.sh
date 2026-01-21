#!/usr/bin/env bash
set -euo pipefail

source config.sh
export PGPASSWORD

psql \
  -h "${PGHOST}" \
  -p "${PGPORT}" \
  -U "${PGUSER}" \
  -d "${PGDATABASE}" \
  -v ON_ERROR_STOP=1 \
  -f compute_slope_static.sql \
  -c "CALL compute_slope_static();"
