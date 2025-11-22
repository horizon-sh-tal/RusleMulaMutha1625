# #!/usr/bin/env python3
# """
# RUSLE C-Factor (Cover-Management) from Sentinel-2 NDVI (yearly @ 90 m)
# - Uses NDVI -> C conversion: Van der Knijff et al. (2000)
#   C = exp( -ALPHA * NDVI / (BETA - NDVI) ), default ALPHA=2.0, BETA=1.0
# - Robust to odd NDVI pixels: clamps NDVI to [NDVI_MIN, NDVI_MAX] before conversion.
# - Inputs: temp/RUSLE_NDVI90m/ndvi_YYYY_90m_clean.tif (2016..2025)
# - Outputs per-year:
#     temp/factors/c_factor_YYYY.tif
#     outputs/statistics/c_factor_stats_YYYY.csv
#     outputs/figures/c_factor_YYYY.png
# """

# import sys
# import os
# from pathlib import Path
# import logging
# from datetime import datetime
# import csv

# import numpy as np
# import rasterio
# from rasterio.enums import Resampling

# # -----------------------------------------------------------------------------
# # Project paths / defaults (overridden by scripts/config.py if present)
# # -----------------------------------------------------------------------------
# BASE_DIR = Path(__file__).resolve().parents[1]
# SCRIPTS_DIR = BASE_DIR / "scripts"

# DEM_PATH       = BASE_DIR / "temp" / "dem_srtm_90m.tif"
# NDVI_DIR       = BASE_DIR / "temp" / "RUSLE_NDVI90m"
# FACTORS_DIR    = BASE_DIR / "temp" / "factors"
# FIGURES_DIR    = BASE_DIR / "outputs" / "figures"
# STATS_DIR      = BASE_DIR / "outputs" / "statistics"

# YEARS          = list(range(2016, 2026))  # 2016..2025
# # NDVI -> C parameters (Van der Knijff 2000)
# ALPHA          = 2.0
# BETA           = 1.0
# # Safe clamp for NDVI before conversion
# NDVI_MIN       = 0.0      # set <0 to allow negatives if you prefer
# NDVI_MAX       = 0.90     # keep <1.0 to avoid division by zero

# DISPLAY_MAX    = 1.0      # PNG upper color bound for C
# DISPLAY_MIN    = 0.0

# LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# # Optional project config override
# try:
#     sys.path.insert(0, str(SCRIPTS_DIR))
#     import config as _cfg  # type: ignore
#     DEM_PATH    = getattr(_cfg, "DEM_PATH", DEM_PATH)
#     FACTORS_DIR = getattr(_cfg, "FACTORS_DIR", FACTORS_DIR)
#     FIGURES_DIR = getattr(_cfg, "FIGURES_DIR", FIGURES_DIR)
#     STATS_DIR   = getattr(_cfg, "STATS_DIR", STATS_DIR)
#     ALPHA       = getattr(_cfg, "C_ALPHA", ALPHA)
#     BETA        = getattr(_cfg, "C_BETA", BETA)
#     NDVI_MIN    = getattr(_cfg, "NDVI_MIN", NDVI_MIN)
#     NDVI_MAX    = getattr(_cfg, "NDVI_MAX", NDVI_MAX)
#     print("[OK] Configuration loaded successfully!")
#     print("Analysis period: 2016-2025 (10 years)")
#     print(f"Output directory: {BASE_DIR/'outputs'}")
#     print(f"Target CRS: {getattr(_cfg, 'TARGET_CRS', 'EPSG:4326')}")
#     try:
#         import color_config as _cc  # type: ignore
#         print("[OK] Standardized color configuration loaded")
#     except Exception:
#         pass
# except Exception:
#     print("[INFO] Using internal defaults (no scripts/config.py found)")

# # Ensure dirs
# FACTORS_DIR.mkdir(parents=True, exist_ok=True)
# FIGURES_DIR.mkdir(parents=True, exist_ok=True)
# STATS_DIR.mkdir(parents=True, exist_ok=True)

