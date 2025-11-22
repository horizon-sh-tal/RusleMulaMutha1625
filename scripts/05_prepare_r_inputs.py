#!/usr/bin/env python3
"""
Prepare CHIRPS annual rainfall rasters (mm/year) for R-factor derivation.
- Aligns CHIRPS totals to DEM grid (EPSG:4326, 90 m) with bilinear resampling
- Applies AOI mask on the DEM grid
- Enforces non-negative precipitation
- Writes cleaned rasters and a summary CSV

Inputs (expected):
- DEM: temp/dem_srtm_90m.tif
- CHIRPS exports: temp/RUSLE_CHIRPS90m/chirps_total_mm_YYYY_90m.tif
- AOI: catchment/Mula_Mutha_Catchment.shp (optional but recommended)

Outputs:
- temp/factors/rain_total_YYYY.tif           (aligned, AOI-masked, non-negative)
- outputs/statistics/r_prep_stats_<ts>.csv   (per-year stats)
- temp/factors/05_r_prep_<ts>.log            (log)
"""

import sys, os, re, csv
from pathlib import Path
from datetime import datetime
import logging
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio import warp
from rasterio.features import rasterize

# ----------------------------
# Project paths / configuration
# ----------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / "scripts"

DEM_PATH      = BASE_DIR / "temp" / "dem_srtm_90m.tif"
CHIRPS_DIR    = BASE_DIR / "temp" / "RUSLE_CHIRPS90m"
AOI_SHP       = BASE_DIR / "catchment" / "Mula_Mutha_Catchment.shp"

FACTORS_DIR   = BASE_DIR / "temp" / "factors"
FIGURES_DIR   = BASE_DIR / "outputs" / "figures"
STATS_DIR     = BASE_DIR / "outputs" / "statistics"
LOGS_DIR      = FACTORS_DIR

# Try project config (optional)
try:
    sys.path.insert(0, str(SCRIPTS_DIR))
    import config as _cfg  # type: ignore
    FACTORS_DIR = getattr(_cfg, "FACTORS_DIR", FACTORS_DIR)
    FIGURES_DIR = getattr(_cfg, "FIGURES_DIR", FIGURES_DIR)
    print("[OK] Configuration loaded successfully!")
    print("Analysis period: 2016-2025 (10 years)")
    print(f"Output directory: {BASE_DIR/'outputs'}")
    print(f"Target CRS: {getattr(_cfg, 'TARGET_CRS', 'EPSG:4326')}")
    try:
        import color_config as _cc  # type: ignore
        print("[OK] Standardized color configuration loaded")
    except Exception:
        pass
except Exception:
    print("[INFO] Using internal defaults (no scripts/config.py found)")

FACTORS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
STATS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOGS_DIR / f"05_r_prep_{ts}.log"
for h in (logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)):
    h.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(h)

# ----------------------------
# Helpers
# ----------------------------
def read_raster(path):
    with rasterio.open(path) as src:
        arr = src.read(1)
        prof = src.profile
    return arr, prof

def reproject_to_match(source_arr, source_prof, match_prof, continuous=True):
    """Reproject/Resample source into the exact grid of match_prof."""
    dst = np.full((match_prof["height"], match_prof["width"]),
                  match_prof.get("nodata", -9999.0), dtype=np.float32)
    resamp = Resampling.bilinear if continuous else Resampling.nearest
    warp.reproject(
        source=source_arr.astype(np.float32),
        destination=dst,
        src_transform=source_prof["transform"],
        src_crs=source_prof["crs"],
        dst_transform=match_prof["transform"],
        dst_crs=match_prof["crs"],
        dst_nodata=match_prof.get("nodata", -9999.0),
        resampling=resamp,
    )
    return dst

def load_aoi_mask(match_prof):
    """Rasterize AOI polygon to the target grid; return boolean mask (True=inside)."""
    if not AOI_SHP.exists():
        return None
    try:
        import geopandas as gpd
        gdf = gpd.read_file(AOI_SHP)
        if gdf.crs is None or gdf.crs.to_string() != str(match_prof["crs"]):
            gdf = gdf.to_crs(match_prof["crs"])
        shapes = [(geom, 1) for geom in gdf.geometry if geom is not None]
        if not shapes:
            return None
        mask = rasterize(
            shapes=shapes,
            out_shape=(match_prof["height"], match_prof["width"]),
            transform=match_prof["transform"],
            fill=0,
            dtype="uint8",
        )
        return mask.astype(bool)
    except Exception as e:
        logger.warning(f"AOI mask not applied: {e}")
        return None

