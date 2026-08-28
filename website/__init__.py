"""The site generator.

Where this project keeps its files, written once. The generator, the scripts
that produce what it reads, and the tests all resolve them from here, so a
directory that moves is one edit rather than a search across eleven files.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "dataset"
INDEX_FILE = ROOT / "metadata" / "site-index.json"
MIPLIB_FILE = ROOT / "metadata" / "miplib_meta.json"

__all__ = ["DATASET_DIR", "INDEX_FILE", "MIPLIB_FILE", "ROOT"]
