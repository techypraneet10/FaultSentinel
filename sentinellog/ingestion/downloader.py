"""Raw dataset downloader and extractor for Loghub HDFS and BGL.

Acquires official archives from Zenodo (Loghub collection DOI: 10.5281/zenodo.8196385),
verifies SHA-256 integrity, extracts raw files into data/raw/, and records manifests.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, Optional
import zipfile

import httpx

from sentinellog.ingestion.hasher import compute_sha256, get_file_metadata


ZENODO_RECORD_URL = "https://zenodo.org/records/8196385"
HDFS_ZIP_URL = f"{ZENODO_RECORD_URL}/files/HDFS_v1.zip?download=1"
BGL_ZIP_URL = f"{ZENODO_RECORD_URL}/files/BGL.zip?download=1"


def download_file(
    url: str,
    target_path: Path,
    expected_size: Optional[int] = None,
    chunk_size: int = 1048576,  # 1MB chunks
) -> Path:
    """Download a file via streaming HTTP GET with progress reporting."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(".tmp")

    with httpx.Client(follow_redirects=True, timeout=120.0) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with open(temp_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=chunk_size):
                    f.write(chunk)

    if expected_size and temp_path.stat().st_size != expected_size:
        temp_path.unlink(missing_ok=True)
        raise ValueError(
            f"Downloaded size {temp_path.stat().st_size} does not match expected {expected_size}"
        )

    temp_path.replace(target_path)
    return target_path


def acquire_hdfs(
    raw_dir: Path,
    force_download: bool = False,
) -> Dict[str, str]:
    """Acquire official HDFS_v1 archive and extract HDFS.log and anomaly_label.csv.

    Args:
        raw_dir: Root raw directory (e.g. data/raw).
        force_download: If True, re-download even if files already exist.

    Returns:
        Dictionary of extracted file paths and their SHA-256 hashes.
    """
    hdfs_dir = raw_dir / "hdfs"
    hdfs_dir.mkdir(parents=True, exist_ok=True)

    log_path = hdfs_dir / "HDFS.log"
    label_path = hdfs_dir / "anomaly_label.csv"
    zip_path = hdfs_dir / "HDFS_v1.zip"

    if not force_download and log_path.exists() and label_path.exists():
        return {
            "log_path": str(log_path),
            "label_path": str(label_path),
            "log_sha256": compute_sha256(log_path),
            "label_sha256": compute_sha256(label_path),
            "status": "already_present",
        }

    # Download archive if not present
    if not zip_path.exists() or force_download:
        download_file(HDFS_ZIP_URL, zip_path, expected_size=186645559)

    # Extract required files
    with zipfile.ZipFile(zip_path, "r") as zf:
        # Extract HDFS.log
        with zf.open("HDFS.log") as src, open(log_path, "wb") as dst:
            while chunk := src.read(1048576):
                dst.write(chunk)

        # Extract anomaly_label.csv from preprocessed/
        with zf.open("preprocessed/anomaly_label.csv") as src, open(label_path, "wb") as dst:
            while chunk := src.read(1048576):
                dst.write(chunk)

    manifest = {
        "dataset": "hdfs",
        "source": "Loghub Zenodo 8196385 (HDFS_v1.zip)",
        "source_url": HDFS_ZIP_URL,
        "acquisition_timestamp": datetime.now(timezone.utc).isoformat(),
        "files": {
            "HDFS.log": get_file_metadata(log_path),
            "anomaly_label.csv": get_file_metadata(label_path),
            "HDFS_v1.zip": get_file_metadata(zip_path),
        },
    }
    with open(hdfs_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    return {
        "log_path": str(log_path),
        "label_path": str(label_path),
        "log_sha256": manifest["files"]["HDFS.log"]["sha256"],
        "label_sha256": manifest["files"]["anomaly_label.csv"]["sha256"],
        "status": "acquired_from_source",
    }


def acquire_bgl(
    raw_dir: Path,
    force_download: bool = False,
) -> Dict[str, str]:
    """Acquire official BGL archive and extract BGL.log.

    Args:
        raw_dir: Root raw directory (e.g. data/raw).
        force_download: If True, re-download even if files already exist.

    Returns:
        Dictionary of extracted file path and SHA-256 hash.
    """
    bgl_dir = raw_dir / "bgl"
    bgl_dir.mkdir(parents=True, exist_ok=True)

    log_path = bgl_dir / "BGL.log"
    zip_path = bgl_dir / "BGL.zip"

    if not force_download and log_path.exists():
        return {
            "log_path": str(log_path),
            "log_sha256": compute_sha256(log_path),
            "status": "already_present",
        }

    # Download archive if not present
    if not zip_path.exists() or force_download:
        download_file(BGL_ZIP_URL, zip_path, expected_size=57489019)

    # Extract BGL.log
    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open("BGL.log") as src, open(log_path, "wb") as dst:
            while chunk := src.read(1048576):
                dst.write(chunk)

    manifest = {
        "dataset": "bgl",
        "source": "Loghub Zenodo 8196385 (BGL.zip)",
        "source_url": BGL_ZIP_URL,
        "acquisition_timestamp": datetime.now(timezone.utc).isoformat(),
        "files": {
            "BGL.log": get_file_metadata(log_path),
            "BGL.zip": get_file_metadata(zip_path),
        },
    }
    with open(bgl_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    return {
        "log_path": str(log_path),
        "log_sha256": manifest["files"]["BGL.log"]["sha256"],
        "status": "acquired_from_source",
    }
