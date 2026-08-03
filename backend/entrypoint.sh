#!/bin/sh
# =============================================================================
# entrypoint.sh — TN Gov AI Scheme Assistant Production Startup
# =============================================================================
#
# BEHAVIOUR:
#   Validates ChromaDB state before starting the application server.
#   Does NOT auto-run ingestion. If validation fails, exits 1 with a
#   structured diagnostic message explaining exactly what is missing.
#
# INITIALIZATION (one-time, run before first deploy):
#   railway run python -m ingestion.cli ingest --data-dir /data
#
# CHECKS PERFORMED (fail-fast — all three must pass):
#   1. CHROMA_DB_PATH directory is mounted and accessible
#   2. The 'tn_gov_schemes' collection exists in ChromaDB
#   3. collection.count() == 31 (exact expected chunk count)
# =============================================================================

set -e

CHROMA_DB_PATH="${CHROMA_DB_PATH:-/data/chroma_db}"
EXPECTED_CHUNKS=31
COLLECTION_NAME="${CHROMA_COLLECTION_NAME:-tn_gov_schemes}"

# ── INIT_MODE: One-time data seeding ─────────────────────────────
# Set INIT_MODE=true in Railway variables for the first deploy.
# This runs the ingestion pipeline to populate ChromaDB on the
# persistent volume, then starts uvicorn so the deploy succeeds.
# After the first deploy, REMOVE the INIT_MODE variable and redeploy.
if [ "${INIT_MODE}" = "true" ]; then
    echo "============================================================"
    echo " INIT_MODE=true — Running one-time data initialization"
    echo "============================================================"
    echo " ChromaDB path: ${CHROMA_DB_PATH}"
    echo " Data dir     : ${DATA_DIR:-/app/data}"

    # Ensure the ChromaDB directory exists
    mkdir -p "${CHROMA_DB_PATH}"

    # Run the ingestion pipeline
    python3 -m ingestion.cli ingest \
        --data-dir "${DATA_DIR:-/app/data}" \
        --force

    # Verify the result
    INIT_COUNT=$(python3 -c "
import chromadb
c = chromadb.PersistentClient(path='${CHROMA_DB_PATH}')
col = c.get_collection('${COLLECTION_NAME}')
print(col.count())
" 2>/dev/null || echo "0")

    echo ""
    echo "============================================================"
    echo " Initialization complete. Chunk count: ${INIT_COUNT}"
    echo "============================================================"

    if [ "${INIT_COUNT}" = "${EXPECTED_CHUNKS}" ]; then
        echo " SUCCESS: ChromaDB seeded with ${EXPECTED_CHUNKS} chunks."
        echo " NEXT STEPS:"
        echo "   1. Remove INIT_MODE variable from Railway"
        echo "   2. Redeploy the service"
        echo "============================================================"
    else
        echo " WARNING: Expected ${EXPECTED_CHUNKS} chunks but got ${INIT_COUNT}."
        echo " Check ingestion logs above for errors."
        echo "============================================================"
    fi

    # Start uvicorn so the deploy health check passes
    PORT="${PORT:-8000}"
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --workers 1
fi

echo "============================================================"
echo " TN Gov AI Scheme Assistant — Startup Validation"
echo "============================================================"
echo " ChromaDB path  : ${CHROMA_DB_PATH}"
echo " Collection     : ${COLLECTION_NAME}"
echo " Expected chunks: ${EXPECTED_CHUNKS}"
echo "============================================================"

# ── Seed Initialization: Seed persistent volume if empty or model mismatched ──
SEED_NEEDED=0
if [ ! -f "${CHROMA_DB_PATH}/chroma.sqlite3" ]; then
    SEED_NEEDED=1
else
    MATCHING_MODEL=$(python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('${CHROMA_DB_PATH}/chroma.sqlite3')
    cur = conn.cursor()
    rows = cur.execute(\"SELECT string_value FROM collection_metadata WHERE key='embedding_model'\").fetchall()
    print('1' if rows and rows[0][0] == '${EMBEDDING_MODEL}' else '0')
except Exception:
    print('0')
" 2>/dev/null || echo "0")
    if [ "${MATCHING_MODEL}" = "0" ]; then
        echo "[SEED] Volume ChromaDB model does not match '${EMBEDDING_MODEL}' — forcing seed update."
        SEED_NEEDED=1
    fi
fi

if [ "${SEED_NEEDED}" = "1" ] && [ -d "/app/seed_data/chroma_db" ]; then
    echo "[SEED] Seeding ChromaDB persistent volume from /app/seed_data/chroma_db..."
    rm -rf "${CHROMA_DB_PATH:?}"/*
    mkdir -p "${CHROMA_DB_PATH}"
    cp -rf /app/seed_data/chroma_db/* "${CHROMA_DB_PATH}/"
    echo "[SEED] Seeding complete."
fi

# ── Check 1: Directory accessibility ─────────────────────────────
echo "[CHECK 1/3] Verifying ChromaDB path is mounted and accessible..."

if [ ! -d "${CHROMA_DB_PATH}" ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  ERROR: ChromaDB validation failed — startup aborted.   ║"
    echo "╠══════════════════════════════════════════════════════════╣"
    echo "║                                                          ║"
    echo "║  Check 1 FAILED: Path not found or not a directory.     ║"
    echo "║  Path: ${CHROMA_DB_PATH}"
    echo "║                                                          ║"
    echo "║  CAUSE: The persistent volume is not mounted, or the    ║"
    echo "║  CHROMA_DB_PATH environment variable points to a path   ║"
    echo "║  that does not exist inside the container.              ║"
    echo "║                                                          ║"
    echo "║  ACTION REQUIRED:                                        ║"
    echo "║  1. Verify the Railway persistent volume is attached     ║"
    echo "║     and mounted at: ${CHROMA_DB_PATH}"
    echo "║  2. Run one-time initialization:                         ║"
    echo "║     railway run python -m ingestion.cli ingest           ║"
    echo "║  3. Redeploy the service.                                ║"
    echo "║                                                          ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    exit 1
fi

echo "[CHECK 1/3] PASSED — Path exists: ${CHROMA_DB_PATH}"

# ── Checks 2 & 3: Collection existence and chunk count ───────────
echo "[CHECK 2/3] Verifying ChromaDB collection and chunk count..."

set +e
VALIDATION_OUTPUT=$(python3 - <<'PYTHON_EOF'
import sys
import os
import sqlite3

chroma_path = os.environ.get("CHROMA_DB_PATH", "/data/chroma_db")
collection_name = os.environ.get("CHROMA_COLLECTION_NAME", "tn_gov_schemes")
expected_chunks = 31

db_file = os.path.join(chroma_path, "chroma.sqlite3")
if not os.path.exists(db_file):
    print(f"CHROMADB_CLIENT_ERROR:{db_file} not found")
    sys.exit(2)

try:
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    existing = [row[0] for row in cur.execute("SELECT name FROM collections").fetchall()]
    if collection_name not in existing:
        print(f"COLLECTION_MISSING:{collection_name}:AVAILABLE:{','.join(existing) if existing else 'none'}")
        sys.exit(3)

    count = cur.execute("SELECT count(*) FROM embeddings").fetchone()[0]
    print(f"COUNT:{count}")
    if count != expected_chunks:
        sys.exit(4)
    sys.exit(0)
except Exception as e:
    print(f"COUNT_ERROR:{e}")
    sys.exit(2)
PYTHON_EOF
)
PYTHON_EXIT=$?
set -e

echo "[DEBUG] Python validation script exit code: ${PYTHON_EXIT}, output: ${VALIDATION_OUTPUT}"

# ── Interpret Python probe output ─────────────────────────────────
case $PYTHON_EXIT in
    0)
        CHUNK_COUNT=$(echo "$VALIDATION_OUTPUT" | grep "^COUNT:" | cut -d: -f2)
        echo "[CHECK 2/3] PASSED — Collection '${COLLECTION_NAME}' exists."
        echo "[CHECK 3/3] PASSED — Chunk count: ${CHUNK_COUNT} (expected ${EXPECTED_CHUNKS})."
        ;;

    2)
        echo ""
        echo "╔══════════════════════════════════════════════════════════╗"
        echo "║  ERROR: ChromaDB validation failed — startup aborted.   ║"
        echo "╠══════════════════════════════════════════════════════════╣"
        echo "║                                                          ║"
        echo "║  Check 2 FAILED: ChromaDB client error.                 ║"
        echo "║  Detail: ${VALIDATION_OUTPUT}"
        echo "║                                                          ║"
        echo "║  CAUSE: ChromaDB cannot open or read the persistent     ║"
        echo "║  store. The volume may be corrupted or empty.           ║"
        echo "║                                                          ║"
        echo "║  ACTION REQUIRED:                                        ║"
        echo "║     railway run python -m ingestion.cli ingest           ║"
        echo "║                                                          ║"
        echo "╚══════════════════════════════════════════════════════════╝"
        exit 1
        ;;

    3)
        MISSING_COLLECTION=$(echo "$VALIDATION_OUTPUT" | grep "^COLLECTION_MISSING:" | cut -d: -f2)
        AVAILABLE=$(echo "$VALIDATION_OUTPUT" | grep "^COLLECTION_MISSING:" | sed 's/.*AVAILABLE://')
        echo ""
        echo "╔══════════════════════════════════════════════════════════╗"
        echo "║  ERROR: ChromaDB validation failed — startup aborted.   ║"
        echo "╠══════════════════════════════════════════════════════════╣"
        echo "║                                                          ║"
        echo "║  Check 2 FAILED: Collection not found.                  ║"
        echo "║  Expected collection : ${COLLECTION_NAME}"
        echo "║  Collections present : ${AVAILABLE}"
        echo "║                                                          ║"
        echo "║  CAUSE: The persistent volume exists but the ingestion   ║"
        echo "║  pipeline has not been run, or ran with a different     ║"
        echo "║  collection name.                                        ║"
        echo "║                                                          ║"
        echo "║  ACTION REQUIRED:                                        ║"
        echo "║     railway run python -m ingestion.cli ingest           ║"
        echo "║                                                          ║"
        echo "╚══════════════════════════════════════════════════════════╝"
        exit 1
        ;;

    4)
        ACTUAL_COUNT=$(echo "$VALIDATION_OUTPUT" | grep "^COUNT:" | cut -d: -f2)
        echo ""
        echo "╔══════════════════════════════════════════════════════════╗"
        echo "║  ERROR: ChromaDB validation failed — startup aborted.   ║"
        echo "╠══════════════════════════════════════════════════════════╣"
        echo "║                                                          ║"
        echo "║  Check 3 FAILED: Unexpected chunk count.                ║"
        echo "║  Actual count  : ${ACTUAL_COUNT}"
        echo "║  Expected count: ${EXPECTED_CHUNKS}"
        echo "║                                                          ║"
        echo "║  CAUSE: The collection exists but contains the wrong    ║"
        echo "║  number of chunks. Ingestion may be incomplete or the   ║"
        echo "║  corpus may have been modified.                         ║"
        echo "║                                                          ║"
        echo "║  ACTION REQUIRED:                                        ║"
        echo "║  1. Clear and re-initialize:                             ║"
        echo "║     railway run python -m ingestion.cli clear            ║"
        echo "║     railway run python -m ingestion.cli ingest           ║"
        echo "║  2. Verify your data directory contains all 31 source   ║"
        echo "║     documents before re-ingesting.                      ║"
        echo "║                                                          ║"
        echo "╚══════════════════════════════════════════════════════════╝"
        exit 1
        ;;

    *)
        echo ""
        echo "╔══════════════════════════════════════════════════════════╗"
        echo "║  ERROR: ChromaDB validation probe failed unexpectedly.  ║"
        echo "║  Exit code: ${PYTHON_EXIT}                              ║"
        echo "║  Output: ${VALIDATION_OUTPUT}"
        echo "╚══════════════════════════════════════════════════════════╝"
        exit 1
        ;;
esac

# ── All checks passed — start uvicorn ────────────────────────────
echo ""
echo "============================================================"
echo " ChromaDB validation PASSED. Starting application server..."
echo "============================================================"

PORT="${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --workers 1