# # -----------------------------------------------------------------------------
# # Logging
# # -----------------------------------------------------------------------------
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
# log_file = FACTORS_DIR / f"04_c_factor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
# handlers = [
#     logging.FileHandler(log_file, encoding="utf-8"),
#     logging.StreamHandler(sys.stdout),
# ]
# for h in handlers:
#     h.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
#     logger.addHandler(h)

# # -----------------------------------------------------------------------------
# # IO helpers
# # -----------------------------------------------------------------------------
# def read_raster(path):
#     with rasterio.open(path) as src:
#         arr = src.read(1)
#         prof = src.profile
#     return arr, prof

# def save_geotiff(path, data, profile):
#     prof = profile.copy()
#     prof.update({
#         "driver": "GTiff",
#         "count": 1,
#         "dtype": "float32",
#         "compress": "lzw",
#         "nodata": -9999.0
#     })
#     with rasterio.open(path, "w", **prof) as dst:
#         dst.write(data.astype(np.float32), 1)

# def save_stats_csv(path, stats):
#     fieldnames = list(stats.keys())
#     with open(path, "w", newline="", encoding="utf-8") as f:
#         w = csv.DictWriter(f, fieldnames=fieldnames)
#         w.writeheader()
#         w.writerow(stats)

# # -----------------------------------------------------------------------------
# # Core: NDVI -> C conversion (vectorized)
# # -----------------------------------------------------------------------------
# def ndvi_to_c(ndvi):
#     # Clamp NDVI for stable math
#     x = np.clip(ndvi, NDVI_MIN, NDVI_MAX)
#     # C = exp( -ALPHA * x / (BETA - x) )
#     denom = (BETA - x)
#     denom[denom == 0] = 1e-6
#     c = np.exp(-ALPHA * x / denom)
#     # Ensure [0,1] bounds
#     c = np.clip(c, 0.0, 1.0)
#     return c

# # -----------------------------------------------------------------------------
# # Main per-year processing
# # -----------------------------------------------------------------------------
# def process_year(y, dem, dem_prof):
#     ndvi_path = NDVI_DIR / f"ndvi_{y}_90m_clean.tif"
#     if not ndvi_path.exists():
#         logger.warning(f"NDVI file missing, skipping {y}: {ndvi_path}")
#         return False

#     ndvi, ndvi_prof = read_raster(ndvi_path)

#     # Sanity: check grid match; if not exact, resample to DEM grid
#     same_shape = (ndvi.shape == dem.shape)
#     same_crs   = (ndvi_prof.get("crs") == dem_prof.get("crs"))
#     same_tx    = (ndvi_prof.get("transform") == dem_prof.get("transform"))

#     if not (same_shape and same_crs and same_tx):
#         logger.info(f"Resampling NDVI {y} to DEM grid (should be rare; your *_clean.tif are usually aligned)")
#         dst = np.full(dem.shape, -9999.0, dtype=np.float32)
#         rasterio.warp.reproject(
#             source=ndvi.astype(np.float32),
#             destination=dst,
#             src_transform=ndvi_prof["transform"],
#             src_crs=ndvi_prof["crs"],
#             dst_transform=dem_prof["transform"],
#             dst_crs=dem_prof["crs"],
#             src_nodata=ndvi_prof.get("nodata", None),
#             dst_nodata=-9999.0,
#             resampling=Resampling.bilinear,
#         )
#         ndvi = dst
#         ndvi_prof = dem_prof.copy()

#     # Mask to valid NDVI pixels (we expect AOI-only already)
#     ndvi_nodata = ndvi_prof.get("nodata", None)
#     valid = np.isfinite(ndvi)
#     if ndvi_nodata is not None:
#         valid &= (ndvi != ndvi_nodata)

#     # Compute C
#     c_arr = np.full_like(ndvi, -9999.0, dtype=np.float32)
#     if valid.any():
#         c_arr[valid] = ndvi_to_c(ndvi[valid])