def save_geotiff(path, data, profile):
    prof = profile.copy()
    prof.update({
        "driver": "GTiff",
        "count": 1,
        "dtype": "float32",
        "compress": "lzw",
        "nodata": -9999.0
    })
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(data.astype(np.float32), 1)

# ----------------------------
# Main
# ----------------------------
def main():
    logger.info("")
    logger.info("=" * 80)
    logger.info("PREPARING CHIRPS ANNUAL TOTALS (mm) FOR R-FACTOR")
    logger.info("=" * 80)

    # DEM
    if not DEM_PATH.exists():
        logger.error(f"DEM not found: {DEM_PATH}")
        return False
    dem, dem_prof = read_raster(DEM_PATH)
    if dem_prof.get("nodata", None) is None:
        dem_prof["nodata"] = -9999.0
    logger.info(f"DEM grid: CRS={dem_prof['crs']}  shape={dem.shape}  nodata={dem_prof['nodata']}")

    # AOI mask on DEM grid
    aoi_mask = load_aoi_mask(dem_prof)
    if aoi_mask is None:
        logger.warning("AOI mask not found; proceeding without AOI hard mask on DEM grid.")
        aoi_mask = np.ones_like(dem, dtype=bool)

    # Find CHIRPS files
    if not CHIRPS_DIR.exists():
        logger.error(f"CHIRPS directory not found: {CHIRPS_DIR}")
        return False

    chirps_files = sorted(CHIRPS_DIR.glob("chirps_total_mm_*_90m.tif"))
    if not chirps_files:
        logger.error(f"No CHIRPS files matching pattern in {CHIRPS_DIR}")
        return False

    # Prepare stats writer
    stats_rows = []
    year_re = re.compile(r"chirps_total_mm_(\d{4})_90m\.tif$")

    for tif in chirps_files:
        m = year_re.search(tif.name)
        if not m:
            logger.warning(f"Skip file (year not parsed): {tif.name}")
            continue
        year = int(m.group(1))
        arr, prof = read_raster(tif)
        logger.info(f"Processing {tif.name}: CRS={prof['crs']} shape={arr.shape}")

        # Align to DEM grid (continuous → bilinear)
        arr_match = reproject_to_match(arr, prof, dem_prof, continuous=True)

        # AOI on DEM grid + DEM nodata
        out = arr_match.copy()
        out[~aoi_mask] = -9999.0
        if dem_prof.get("nodata", None) is not None:
            out[dem == dem_prof["nodata"]] = -9999.0

        # Enforce non-negative precipitation
        valid = (out != -9999.0) & np.isfinite(out)
        neg_count = int((out[valid] < 0).sum())
        if neg_count > 0:
            logger.warning(f"{tif.name}: Found {neg_count} negative pixels; clamping to 0 mm.")
            out[valid & (out < 0)] = 0.0

        # Stats
        vals = out[valid]
        if vals.size > 0:
            row = {
                "year": year,
                "min": float(vals.min()),
                "mean": float(vals.mean()),
                "median": float(np.median(vals)),
                "max": float(vals.max()),
                "std": float(vals.std()),
                "valid_count": int(vals.size),
                "total_pixels": int(out.size),
                "coverage_pct": float(vals.size / out.size * 100.0),
                "note": "2025 is Jan–Nov only" if year == 2025 else "",
            }
            logger.info(f"CHIRPS {year} stats: min={row['min']:.2f} mean={row['mean']:.2f} "
                        f"median={row['median']:.2f} max={row['max']:.2f} std={row['std']:.2f} "
                        f"n={row['valid_count']} (coverage {row['coverage_pct']:.2f}%)")
            stats_rows.append(row)
        else:
            logger.warning(f"{tif.name}: No valid pixels after masking.")

        # Save cleaned aligned raster
        out_tif = FACTORS_DIR / f"rain_total_{year}.tif"
        out_prof = dem_prof.copy()
        out_prof.update({"dtype": "float32", "nodata": -9999.0})
        save_geotiff(out_tif, out, out_prof)
        logger.info(f"Saved: {out_tif}")

    # Write stats CSV
    stats_path = STATS_DIR / f"r_prep_stats_{ts}.csv"
    if stats_rows:
        fields = ["year","min","mean","median","max","std","valid_count","total_pixels","coverage_pct","note"]
        with open(stats_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in sorted(stats_rows, key=lambda d: d["year"]):
                w.writerow(r)
        logger.info(f"Saved stats CSV: {stats_path}")
    else:
        logger.warning("No stats rows written (no valid rasters processed?).")

    logger.info("R rainfall prep completed.")
    logger.info("=" * 80)
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
