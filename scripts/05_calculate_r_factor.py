#!/usr/bin/env python3
"""
RUSLE R-Factor (Rainfall Erosivity) from CHIRPS annual totals (mm)
Hardened, AOI-first, DEM-aligned, strict nodata.

Inputs (expected)
-----------------
- DEM (master grid):             temp/dem_srtm_90m.tif
- Annual rainfall totals (mm):   temp/factors/rain_total_YYYY.tif
- Preferred AOI raster:          temp/aoi/aoi_mask.tif  (0/1; same grid as DEM)
- Fallback AOI shapefile:        catchment/Mula_Mutha_Catchment.shp

Outputs
-------
- temp/factors/r_factor_YYYY.tif
- outputs/figures/r_factor_YYYY.png
- outputs/statistics/r_factor_stats_YYYY.csv
- outputs/statistics/r_factor_stats_<timestamp>.csv   (master)
"""

import sys
import csv
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio
from rasterio import warp
from rasterio.enums import Resampling
from rasterio.features import rasterize

# -----------------------------------------------------------------------------#
# Project paths / defaults (overridden by scripts/config.py if present)
# -----------------------------------------------------------------------------#
BASE_DIR    = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / "scripts"

DEM_PATH    = BASE_DIR / "temp" / "dem_srtm_90m.tif"
FACTORS_DIR = BASE_DIR / "temp" / "factors"
FIGURES_DIR = BASE_DIR / "outputs" / "figures"
STATS_DIR   = BASE_DIR / "outputs" / "statistics"

AOI_RASTER  = BASE_DIR / "temp" / "aoi" / "aoi_mask.tif"   # preferred
AOI_SHP     = BASE_DIR / "catchment" / "Mula_Mutha_Catchment.shp"

YEARS       = list(range(2016, 2026))  # 2016..2025
RAIN_PATTERN = "rain_total_{Y}.tif"    # inside FACTORS_DIR

# PNG (display only)
PNG_PERCENTILE_MAX = 98.0
PNG_CMAP = "Blues"

# R = a * P^b  (P in mm). Document output unit explicitly.
R_COEFF_A = 0.35
R_COEFF_B = 1.00
R_FORMULA_NAME = "PowerLaw_R=a*P^b"
R_OUTPUT_UNIT  = "arbitrary-R (set via a,b)"  # override via config

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
NODATA_F = -9999.0

# Try to import config overrides
try:
    sys.path.insert(0, str(SCRIPTS_DIR))
    import config as _cfg  # type: ignore
    DEM_PATH     = getattr(_cfg, "DEM_PATH", DEM_PATH)
    FACTORS_DIR  = getattr(_cfg, "FACTORS_DIR", FACTORS_DIR)
    FIGURES_DIR  = getattr(_cfg, "FIGURES_DIR", FIGURES_DIR)
    STATS_DIR    = getattr(_cfg, "STATS_DIR", STATS_DIR)
    AOI_SHP      = getattr(_cfg, "CATCHMENT_SHP", AOI_SHP)
    R_COEFF_A    = getattr(_cfg, "R_COEFF_A", R_COEFF_A)
    R_COEFF_B    = getattr(_cfg, "R_COEFF_B", R_COEFF_B)
    R_FORMULA_NAME = getattr(_cfg, "R_FORMULA_NAME", R_FORMULA_NAME)
    R_OUTPUT_UNIT  = getattr(_cfg, "R_OUTPUT_UNIT", R_OUTPUT_UNIT)
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

# Ensure dirs
FACTORS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
STATS_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------#
# Logging
# -----------------------------------------------------------------------------#
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_logfile = FACTORS_DIR / f"05_r_factor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
for h in (logging.FileHandler(_logfile, encoding="utf-8"),
          logging.StreamHandler(sys.stdout)):
    h.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(h)

# -----------------------------------------------------------------------------#
# Helpers
# -----------------------------------------------------------------------------#
def read_raster(path: Path):
    with rasterio.open(path) as src:
        arr = src.read(1)
        prof = src.profile
    return arr, prof

def reproject_to_match(source_arr, source_prof, match_prof, resampling=Resampling.bilinear):
    """Reproject/Resample source into the exact grid of match_prof."""
    dst = np.full((match_prof["height"], match_prof["width"]), NODATA_F, dtype=np.float32)
    warp.reproject(
        source=source_arr.astype(np.float32),
        destination=dst,
        src_transform=source_prof["transform"],
        src_crs=source_prof["crs"],
        dst_transform=match_prof["transform"],
        dst_crs=match_prof["crs"],
        src_nodata=source_prof.get("nodata", None),
        dst_nodata=NODATA_F,
        resampling=resampling,
    )
    return dst