#     # Stats
#     vmask = (c_arr != -9999.0) & np.isfinite(c_arr)
#     if vmask.any():
#         vals = c_arr[vmask]
#         stats = {
#             "year": y,
#             "min": float(vals.min()),
#             "mean": float(vals.mean()),
#             "median": float(np.median(vals)),
#             "max": float(vals.max()),
#             "std": float(vals.std()),
#             "valid_count": int(vals.size),
#             "total_pixels": int(c_arr.size),
#             "coverage_pct": float(vals.size / c_arr.size * 100.0),
#             "alpha": ALPHA,
#             "beta": BETA,
#             "ndvi_min_used": NDVI_MIN,
#             "ndvi_max_used": NDVI_MAX,
#         }
#         logger.info(f"C stats {y}: min={stats['min']:.4f}  mean={stats['mean']:.4f}  "
#                     f"median={stats['median']:.4f}  max={stats['max']:.4f}  std={stats['std']:.4f}  "
#                     f"n={stats['valid_count']} (coverage {stats['coverage_pct']:.2f}%)")
#     else:
#         logger.error(f"No valid C pixels for {y}")
#         return False

#     # Save GeoTIFF
#     out_tif = FACTORS_DIR / f"c_factor_{y}.tif"
#     out_prof = dem_prof.copy()
#     out_prof.update({"dtype": "float32", "nodata": -9999.0})
#     save_geotiff(out_tif, c_arr, out_prof)
#     logger.info(f"Saved C raster: {out_tif}")

#     # Save stats CSV
#     out_csv = STATS_DIR / f"c_factor_stats_{y}.csv"
#     save_stats_csv(out_csv, stats)
#     logger.info(f"Saved C stats CSV: {out_csv}")

#     # Preview PNG
#     try:
#         import matplotlib.pyplot as plt
#         fig_path = FIGURES_DIR / f"c_factor_{y}.png"
#         view = np.where(c_arr <= 0, np.nan, c_arr)
#         vmin = DISPLAY_MIN
#         vmax = DISPLAY_MAX
#         plt.figure(figsize=(9, 7))
#         im = plt.imshow(view, cmap="YlGn", vmin=vmin, vmax=vmax)
#         plt.title(f"C-Factor {y} (NDVI→C; Van der Knijff)")
#         cbar = plt.colorbar(im, shrink=0.8)
#         cbar.set_label("C (0..1)")
#         plt.xlabel("pixels (lon)")
#         plt.ylabel("pixels (lat)")
#         plt.tight_layout()
#         plt.savefig(fig_path, dpi=140)
#         plt.close()
#         logger.info(f"Saved C figure: {fig_path}")
#     except Exception as e:
#         logger.warning(f"Could not create PNG preview for {y}: {e}")

#     return True

# # -----------------------------------------------------------------------------
# def main():
#     logger.info("")
#     logger.info("=" * 80)
#     logger.info("RUSLE C-FACTOR CALCULATION (from Sentinel-2 yearly NDVI @ 90 m)")
#     logger.info("=" * 80)

#     if not DEM_PATH.exists():
#         logger.error(f"DEM not found: {DEM_PATH}")
#         return False

#     dem, dem_prof = read_raster(DEM_PATH)
#     if dem_prof.get("nodata", None) is None:
#         dem_prof["nodata"] = -9999.0

#     ok_any = False
#     for y in YEARS:
#         ok = process_year(y, dem, dem_prof)
#         ok_any = ok_any or ok

#     if not ok_any:
#         logger.error("No C rasters were produced.")
#         return False

#     logger.info("C-factor computation completed.")
#     logger.info("=" * 80)
#     return True

# if __name__ == "__main__":
#     sys.exit(0 if main() else 1)

#!/usr/bin/env python3
"""
RUSLE C-Factor (Cover-Management) from Sentinel-2 NDVI (yearly @ 90 m)
- Uses NDVI -> C conversion: Van der Knijff et al. (2000)
  C = exp( -ALPHA * NDVI / (BETA - NDVI) ), default ALPHA=2.0, BETA=1.0
- Robust to odd NDVI pixels: clamps NDVI to [NDVI_MIN, NDVI_MAX] before conversion.
- Inputs: temp/RUSLE_NDVI90m/ndvi_YYYY_90m_clean.tif (2016..2025)
- Outputs per-year:
    temp/factors/c_factor_YYYY.tif
    outputs/statistics/c_factor_stats_YYYY.csv
    outputs/figures/c_factor_YYYY.png
"""

