#!/usr/bin/env python3
"""
RUSLE Project 2016-2025: Environment & Data Validation (Single-file, ASCII-only)
-------------------------------------------------------------------------------

- ASCII-only console output (Windows-friendly)
- No external local imports
- Reads GEE project ID from BASE_DIR/gee_project_config.txt if present
- Falls back to env var GEE_PROJECT_ID, then to ee.Initialize() without project
- Creates all folders needed by later scripts (00..08)

Run:
    python scripts/01_environment_validation.py
"""

import sys
import os
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------
# Simple printing helpers (ASCII only)
# ---------------------------------------------------------------------
def heading(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70 + "\n")

def section(title: str):
    print("\n" + "-" * 70)
    print(title)
    print("-" * 70 + "\n")

def ok(msg: str):
    print(f"OK    {msg}")

def fail(msg: str):
    print(f"FAIL  {msg}")

def warn(msg: str):
    print(f"WARN  {msg}")

def info(msg: str):
    print(f"INFO  {msg}")

BASE_DIR = Path(__file__).parent.parent

# ---------------------------------------------------------------------
# 1) Python version
# ---------------------------------------------------------------------
def check_python_version():
    heading("1. PYTHON VERSION CHECK")
    v = sys.version_info
    vstr = f"{v.major}.{v.minor}.{v.micro}"
    info(f"Python version: {vstr}")
    info(f"Executable: {sys.executable}")
    if v.major >= 3 and v.minor >= 8:
        ok(f"Python {vstr} is compatible (>= 3.8 required)")
        return True
    fail(f"Python {vstr} is too old (>= 3.8 required)")
    return False

# ---------------------------------------------------------------------
# 2) Required packages
# ---------------------------------------------------------------------
def check_required_packages():
    heading("2. PYTHON PACKAGES CHECK")
    # Aligned with your requirements.txt
    required_core = {
        "numpy": "numpy",
        "pandas": "pandas",
        "geopandas": "geopandas",
        "rasterio": "rasterio",
        "fiona": "fiona",
        "shapely": "shapely",
        "pyproj": "pyproj",
        "scipy": "scipy",
        "ee": "earthengine-api",
        "geemap": "geemap",
        "whitebox": "whitebox",
        "matplotlib": "matplotlib",
        "seaborn": "seaborn",
        "plotly": "plotly",
        "tqdm": "tqdm",
        "dotenv": "python-dotenv",
    }
    optional = {
        "ipykernel": "ipykernel",
        "jupyter": "jupyter",
    }

    all_ok = True
    installed = 0

    for mod, pkgname in required_core.items():
        try:
            m = __import__(mod)
            ver = getattr(m, "__version__", "unknown")
            ok(f"{pkgname:20s} version {ver}")
            installed += 1
        except Exception:
            fail(f"{pkgname:20s} NOT INSTALLED")
            all_ok = False

    # Optional packages: do not fail the run
    for mod, pkgname in optional.items():
        try:
            m = __import__(mod)
            ver = getattr(m, "__version__", "unknown")
            ok(f"{pkgname:20s} version {ver} (optional)")
        except Exception:
            info(f"{pkgname:20s} not installed (optional)")

    print("\nSummary:")
    print(f"Installed {installed} of {len(required_core)} required packages")
    return all_ok

# ---------------------------------------------------------------------
# 3) System resources
# ---------------------------------------------------------------------
def check_system_resources():
    heading("3. SYSTEM RESOURCES CHECK")
    # Disk
    try:
        import shutil
        total, used, free = shutil.disk_usage(Path.home())
        total_gb = total / (1024**3)
        free_gb = free / (1024**3)
        used_pct = used / total * 100.0
        info(f"Disk total: {total_gb:.2f} GB")
        info(f"Disk used:  {used_pct:.1f}%")
        info(f"Disk free:  {free_gb:.2f} GB")
        if free_gb >= 10:
            ok("Sufficient disk space (>= 10 GB)")
        else:
            warn("Low disk space (< 10 GB) - processing may fail later")
    except Exception as e:
        fail(f"Could not check disk space: {e}")

    # RAM
    try:
        import psutil
        total_gb = psutil.virtual_memory().total / (1024**3)
        info(f"RAM total: {total_gb:.2f} GB")
        if total_gb >= 8:
            ok("Sufficient RAM (>= 8 GB)")
        else:
            warn("Low RAM (< 8 GB) - processing may be slow or fail")
    except Exception:
        info("psutil not installed; skipping RAM check")

    # CPU
    try:
        import multiprocessing
        cores = multiprocessing.cpu_count()
        info(f"CPU cores: {cores}")
        if cores >= 4:
            ok("Good CPU count (>= 4 cores)")
        else:
            info("Performance may be slow on low-core systems")
    except Exception as e:
        fail(f"Could not check CPU cores: {e}")

    return True