def load_aoi_mask(match_prof):
    """
    Prefer raster AOI (exact DEM grid) if present, else rasterize shapefile.
    Returns boolean mask (True=inside AOI) or None.
    """
    # Preferred: raster AOI aligned to DEM grid
    if AOI_RASTER.exists():
        try:
            with rasterio.open(AOI_RASTER) as msrc:
                aoi = msrc.read(1)
                aoi_prof = msrc.profile
            # If raster AOI grid differs for any reason, reproject to match
            if (aoi.shape != (match_prof["height"], match_prof["width"])) or \
               (aoi_prof.get("crs") != match_prof.get("crs")) or \
               (aoi_prof.get("transform") != match_prof.get("transform")):
                tmp_src_prof = {
                    "transform": aoi_prof["transform"],
                    "crs": aoi_prof["crs"],
                    "height": aoi.shape[0],
                    "width": aoi.shape[1],
                    "nodata": 0
                }
                aoi = reproject_to_match(aoi, tmp_src_prof, match_prof, resampling=Resampling.nearest)
            aoi_mask = (aoi > 0).astype(bool)
            logger.info("AOI mask loaded: aoi_mask.tif (preferred raster)")
            return aoi_mask
        except Exception as e:
            logger.warning(f"Failed to use raster AOI, will try shapefile: {e}")

    # Fallback: shapefile
    if AOI_SHP.exists():
        try:
            import geopandas as gpd
            gdf = gpd.read_file(AOI_SHP)
            if gdf.crs is None or str(gdf.crs) != str(match_prof["crs"]):
                gdf = gdf.to_crs(match_prof["crs"])
            shapes = [(geom, 1) for geom in gdf.geometry if geom is not None]
            if not shapes:
                return None
            mask = rasterize(
                shapes=shapes,
                out_shape=(match_prof["height"], match_prof["width"]),
                transform=match_prof["transform"],
                fill=0, dtype="uint8", all_touched=False
            )
            logger.info("AOI mask rasterized from shapefile (fallback)")
            return mask.astype(bool)
        except Exception as e:
            logger.warning(f"AOI mask not applied: {e}")
            return None

    return None

def compute_r_from_p(p_mm, a, b, nodata_value=NODATA_F):
    """Compute R = a * P^b, maintaining nodata where P is nodata/non-finite/negative."""
    out = np.full_like(p_mm, nodata_value, dtype=np.float32)
    good = np.isfinite(p_mm) & (p_mm != nodata_value) & (p_mm >= 0.0)
    out[good] = (a * np.power(p_mm[good], b, dtype=np.float64)).astype(np.float32)
    return out

def save_geotiff(path, data, profile):
    prof = profile.copy()
    prof.update({
        "driver": "GTiff",
        "count": 1,
        "dtype": "float32",
        "compress": "lzw",
        "nodata": NODATA_F,
        "tiled": True,
    })
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(data.astype(np.float32), 1)