import sys
import os
from pathlib import Path
import logging
from datetime import datetime
import csv

import numpy as np
import rasterio
from rasterio.enums import Resampling

# -----------------------------------------------------------------------------
# Project paths / defaults (overridden by scripts/config.py if present)
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / "scripts"

DEM_PATH       = BASE_DIR / "temp" / "dem_srtm_90m.tif"
AOI_MASK_PATH  = BASE_DIR / "temp" / "aoi" / "aoi_mask.tif"   # <— added (preferred raster AOI)
NDVI_DIR       = BASE_DIR / "temp" / "RUSLE_NDVI90m"
FACTORS_DIR    = BASE_DIR / "temp" / "factors"
FIGURES_DIR    = BASE_DIR / "outputs" / "figures"
STATS_DIR      = BASE_DIR / "outputs" / "statistics"

YEARS          = list(range(2016, 2026))  # 2016..2025
# NDVI -> C parameters (Van der Knijff 2000)
ALPHA          = 2.0
BETA           = 1.0
# Safe clamp for NDVI before conversion
NDVI_MIN       = 0.0      # set <0 to allow negatives if you prefer
NDVI_MAX       = 0.90     # keep <1.0 to avoid division by zero

DISPLAY_MAX    = 1.0      # PNG upper color bound for C
DISPLAY_MIN    = 0.0
NODATA_F       = -9999.0  # <— consistent nodata

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Optional project config override
try:
    sys.path.insert(0, str(SCRIPTS_DIR))
    import config as _cfg  # type: ignore
    DEM_PATH    = getattr(_cfg, "DEM_PATH", DEM_PATH)
    FACTORS_DIR = getattr(_cfg, "FACTORS_DIR", FACTORS_DIR)
    FIGURES_DIR = getattr(_cfg, "FIGURES_DIR", FIGURES_DIR)
    STATS_DIR   = getattr(_cfg, "STATS_DIR", STATS_DIR)
    ALPHA       = getattr(_cfg, "C_ALPHA", ALPHA)
    BETA        = getattr(_cfg, "C_BETA", BETA)
    NDVI_MIN    = getattr(_cfg, "NDVI_MIN", NDVI_MIN)
    NDVI_MAX    = getattr(_cfg, "NDVI_MAX", NDVI_MAX)
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

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_file = FACTORS_DIR / f"04_c_factor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
handlers = [
    logging.FileHandler(log_file, encoding="utf-8"),
    logging.StreamHandler(sys.stdout),
]
for h in handlers:
    h.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(h)

# -----------------------------------------------------------------------------
# IO helpers
# -----------------------------------------------------------------------------
def read_raster(path):
    with rasterio.open(path) as src:
        arr = src.read(1)
        prof = src.profile
    return arr, prof

def save_geotiff(path, data, profile):
    prof = profile.copy()
    prof.update({
        "driver": "GTiff",
        "count": 1,
        "dtype": "float32",
        "compress": "lzw",
        "nodata": NODATA_F
    })
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(data.astype(np.float32), 1)

