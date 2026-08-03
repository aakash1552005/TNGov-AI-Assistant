"""One-time ChromaDB initialization script for production deployment.

Run this ONCE via Railway CLI after the first deploy to seed the persistent
volume with the 31 scheme document chunks:

    railway run python -m backend.scripts.init_vectorstore
    # or from inside the container:
    python scripts/init_vectorstore.py

This script is NOT called during normal application startup.
The entrypoint.sh validates the result of this script on every boot.

Exit codes:
    0 — Success: ChromaDB initialized and verified with exactly 31 chunks.
    1 — Error:   Initialization or verification failed.
"""

import logging
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

EXPECTED_CHUNK_COUNT = 31


def _verify_chroma(chroma_db_path: str, collection_name: str) -> int:
    """Return the current chunk count in ChromaDB, or -1 on error."""
    try:
        import chromadb  # noqa: PLC0415

        client = chromadb.PersistentClient(path=chroma_db_path)
        existing = [c.name for c in client.list_collections()]
        if collection_name not in existing:
            return 0
        collection = client.get_collection(collection_name)
        return collection.count()
    except Exception as exc:
        logger.error("ChromaDB verification error: %s", exc)
        return -1


def main() -> int:
    """Run ingestion and verify the result.

    Returns 0 on success, 1 on failure.
    """
    import os  # noqa: PLC0415

    chroma_db_path = os.environ.get("CHROMA_DB_PATH", "/data/chroma_db")
    collection_name = os.environ.get("CHROMA_COLLECTION_NAME", "tn_gov_schemes")
    data_dir = os.environ.get("DATA_DIR", "/data")

    logger.info("=" * 60)
    logger.info("TN Gov AI — One-Time Vector Store Initialization")
    logger.info("=" * 60)
    logger.info("ChromaDB path  : %s", chroma_db_path)
    logger.info("Collection     : %s", collection_name)
    logger.info("Data directory : %s", data_dir)
    logger.info("Expected chunks: %d", EXPECTED_CHUNK_COUNT)
    logger.info("=" * 60)

    # Pre-check: is there already a valid index?
    pre_count = _verify_chroma(chroma_db_path, collection_name)
    if pre_count == EXPECTED_CHUNK_COUNT:
        logger.info(
            "ChromaDB already initialized with %d chunks. "
            "Skipping re-ingestion. Use 'ingestion.cli clear' first if you "
            "need to re-index.",
            pre_count,
        )
        return 0

    if pre_count > 0:
        logger.warning(
            "ChromaDB contains %d chunks (expected %d). "
            "Proceeding with re-ingestion — clear first if needed.",
            pre_count,
            EXPECTED_CHUNK_COUNT,
        )

    # Run ingestion pipeline
    logger.info("Running ingestion pipeline...")
    cmd = [
        sys.executable,
        "-m",
        "ingestion.cli",
        "ingest",
        "--data-dir",
        data_dir,
        "--force",
    ]
    logger.info("Command: %s", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=False, text=True)  # noqa: S603

    if result.returncode != 0:
        logger.error("Ingestion pipeline exited with code %d", result.returncode)
        return 1

    # Post-ingestion verification
    logger.info("Ingestion complete. Verifying chunk count...")
    post_count = _verify_chroma(chroma_db_path, collection_name)

    if post_count == EXPECTED_CHUNK_COUNT:
        logger.info("=" * 60)
        logger.info("SUCCESS: ChromaDB initialized.")
        logger.info("  Collection : %s", collection_name)
        logger.info("  Chunks     : %d (expected %d)", post_count, EXPECTED_CHUNK_COUNT)
        logger.info("=" * 60)
        logger.info("The application server will pass startup validation.")
        return 0

    logger.error("=" * 60)
    logger.error("FAILURE: Chunk count mismatch after ingestion.")
    logger.error("  Actual count  : %d", post_count)
    logger.error("  Expected count: %d", EXPECTED_CHUNK_COUNT)
    logger.error(
        "ACTION: Check that all 31 source documents are present in DATA_DIR=%s",
        data_dir,
    )
    logger.error("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())