def save_stats_csv(path, stats_dict):
    fields = list(stats_dict.keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerow(stats_dict)

# -----------------------------------------------------------------------------#
# Main
# -----------------------------------------------------------------------------#
def main():
    logger.info("")
    logger.info("=" * 80)
    logger.info("RUSLE R-FACTOR CALCULATION (from CHIRPS annual totals, mm)")
    logger.info("=" * 80)
    logger.info(f"Formula: {R_FORMULA_NAME}   R = a * P^b   (a={R_COEFF_A}, b={R_COEFF_B})")
    logger.info(f"R units: {R_OUTPUT_UNIT}")

    # DEM (master grid)
    if not DEM_PATH.exists():
        logger.error(f"DEM not found: {DEM_PATH}")
        return False
    dem, dem_prof = read_raster(DEM_PATH)
    if dem_prof.get("nodata", None) is None:
        dem_prof["nodata"] = NODATA_F
    logger.info(f"DEM grid: CRS={dem_prof['crs']}  shape={dem.shape}  nodata={dem_prof.get('nodata')}")

    # AOI mask (prefer raster, else shp)
    aoi_mask = load_aoi_mask(dem_prof)
    if aoi_mask is None:
        logger.info("AOI mask: not applied (missing/unreadable).")
        aoi_pixels = dem.size
    else:
        aoi_pixels = int(aoi_mask.sum())
        logger.info(f"AOI pixels: {aoi_pixels} / {dem.size} ({aoi_pixels/dem.size*100.0:.2f}%)")

    master_rows = []

    for y in YEARS:
        rain_path = FACTORS_DIR / RAIN_PATTERN.format(Y=y)
        if not rain_path.exists():
            logger.warning(f"Skipping {y}: rainfall file missing: {rain_path}")
            continue

        with rasterio.open(rain_path) as src:
            p_arr = src.read(1)
            p_prof = src.profile

        # Reproject rainfall to DEM grid if needed (kept robust)
        if (p_prof["crs"] != dem_prof["crs"]) or (p_arr.shape != dem.shape) or (p_prof["transform"] != dem_prof["transform"]):
            logger.info(f"Reprojecting rainfall {y} to DEM grid (bilinear)…")
            p_match = reproject_to_match(p_arr, p_prof, dem_prof, resampling=Resampling.bilinear)
        else:
            p_match = p_arr.astype(np.float32)

        # Apply AOI mask before stats & R (strict)
        if aoi_mask is not None:
            p_match[~aoi_mask] = NODATA_F

        # Enforce DEM nodata footprint
        if dem_prof.get("nodata", None) is not None:
            p_match[dem == dem_prof["nodata"]] = NODATA_F

        # Rainfall stats (AOI-only)
        p_valid = (p_match != NODATA_F) & np.isfinite(p_match)
        if p_valid.any():
            p_vals = p_match[p_valid]
            p_stats = {
                "p_min_mm": float(p_vals.min()),
                "p_mean_mm": float(p_vals.mean()),
                "p_median_mm": float(np.median(p_vals)),
                "p_max_mm": float(p_vals.max()),
                "p_std_mm": float(p_vals.std()),
                "p_count": int(p_vals.size),
                "p_coverage_pct": float(p_vals.size / (aoi_pixels if aoi_mask is not None else p_match.size) * 100.0),
            }
        else:
            logger.error(f"No valid rainfall pixels for {y}.")
            continue

        # Compute R
        r_arr = compute_r_from_p(p_match, a=R_COEFF_A, b=R_COEFF_B, nodata_value=NODATA_F)

        # R stats (AOI-only)
        r_valid = (r_arr != NODATA_F) & np.isfinite(r_arr)
        if r_valid.any():
            r_vals = r_arr[r_valid]
            stats = {
                "year": y,
                # R stats
                "r_min": float(r_vals.min()),
                "r_mean": float(r_vals.mean()),
                "r_median": float(np.median(r_vals)),
                "r_max": float(r_vals.max()),
                "r_std": float(r_vals.std()),
                "r_count": int(r_vals.size),
                "r_coverage_pct": float(r_vals.size / (aoi_pixels if aoi_mask is not None else r_arr.size) * 100.0),
                # P stats (for traceability)
                **p_stats,
                # Meta
                "formula": R_FORMULA_NAME,
                "a": float(R_COEFF_A),
                "b": float(R_COEFF_B),
                "unit_P": "mm",
                "unit_R": R_OUTPUT_UNIT,
            }
            logger.info(
                f"R stats {y} (AOI-only): R[min={stats['r_min']:.3f}, mean={stats['r_mean']:.3f}, "
                f"med={stats['r_median']:.3f}, max={stats['r_max']:.3f}, std={stats['r_std']:.3f}], "
                f"P[min={stats['p_min_mm']:.1f}, mean={stats['p_mean_mm']:.1f}, max={stats['p_max_mm']:.1f}] "
                f"coverage={stats['r_coverage_pct']:.2f}%"
            )
        else:
            logger.error(f"No valid R pixels for {y}.")
            continue

        # Save GeoTIFF
        out_tif = FACTORS_DIR / f"r_factor_{y}.tif"
        out_prof = dem_prof.copy()
        out_prof.update({"dtype": "float32", "nodata": NODATA_F})
        save_geotiff(out_tif, r_arr, out_prof)
        logger.info(f"Saved R raster: {out_tif}")

        # Save per-year stats CSV
        out_csv = STATS_DIR / f"r_factor_stats_{y}.csv"
        save_stats_csv(out_csv, stats)
        logger.info(f"Saved R stats CSV: {out_csv}")

        # PNG (display-only; 98th percentile cap)
        try:
            import matplotlib.pyplot as plt
            fig_path = FIGURES_DIR / f"r_factor_{y}.png"
            view = np.where(r_arr <= 0, np.nan, r_arr)
            vmax = float(np.nanpercentile(view, PNG_PERCENTILE_MAX))
            plt.figure(figsize=(10, 7))
            im = plt.imshow(view, cmap=PNG_CMAP, vmin=0.0, vmax=vmax)
            plt.title(f"R-Factor {y} ({R_FORMULA_NAME}, a={R_COEFF_A}, b={R_COEFF_B})")
            cbar = plt.colorbar(im, shrink=0.8)
            cbar.set_label(f"R ({R_OUTPUT_UNIT})")
            plt.xlabel("pixels (lon)")
            plt.ylabel("pixels (lat)")
            plt.tight_layout()
            plt.savefig(fig_path, dpi=150)
            plt.close()
            logger.info(f"Saved R figure: {fig_path}")
        except Exception as e:
            logger.warning(f"Could not create PNG for {y}: {e}")

        master_rows.append(stats)

    # Master stats CSV
    if master_rows:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        master_csv = STATS_DIR / f"r_factor_stats_{ts}.csv"
        fields = list(master_rows[0].keys())
        with open(master_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in master_rows:
                w.writerow(row)
        logger.info(f"Saved master R stats CSV: {master_csv}")

    logger.info("R-factor computation completed.")
    logger.info("=" * 80)
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
