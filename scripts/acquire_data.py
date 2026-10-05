"""Script to acquire official Loghub HDFS and BGL datasets."""

import argparse
from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sentinellog.ingestion.downloader import acquire_bgl, acquire_hdfs


def main():
    parser = argparse.ArgumentParser(description="Acquire raw Loghub datasets")
    parser.add_argument(
        "--dataset",
        choices=["hdfs", "bgl", "all"],
        default="all",
        help="Dataset to download (hdfs, bgl, or all)",
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default="data/raw",
        help="Directory to save raw datasets",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if files already exist",
    )
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    print(f"Acquiring datasets into: {raw_dir.resolve()}")

    if args.dataset in ("hdfs", "all"):
        print("Acquiring HDFS dataset from official Loghub Zenodo repository...")
        hdfs_res = acquire_hdfs(raw_dir, force_download=args.force)
        print(f"HDFS acquired: log={hdfs_res['log_path']} (SHA-256: {hdfs_res['log_sha256']})")
        print(f"HDFS labels: label={hdfs_res['label_path']} (SHA-256: {hdfs_res['label_sha256']})")

    if args.dataset in ("bgl", "all"):
        print("Acquiring BGL dataset from official Loghub Zenodo repository...")
        bgl_res = acquire_bgl(raw_dir, force_download=args.force)
        print(f"BGL acquired: log={bgl_res['log_path']} (SHA-256: {bgl_res['log_sha256']})")


if __name__ == "__main__":
    main()
