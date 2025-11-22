#!/usr/bin/env python3
"""
verify_setup.py — quick post-setup audit for RUSLE repo

Usage:
    python scripts/verify_setup.py
    python scripts/verify_setup.py --touch-readmes   # adds README.txt to empty dirs
"""
from pathlib import Path
import sys
import argparse

BASE = Path(__file__).resolve().parents[1]

DIRS = {
    "catchment": "Contains your AOI shapefile (e.g., Mula_Mutha_Catchment.shp).",
    "temp/dem": "Optional home for DEM files (you currently use temp/dem_srtm_90m.tif).",
    "temp/aoi": "Will hold rasterized AOI mask after step 02.",
    "temp/factors": "Intermediate rasters for K/LS/C/R/P during steps 02–06.",
    "outputs/figures": "PNG figures for factors and temporal plots.",
    "outputs/figures/temporal": "Year-to-year change plots and trend maps.",
    "outputs/maps": "Static map exports (GeoTIFF/PNGs).",
    "outputs/web_maps": "Leaflet/Folium web maps if enabled.",
    "outputs/statistics": "CSV stats for factors and temporal summaries.",
    "outputs/statistics/temporal": "CSV: change_summary/temporal_summary/trend_summary.",
    "outputs/logs": "Run logs for each step.",
    "outputs/temporal": "Slope/intercept rasters; change GeoTIFFs.",
    "outputs/temporal/arrays": "Numpy stacks (e.g., a_stack.npy).",
}

def exists(p): return (BASE / p).exists()

def fmt(ok): return "OK " if ok else "!! "

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--touch-readmes", action="store_true",
                    help="create README.txt in empty directories to keep structure visible")
    args = ap.parse_args()

    print("\nRUSLE Setup Verification\n" + "="*60)

    # 1) Confirm gee project file
    cfg = BASE / "gee_project_config.txt"
    print("\nGEE Project Config")
    print("-"*60)
    if cfg.exists():
        raw = cfg.read_text(encoding="utf-8").strip()
        print(f"{fmt(True)}gee_project_config.txt found -> '{raw}'")
    else:
        print(f"{fmt(False)}gee_project_config.txt missing (run scripts/00_gee_setup.py)")

    # 2) Folders overview
    print("\nFolder Structure")
    print("-"*60)
    for rel, desc in DIRS.items():
        p = BASE / rel
        if p.exists():
            children = list(p.iterdir())
            print(f"{fmt(True)}{rel}  ({'empty' if len(children)==0 else f'{len(children)} items'})")
            if len(children)==0:
                print(f"     ↳ Expected later: {desc}")
                if args.touch_readmes:
                    (p / "README.txt").write_text(desc + "\n", encoding="utf-8")
        else:
            print(f"{fmt(False)}{rel}  (missing) — should exist. The validator normally creates it.")

    # 3) AOI shapefile presence
    print("\nAOI Shapefile Check")
    print("-"*60)
    shp = list((BASE / "catchment").glob("*.shp"))
    if shp:
        print(f"{fmt(True)}Found AOI shapefile: {shp[0].name}")
    else:
        print(f"{fmt(False)}No .shp in catchment/. Place your AOI shapefile there.")

    # 4) DEM presence (legacy and neatly under temp/dem)
    print("\nDEM Check")
    print("-"*60)
    legacy_dem = BASE / "temp" / "dem_srtm_90m.tif"
    nested_dem = BASE / "temp" / "dem" / "dem_srtm_90m.tif"
    if legacy_dem.exists():
        print(f"{fmt(True)}DEM present at temp/dem_srtm_90m.tif (used by scripts).")
    elif nested_dem.exists():
        print(f"{fmt(True)}DEM present at temp/dem/dem_srtm_90m.tif.")
    else:
        print(f"{fmt(False)}DEM not found. Expected at temp/dem_srtm_90m.tif (or adjust config).")

    # 5) Quick pointers on what fills when
    print("\nWhat fills these folders and when")
    print("-"*60)
    print("• temp/aoi -> step 02: rasterized AOI mask")
    print("• temp/factors, outputs/statistics -> steps 02–06: K, LS, C, R, P and CSVs")
    print("• outputs/temporal, outputs/figures/temporal -> step 08: change GeoTIFFs and plots")

    print("\nDone.\n")

if __name__ == "__main__":
    sys.exit(main())