def save_stats_csv(path, stats):
    fieldnames = list(stats.keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerow(stats)

# -----------------------------------------------------------------------------
# AOI helper (prefer raster AOI for speed; reproject if needed)
# -----------------------------------------------------------------------------
def load_aoi_mask(match_prof):
    if not AOI_MASK_PATH.exists():
        logger.info("No AOI raster found; proceeding without AOI.")
        return None
    try:
        with rasterio.open(AOI_MASK_PATH) as src:
            m = src.read(1)
            same = (
                (src.crs == match_prof.get("crs")) and
                (src.transform == match_prof.get("transform")) and
                (src.width == match_prof.get("width")) and
                (src.height == match_prof.get("height"))
            )
            if not same:
                dst = np.zeros((match_prof["height"], match_prof["width"]), dtype=np.uint8)
                rasterio.warp.reproject(
                    source=m.astype(np.uint8),
                    destination=dst,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=match_prof["transform"],
                    dst_crs=match_prof["crs"],
                    src_nodata=0,
                    dst_nodata=0,
                    resampling=Resampling.nearest
                )
                m = dst
        m = (m > 0).astype(bool)
        logger.info("AOI mask loaded: aoi_mask.tif (preferred raster)")
        return m
    except Exception as e:
        logger.warning(f"AOI raster present but failed to load/apply ({e}); proceeding without AOI.")
        return None

# -----------------------------------------------------------------------------
# Core: NDVI -> C conversion (vectorized)
# -----------------------------------------------------------------------------
def ndvi_to_c(ndvi):
    # Clamp NDVI for stable math
    x = np.clip(ndvi.astype(np.float32), NDVI_MIN, NDVI_MAX)
    # C = exp( -ALPHA * x / (BETA - x) )
    denom = (BETA - x)
    denom[denom == 0] = 1e-6
    c = np.exp(-ALPHA * x / denom)
    # Ensure [0,1] bounds
    return np.clip(c, 0.0, 1.0)

# -----------------------------------------------------------------------------
# Main per-year processing
# -----------------------------------------------------------------------------
def process_year(y, dem, dem_prof, aoi_mask, aoi_pixels):
    ndvi_path = NDVI_DIR / f"ndvi_{y}_90m_clean.tif"
    if not ndvi_path.exists():
        logger.warning(f"NDVI file missing, skipping {y}: {ndvi_path}")
        return False

    ndvi, ndvi_prof = read_raster(ndvi_path)

    # Sanity: check grid match; if not exact, resample to DEM grid
    same_shape = (ndvi.shape == dem.shape)
    same_crs   = (ndvi_prof.get("crs") == dem_prof.get("crs"))
    same_tx    = (ndvi_prof.get("transform") == dem_prof.get("transform"))

    if not (same_shape and same_crs and same_tx):
        logger.info(f"Resampling NDVI {y} to DEM grid (bilinear)")
        dst = np.full(dem.shape, NODATA_F, dtype=np.float32)
        rasterio.warp.reproject(
            source=ndvi.astype(np.float32),
            destination=dst,
            src_transform=ndvi_prof["transform"],
            src_crs=ndvi_prof["crs"],
            dst_transform=dem_prof["transform"],
            dst_crs=dem_prof["crs"],
            src_nodata=ndvi_prof.get("nodata", None),
            dst_nodata=NODATA_F,
            resampling=Resampling.bilinear,
        )
        ndvi = dst
        ndvi_prof = dem_prof.copy()

    # Respect DEM nodata footprint
    if dem_prof.get("nodata", None) is not None:
        ndvi[dem == dem_prof["nodata"]] = NODATA_F

    # Build validity mask BEFORE mapping (AOI + finite + not nodata)
    pre_mask = np.isfinite(ndvi) & (ndvi != NODATA_F)
    if aoi_mask is not None:
        pre_mask &= aoi_mask

    if not pre_mask.any():
        logger.error(f"No valid NDVI pixels inside AOI for {y}")
        return False

    # Pre-clamp NDVI stats (AOI-only)
    pre_vals = ndvi[pre_mask]
    pre_min = float(np.min(pre_vals))
    pre_max = float(np.max(pre_vals))
    pre_mean = float(np.mean(pre_vals))
    pre_med = float(np.median(pre_vals))

    # Compute C and clamp
    c_arr = np.full_like(ndvi, NODATA_F, dtype=np.float32)
    c_tmp = ndvi_to_c(ndvi)
    c_arr[pre_mask] = c_tmp[pre_mask]

    # Enforce AOI outside: nodata
    if aoi_mask is not None:
        c_arr[~aoi_mask] = NODATA_F

    # Post stats (AOI-only)
    post_mask = (c_arr != NODATA_F) & np.isfinite(c_arr)
    if aoi_mask is not None:
        post_mask &= aoi_mask

    if not post_mask.any():
        logger.error(f"No valid C pixels inside AOI after mapping for {y}")
        return False

    vals = c_arr[post_mask]
    vmin = float(np.min(vals))
    vmax = float(np.max(vals))
    vmean = float(np.mean(vals))
    vmed = float(np.median(vals))
    vstd = float(np.std(vals))
    coverage = float(vals.size / aoi_pixels * 100.0) if aoi_pixels else 0.0

    logger.info(
        f"C stats {y} (AOI-only): "
        f"preNDVI[min={pre_min:.3f}, max={pre_max:.3f}, mean={pre_mean:.3f}, med={pre_med:.3f}]  "
        f"postC[min={vmin:.3f}, max={vmax:.3f}, mean={vmean:.3f}, med={vmed:.3f}, std={vstd:.3f}]  "
        f"n={vals.size}  coverage={coverage:.2f}%"
    )

    # Save GeoTIFF
    out_tif = FACTORS_DIR / f"c_factor_{y}.tif"
    out_prof = dem_prof.copy()
    out_prof.update({"dtype": "float32", "nodata": NODATA_F})
    save_geotiff(out_tif, c_arr, out_prof)
    logger.info(f"Saved C raster: {out_tif}")

    # Save stats CSV (AOI-only, with pre/post + coverage)
    out_csv = STATS_DIR / f"c_factor_stats_{y}.csv"
    save_stats_csv(out_csv, {
        "year": y,
        "pre_ndvi_min": pre_min,
        "pre_ndvi_max": pre_max,
        "pre_ndvi_mean": pre_mean,
        "pre_ndvi_median": pre_med,
        "post_c_min": vmin,
        "post_c_max": vmax,
        "post_c_mean": vmean,
        "post_c_median": vmed,
        "post_c_std": vstd,
        "count_valid": int(vals.size),
        "aoi_pixels": int(aoi_pixels),
        "coverage_pct": coverage,
        "alpha": ALPHA,
        "beta": BETA,
        "ndvi_min_used": NDVI_MIN,
        "ndvi_max_used": NDVI_MAX,
        "note": "NDVI reprojected (bilinear) to DEM grid; AOI mask applied; C clamped to [0,1]; AOI-only stats"
    })
    logger.info(f"Saved C stats CSV: {out_csv}")

    # Preview PNG
    try:
        import matplotlib.pyplot as plt
        fig_path = FIGURES_DIR / f"c_factor_{y}.png"
        view = np.where(c_arr == NODATA_F, np.nan, c_arr)
        plt.figure(figsize=(9, 7))
        im = plt.imshow(view, cmap="YlGn", vmin=DISPLAY_MIN, vmax=DISPLAY_MAX)
        plt.title(f"C-Factor {y} (NDVI→C; Van der Knijff)")
        cbar = plt.colorbar(im, shrink=0.8)
        cbar.set_label("C (0..1)")
        plt.xlabel("pixels (lon)")
        plt.ylabel("pixels (lat)")
        plt.tight_layout()
        plt.savefig(fig_path, dpi=140)
        plt.close()
        logger.info(f"Saved C figure: {fig_path}")
    except Exception as e:
        logger.warning(f"Could not create PNG preview for {y}: {e}")

    return True

# -----------------------------------------------------------------------------
def main():
    logger.info("")
    logger.info("=" * 80)
    logger.info("RUSLE C-FACTOR CALCULATION (from Sentinel-2 yearly NDVI @ 90 m)")
    logger.info("=" * 80)

    if not DEM_PATH.exists():
        logger.error(f"DEM not found: {DEM_PATH}")
        return False

    dem, dem_prof = read_raster(DEM_PATH)
    if dem_prof.get("nodata", None) is None:
        dem_prof["nodata"] = NODATA_F

    # Load AOI raster (preferred) aligned to DEM; compute AOI pixel count
    aoi_mask = load_aoi_mask(dem_prof)
    aoi_pixels = int(aoi_mask.sum()) if aoi_mask is not None else int(dem.size)

    ok_any = False
    for y in YEARS:
        ok = process_year(y, dem, dem_prof, aoi_mask, aoi_pixels)
        ok_any = ok_any or ok

    if not ok_any:
        logger.error("No C rasters were produced.")
        return False

    logger.info("C-factor computation completed.")
    logger.info("=" * 80)
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