# ---------------------------------------------------------------------
# 4) Directory structure
# ---------------------------------------------------------------------
def check_directory_structure():
    heading("4. DIRECTORY STRUCTURE CHECK")
    required_dirs = [
        "catchment",
        "data",
        "temp",
        "temp/dem",
        "temp/aoi",
        "temp/factors",
        "outputs",
        "outputs/figures",
        "outputs/figures/temporal",
        "outputs/maps",
        "outputs/web_maps",
        "outputs/statistics",
        "outputs/statistics/temporal",
        "outputs/logs",
        "outputs/temporal",
        "outputs/temporal/arrays",
        "scripts",
    ]
    all_ok = True
    for rel in required_dirs:
        p = BASE_DIR / rel
        if p.exists():
            ok(rel)
        else:
            info(f"{rel} missing; creating...")
            try:
                p.mkdir(parents=True, exist_ok=True)
                ok(f"Created {rel}")
            except Exception as e:
                fail(f"Could not create {rel}: {e}")
                all_ok = False
    return all_ok

# ---------------------------------------------------------------------
# 5) Catchment shapefile
# ---------------------------------------------------------------------
def check_catchment_shapefile():
    heading("5. CATCHMENT SHAPEFILE VALIDATION")
    try:
        import geopandas as gpd
    except Exception:
        fail("geopandas not installed")
        return False

    shp_list = list((BASE_DIR / "catchment").glob("*.shp"))
    if not shp_list:
        fail("No shapefile found in catchment/")
        return False

    shp = shp_list[0]
    info(f"Found shapefile: {shp.name}")
    try:
        gdf = gpd.read_file(shp)
        info(f"Features: {len(gdf)}")
        info(f"CRS: {gdf.crs}")
        if gdf.crs is None:
            fail("Shapefile has no CRS")
            return False
        ok("Shapefile loaded successfully")
        return True
    except Exception as e:
        fail(f"Error reading shapefile: {e}")
        return False

# ---------------------------------------------------------------------
# 6) DEM file (robust, with fallback)
# ---------------------------------------------------------------------
def _pick_dem_path():
    # Prefer aligned DEM if present, else fallback to srtm_90m
    dem_aligned = BASE_DIR / "temp" / "dem" / "dem_90m_aligned.tif"
    dem_legacy  = BASE_DIR / "temp" / "dem_srtm_90m.tif"
    if dem_aligned.exists():
        return dem_aligned, "aligned"
    if dem_legacy.exists():
        return dem_legacy, "legacy"
    return None, None

def check_dem_file():
    heading("6. DEM FILE VALIDATION")
    try:
        import rasterio
        import numpy as np
    except Exception:
        fail("rasterio/numpy not installed")
        return False

    dem_path, dem_kind = _pick_dem_path()
    if dem_path is None:
        fail("DEM file missing. Expected one of:\n"
             "      temp/dem/dem_90m_aligned.tif  (preferred)\n"
             "      temp/dem_srtm_90m.tif         (fallback)")
        return False

    info(f"Using DEM: {dem_path} ({dem_kind})")
    try:
        with rasterio.open(dem_path) as src:
            info(f"Size: {src.width} x {src.height}")
            info(f"CRS:  {src.crs}")
            info(f"Transform: {src.transform}")
            nodata = src.nodata
            if nodata is None:
                warn("DEM nodata is missing; downstream scripts will treat 'finite()' as valid area.")
            else:
                info(f"Nodata: {nodata}")

            # Pixel size sanity (approx 90m at equator is ~0.000833333 deg)
            px_x = abs(src.transform.a)
            px_y = abs(src.transform.e)
            info(f"Pixel size (deg): {px_x:.9f} x {px_y:.9f}")
            if not (0.0006 <= px_x <= 0.0012):
                warn("DEM pixel size not ~0.00083 deg (approx 90m). Ensure all factors match this grid.")
            if str(src.crs).upper() != "EPSG:4326":
                warn("DEM CRS is not EPSG:4326; reproject/align before analysis.")

            # Lightweight range check
            arr = src.read(1)
            finite = arr[np.isfinite(arr)]
            if finite.size > 0:
                info(f"Elevation sample range: {np.nanmin(finite):.2f} .. {np.nanmax(finite):.2f} meters")
            else:
                warn("DEM has no finite values in band 1.")
        ok("DEM validation completed")
        return True
    except Exception as e:
        fail(f"Error reading DEM: {e}")
        return False

# ---------------------------------------------------------------------
# 7) GEE init
# ---------------------------------------------------------------------
def _read_saved_project_id():
    cfg = BASE_DIR / "gee_project_config.txt"
    if cfg.exists():
        try:
            text = cfg.read_text(encoding="utf-8").strip()
            if "=" in text:
                # Accept legacy "project_id=xxx" but suggest keeping raw ID only
                key, val = text.split("=", 1)
                warn("gee_project_config.txt contains 'project_id=' prefix. "
                     "This is accepted, but please store only the raw ID.")
                return val.strip()
            return text
        except Exception:
            return None
    env_val = os.environ.get("GEE_PROJECT_ID")
    if env_val:
        return env_val.strip()
    return None

