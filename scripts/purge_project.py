#!/usr/bin/env python3
import os
from pathlib import Path

print("=== SAFE PURGE SCRIPT ===")

# auto-detect project root (parent of /scripts)
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent

print(f"Project root detected: {ROOT}")
print("----------------------------------")

# -------------------------------------------------------------------
# LIST OF FILE PATTERNS TO DELETE (FILES ONLY — NO FOLDER DELETION)
# -------------------------------------------------------------------
PATTERNS = [
    "VALIDATION_REPORT.txt",
    "gee_project_config.txt",
    "venv/*",  # deletes content inside, not folder
    "temp/factors/*.tif",
    "temp/factors/*.log",
    "temp/erosion/*.tif",
    "temp/erosion/*.log",
    "temp/aoi/*.tif",

    "outputs/temporal/*.tif",
    "outputs/temporal/*.png",
    "outputs/temporal/*.csv",
    "outputs/temporal/arrays/*.npy",

    "outputs/statistics/**/*.csv",
    "outputs/maps/*.png",
    "outputs/figures/**/*.png",
    "outputs/logs/*.log",
]

# -------------------------------------------------------------------
# DELETE ONLY FILES, NEVER FOLDERS
# -------------------------------------------------------------------
deleted = 0

for pattern in PATTERNS:
    full_pattern = ROOT / pattern
    for path in ROOT.glob(pattern):
        try:
            if path.is_file():
                path.unlink()
                print(f"[DEL] {path}")
                deleted += 1

            elif path.is_dir():
                # delete contents only
                for file in path.glob("*"):
                    if file.is_file():
                        file.unlink()
                        print(f"[DEL] {file}")
                        deleted += 1
                    # do NOT delete directories
                print(f"[SAFE] Skipped directory delete: {path}")

        except Exception as e:
            print(f"[ERROR] {path} -> {e}")

print("----------------------------------")
print(f"Total files deleted: {deleted}")
print("SAFE PURGE COMPLETE ✓")