def check_google_earth_engine():
    heading("7. GOOGLE EARTH ENGINE CHECK")
    try:
        import ee
    except Exception:
        fail("earthengine-api not installed")
        return False

    project_id = _read_saved_project_id()
    if project_id:
        info(f"Using saved GEE project: {project_id}")
        try:
            ee.Initialize(project=project_id)
            ok(f"Google Earth Engine initialized using project '{project_id}'")
            return True
        except Exception as e:
            fail(f"GEE initialization failed with saved project '{project_id}': {e}")

    try:
        info("Attempting fallback: ee.Initialize() without project")
        ee.Initialize()
        ok("Google Earth Engine initialized without explicit project")
        return True
    except Exception as e:
        fail(f"Google Earth Engine initialization failed: {e}")
        info("Run: python scripts/00_gee_setup.py")
        return False

# ---------------------------------------------------------------------
# 8) Config files
# ---------------------------------------------------------------------
def check_config_files():
    heading("8. CONFIGURATION FILES CHECK")
    files = [
        "scripts/config.py",
        "scripts/color_config.py",
        "requirements.txt",
        "README.md",
    ]
    all_ok = True
    for f in files:
        p = BASE_DIR / f
        if p.exists():
            ok(f)
        else:
            fail(f"{f} missing")
            all_ok = False
    return all_ok

# ---------------------------------------------------------------------
# 9) Catchment vs DEM quick spatial sanity
# ---------------------------------------------------------------------
def check_aoi_vs_dem_overlap():
    heading("9. AOI VS DEM OVERLAP CHECK (QUICK)")
    try:
        import geopandas as gpd
        import rasterio
        from shapely.geometry import box
    except Exception:
        info("Dependencies for overlap check missing; skipping.")
        return True  # Do not fail, this is advisory

    shp_list = list((BASE_DIR / "catchment").glob("*.shp"))
    if not shp_list:
        info("No shapefile found; skipping overlap check.")
        return True

    dem_path, _ = _pick_dem_path()
    if dem_path is None:
        info("No DEM found; skipping overlap check.")
        return True

    try:
        gdf = gpd.read_file(shp_list[0])
        aoiminx, aoiminy, aoimax, aoimaxy = gdf.total_bounds

        with rasterio.open(dem_path) as src:
            dem_bounds = src.bounds
            dem_box = box(dem_bounds.left, dem_bounds.bottom, dem_bounds.right, dem_bounds.top)
            aoi_box = box(aoiminx, aoiminy, aoimax, aoimaxy)

            if not dem_box.intersects(aoi_box):
                warn("AOI and DEM do NOT overlap. Check CRS and extents.")
            else:
                ok("AOI and DEM extents overlap.")
        return True
    except Exception as e:
        warn(f"Overlap check skipped due to error: {e}")
        return True

# ---------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------
def generate_validation_report(results: dict):
    heading("10. GENERATING VALIDATION REPORT")
    report = BASE_DIR / "VALIDATION_REPORT.txt"
    try:
        with open(report, "w", encoding="utf-8") as f:
            f.write("RUSLE PROJECT VALIDATION REPORT\n")
            f.write("=" * 70 + "\n\n")
            for key, val in results.items():
                f.write(f"{key:30s} : {'PASS' if val else 'FAIL'}\n")
            f.write("\n" + "=" * 70 + "\n")
            f.write(f"Summary: {sum(results.values())}/{len(results)} checks passed\n")
        ok(f"Report saved to {report}")
        return True
    except Exception as e:
        fail(f"Could not write report: {e}")
        return False

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main():
    print("\nRUSLE PROJECT 2016-2025 ENVIRONMENT VALIDATION\n")

    results = {
        "Python Version":      check_python_version(),
        "Python Packages":     check_required_packages(),
        "System Resources":    check_system_resources(),
        "Directory Structure": check_directory_structure(),
        "Catchment Shapefile": check_catchment_shapefile(),
        "DEM File":            check_dem_file(),
        "Google Earth Engine": check_google_earth_engine(),
        "Configuration Files": check_config_files(),
        "AOI vs DEM Overlap":  check_aoi_vs_dem_overlap(),
    }

    generate_validation_report(results)

    section("VALIDATION SUMMARY")
    for k, v in results.items():
        if v:
            ok(k)
        else:
            fail(k)

    print("\nSummary:", sum(results.values()), "/", len(results), "checks passed")
    if all(results.values()):
        print("\nSystem is ready for RUSLE analysis.")
    else:
        print("\nOne or more checks failed. Fix issues and run again.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
