# #!/usr/bin/env python3
# """
# Prepare P-Factor inputs (Dynamic World derived) for RUSLE
# - Snaps each year’s P raster to the DEM grid (EPSG:4326, 90 m).
# - Enforces strict AOI mask (outside -> nodata).
# - Clamps values to [0, 1] and reports coverage/range.
# - Saves cleaned p_factor_<year>.tif + PNG preview + stats CSVs.

# Expected inputs:
# - DEM grid:                temp/dem_srtm_90m.tif
# - Raw P rasters (from GEE): temp/RUSLE_P_90m/p_factor_<year>_90m.tif
# - AOI shapefile:           catchment/Mula_Mutha_Catchment.shp

# Outputs:
# - Cleaned TIFs:    temp/factors/p_factor_<year>.tif
# - Previews:        outputs/figures/p_factor_<year>.png
# - Per-year stats:  outputs/statistics/p_factor_stats_<year>.csv
# - Master stats:    outputs/statistics/p_prep_stats_<timestamp>.csv
# """

# import sys
# from pathlib import Path
# import logging
# from datetime import datetime
# import csv
# import numpy as np
# import rasterio
# from rasterio.enums import Resampling
# from rasterio import warp
# from rasterio.features import rasterize

# # ----------------------------
# # Project paths / configuration
# # ----------------------------
# BASE_DIR = Path(__file__).resolve().parents[1]
# SCRIPTS_DIR = BASE_DIR / "scripts"

# DEM_PATH     = BASE_DIR / "temp" / "dem_srtm_90m.tif"
# RAW_P_DIR    = BASE_DIR / "temp" / "RUSLE_P_90m"         # <- put your exported P here
# AOI_SHP      = BASE_DIR / "catchment" / "Mula_Mutha_Catchment.shp"

# FACTORS_DIR  = BASE_DIR / "temp" / "factors"
# FIGURES_DIR  = BASE_DIR / "outputs" / "figures"
# STATS_DIR    = BASE_DIR / "outputs" / "statistics"

# LOGS_DIR     = FACTORS_DIR
# LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# # Try to read standard project config (optional)
# try:
#     sys.path.insert(0, str(SCRIPTS_DIR))
#     import config as _cfg  # type: ignore
#     FACTORS_DIR = getattr(_cfg, "FACTORS_DIR", FACTORS_DIR)
#     FIGURES_DIR = getattr(_cfg, "FIGURES_DIR", FIGURES_DIR)
#     TARGET_CRS = getattr(_cfg, "TARGET_CRS", "EPSG:4326")
#     TARGET_RES = getattr(_cfg, "TARGET_RESOLUTION", 90)
#     print("[OK] Configuration loaded successfully!")
#     print("Analysis period: 2016-2025 (10 years)")
#     print(f"Output directory: {BASE_DIR/'outputs'}")
#     print(f"Target CRS: {TARGET_CRS}")
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

# # ----------------------------
# # Logging
# # ----------------------------
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
# log_file = LOGS_DIR / f"06_p_prep_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
# handlers = [
#     logging.FileHandler(log_file, encoding="utf-8"),
#     logging.StreamHandler(sys.stdout),
# ]
# for h in handlers:
#     h.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
#     logger.addHandler(h)

# # ----------------------------
# # Helpers
# # ----------------------------
# def read_raster(path):
#     with rasterio.open(path) as src:
#         arr = src.read(1)
#         prof = src.profile
#     return arr, prof

# def reproject_to_match(source_arr, source_prof, match_prof, continuous=True):
#     """Reproject source into the exact grid of match_prof."""
#     dst = np.full((match_prof["height"], match_prof["width"]), match_prof.get("nodata", -9999), dtype=np.float32)
#     resamp = Resampling.bilinear if continuous else Resampling.nearest
#     warp.reproject(
#         source=source_arr.astype(np.float32),
#         destination=dst,
#         src_transform=source_prof["transform"],
#         src_crs=source_prof["crs"],
#         dst_transform=match_prof["transform"],
#         dst_crs=match_prof["crs"],
#         dst_nodata=match_prof.get("nodata", -9999),
#         resampling=resamp,
#     )
#     return dst

# def load_aoi_mask(match_prof):
#     """Rasterize catchment polygon to the target grid; return boolean mask (True=inside)."""
#     if not AOI_SHP.exists():
#         logger.warning("AOI shapefile not found; skipping AOI hard mask.")
#         return None
#     try:
#         import geopandas as gpd
#         gdf = gpd.read_file(AOI_SHP)
#         if gdf.crs is None or gdf.crs.to_string() != str(match_prof["crs"]):
#             gdf = gdf.to_crs(match_prof["crs"])
#         shapes = [(geom, 1) for geom in gdf.geometry if geom is not None]
#         if not shapes:
#             return None
#         mask = rasterize(
#             shapes=shapes,
#             out_shape=(match_prof["height"], match_prof["width"]),
#             transform=match_prof["transform"],
#             fill=0,
#             dtype="uint8",
#         )
#         return mask.astype(bool)
#     except Exception as e:
#         logger.warning(f"AOI mask not applied: {e}")
#         return None

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

# def save_stats_csv(path, stats_dict):
#     fieldnames = list(stats_dict.keys())
#     with open(path, "w", newline="", encoding="utf-8") as f:
#         writer = csv.DictWriter(f, fieldnames=fieldnames)
#         writer.writeheader()
#         writer.writerow(stats_dict)

# # ----------------------------
# # Main
# # ----------------------------
# def main():
#     logger.info("")
#     logger.info("=" * 80)
#     logger.info("PREPARING P-FACTOR RASTERS (Dynamic-World-derived, expected range [0,1])")
#     logger.info("=" * 80)

#     # 1) DEM (master grid)
#     if not DEM_PATH.exists():
#         logger.error(f"DEM not found: {DEM_PATH}")
#         return False
#     dem, dem_prof = read_raster(DEM_PATH)
#     if dem_prof.get("nodata", None) is None:
#         dem_prof["nodata"] = -9999.0
#     logger.info(f"DEM grid: CRS={dem_prof['crs']}  shape={dem.shape}  nodata={dem_prof.get('nodata')}")

#     # 2) AOI mask on DEM grid
#     aoi_mask = load_aoi_mask(dem_prof)

#     # 3) Iterate years
#     years = list(range(2016, 2026))
#     master_rows = []

#     for y in years:
#         raw_path = RAW_P_DIR / f"p_factor_{y}_90m.tif"
#         if not raw_path.exists():
#             logger.warning(f"Missing P raster for {y}: {raw_path} (skipping this year)")
#             continue

#         # Read raw P
#         p_raw, p_prof = read_raster(raw_path)
#         logger.info(f"Processing {raw_path.name}: CRS={p_prof['crs']} shape={p_raw.shape}")

#         # Reproject to DEM grid (continuous -> bilinear)
#         p_snap = reproject_to_match(p_raw, p_prof, dem_prof, continuous=True)

#         # AOI hard mask
#         if aoi_mask is not None:
#             outside = ~aoi_mask
#             p_snap[outside] = -9999.0
#             logger.info(f"AOI mask applied: {int(outside.sum())} pixels set to nodata outside AOI")

#         # Enforce [0,1]; anything outside set to nodata (strict)
#         valid = np.isfinite(p_snap)
#         too_low = (p_snap < 0) & valid
#         too_high = (p_snap > 1) & valid
#         bad = int(too_low.sum() + too_high.sum())
#         if bad > 0:
#             logger.warning(f"{bad} pixels outside [0,1] -> set to nodata")
#             p_snap[too_low | too_high] = -9999.0

#         # Also honor DEM nodata if present
#         if dem_prof.get("nodata", None) is not None:
#             p_snap[dem == dem_prof["nodata"]] = -9999.0

#         # Stats
#         mask_valid = (p_snap != -9999.0) & np.isfinite(p_snap)
#         if not mask_valid.any():
#             logger.error(f"No valid pixels after processing for {y}.")
#             continue

#         vals = p_snap[mask_valid]
#         stats = {
#             "year": y,
#             "min": float(vals.min()),
#             "mean": float(vals.mean()),
#             "median": float(np.median(vals)),
#             "max": float(vals.max()),
#             "std": float(vals.std()),
#             "valid_count": int(vals.size),
#             "total_pixels": int(p_snap.size),
#             "coverage_pct": float(vals.size / p_snap.size * 100.0),
#             "pct_outside_0_1_set_nodata": float(bad / p_snap.size * 100.0),
#             "note": "Snapped to DEM; AOI hard mask; strict [0,1] clamp"
#         }
#         logger.info(
#             f"P stats {y}: min={stats['min']:.4f}  mean={stats['mean']:.4f}  "
#             f"median={stats['median']:.4f}  max={stats['max']:.4f}  std={stats['std']:.4f}  "
#             f"n={stats['valid_count']} (coverage {stats['coverage_pct']:.2f}%)"
#         )

#         # Save cleaned GeoTIFF
#         out_tif = FACTORS_DIR / f"p_factor_{y}.tif"
#         out_prof = dem_prof.copy()
#         out_prof.update({"dtype": "float32", "nodata": -9999.0})
#         save_geotiff(out_tif, p_snap, out_prof)
#         logger.info(f"Saved P raster: {out_tif}")

#         # Save per-year stats CSV
#         per_csv = STATS_DIR / f"p_factor_stats_{y}.csv"
#         save_stats_csv(per_csv, stats)
#         logger.info(f"Saved P stats CSV: {per_csv}")

#         # Preview PNG
#         try:
#             import matplotlib.pyplot as plt
#             view = np.where(p_snap <= 0, np.nan, p_snap)
#             vmin, vmax = 0.0, 1.0
#             plt.figure(figsize=(10, 7))
#             im = plt.imshow(view, cmap="Blues", vmin=vmin, vmax=vmax)
#             plt.title(f"P-Factor (Support Practice) {y}")
#             cbar = plt.colorbar(im, shrink=0.8)
#             cbar.set_label("P (0–1)")
#             plt.xlabel("pixels (lon)")
#             plt.ylabel("pixels (lat)")
#             plt.tight_layout()
#             fig_path = FIGURES_DIR / f"p_factor_{y}.png"
#             plt.savefig(fig_path, dpi=150)
#             plt.close()
#             logger.info(f"Saved P figure: {fig_path}")
#         except Exception as e:
#             logger.warning(f"Could not create PNG preview ({y}): {e}")

#         master_rows.append(stats)

#     # Master stats CSV
#     if master_rows:
#         ts = datetime.now().strftime("%Y%m%d_%H%M%S")
#         master_csv = STATS_DIR / f"p_prep_stats_{ts}.csv"
#         with open(master_csv, "w", newline="", encoding="utf-8") as f:
#             fieldnames = list(master_rows[0].keys())
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writeheader()
#             writer.writerows(master_rows)
#         logger.info(f"Saved master P prep stats CSV: {master_csv}")
#     else:
#         logger.warning("No years processed; master stats CSV not written.")

#     logger.info("P-factor prep completed.")
#     logger.info("=" * 80)
#     return True

# if __name__ == "__main__":
#     sys.exit(0 if main() else 1)




#!/usr/bin/env python3
"""
Prepare P-Factor inputs (Dynamic World derived) for RUSLE
- Snaps each year’s P raster to the DEM grid (EPSG:4326, 90 m).
- Enforces strict AOI mask (outside -> nodata).
- Clamps values to [0, 1] by marking out-of-range as NODATA (strict in prepare).
- Saves cleaned p_factor_<year>.tif + PNG preview + stats CSVs.
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import csv
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio import warp
from rasterio.features import rasterize

# ----------------------------
# Project paths / configuration
# ----------------------------
BASE_DIR   = Path(__file__).resolve().parents[1]
SCRIPTS_DIR= BASE_DIR / "scripts"

DEM_PATH   = BASE_DIR / "temp" / "dem_srtm_90m.tif"
RAW_P_DIR1 = BASE_DIR / "temp" / "RUSLE_P_90m"   # preferred
RAW_P_DIR2 = BASE_DIR / "temp" / "RUSLE_P90m"    # fallback spelling
AOI_SHP    = BASE_DIR / "catchment" / "Mula_Mutha_Catchment.shp"
AOI_RASTER = BASE_DIR / "temp" / "aoi" / "aoi_mask.tif"  # preferred

FACTORS_DIR= BASE_DIR / "temp" / "factors"
FIGURES_DIR= BASE_DIR / "outputs" / "figures"
STATS_DIR  = BASE_DIR / "outputs" / "statistics"

LOGS_DIR   = FACTORS_DIR
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Optional config overrides
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

# ----------------------------
# Logging
# ----------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_file = LOGS_DIR / f"06_p_prep_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
for h in (logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)):
    h.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(h)

# ----------------------------
# Helpers
# ----------------------------
def read_raster(path):
    with rasterio.open(path) as src:
        return src.read(1), src.profile

def reproject_to_match(source_arr, source_prof, match_prof, continuous=True):
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
    # Prefer prebuilt AOI raster (avoids polygon edge artifacts)
    if AOI_RASTER.exists():
        with rasterio.open(AOI_RASTER) as src:
            am = src.read(1)
            if (src.crs == match_prof["crs"] and
                src.transform == match_prof["transform"] and
                src.width == match_prof["width"] and
                src.height == match_prof["height"]):
                logger.info("AOI mask loaded: aoi_mask.tif (preferred raster)")
                return (am > 0)
            else:
                logger.info("AOI raster exists but grid differs; falling back to shapefile rasterization.")

    if not AOI_SHP.exists():
        logger.warning("AOI shapefile not found; proceeding without AOI hard mask.")
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
        logger.info("AOI mask rasterized from shapefile.")
        return mask.astype(bool)
    except Exception as e:
        logger.warning(f"AOI mask not applied: {e}")
        return None

def save_geotiff(path, data, profile):
    prof = profile.copy()
    prof.update({"driver":"GTiff","count":1,"dtype":"float32","compress":"lzw","nodata":-9999.0})
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(data.astype(np.float32), 1)

# ----------------------------
# Main
# ----------------------------
def main():
    logger.info("")
    logger.info("=" * 80)
    logger.info("PREPARING P-FACTOR RASTERS (strict AOI, strict [0,1] via NODATA)")
    logger.info("=" * 80)

    if not DEM_PATH.exists():
        logger.error(f"DEM not found: {DEM_PATH}")
        return False
    dem, dem_prof = read_raster(DEM_PATH)
    if dem_prof.get("nodata", None) is None:
        dem_prof["nodata"] = -9999.0
    logger.info(f"DEM grid: CRS={dem_prof['crs']}  shape={dem.shape}  nodata={dem_prof['nodata']}")

    aoi_mask = load_aoi_mask(dem_prof)
    if aoi_mask is None:
        aoi_mask = np.ones_like(dem, dtype=bool)
        logger.info("AOI mask not applied (using all pixels).")
    else:
        logger.info(f"AOI pixels: {int(aoi_mask.sum())} / {aoi_mask.size} ({aoi_mask.mean()*100:.2f}%)")

    raw_dir = RAW_P_DIR1 if RAW_P_DIR1.exists() else RAW_P_DIR2
    if not raw_dir.exists():
        logger.error(f"No raw P folder found: {RAW_P_DIR1} or {RAW_P_DIR2}")
        return False

    years = list(range(2016, 2026))
    master_rows = []

    for y in years:
        raw_path = raw_dir / f"p_factor_{y}_90m.tif"
        if not raw_path.exists():
            logger.warning(f"Missing P raster for {y}: {raw_path} (skipping)")
            continue

        p_raw, p_prof = read_raster(raw_path)
        logger.info(f"Processing {raw_path.name}: CRS={p_prof['crs']} shape={p_raw.shape}")

        p_match = reproject_to_match(p_raw, p_prof, dem_prof, continuous=True)

        out = p_match.copy()
        out[~aoi_mask] = -9999.0
        if dem_prof.get("nodata", None) is not None:
            out[dem == dem_prof["nodata"]] = -9999.0

        # Strict: values outside [0,1] -> nodata
        valid = (out != -9999.0) & np.isfinite(out)
        bad = int(((out[valid] < 0.0) | (out[valid] > 1.0)).sum())
        if bad > 0:
            out[(out < 0.0) & valid] = -9999.0
            out[(out > 1.0) & valid] = -9999.0
            logger.warning(f"{y}: {bad} pixels outside [0,1] set to NODATA")

        vmask = (out != -9999.0) & np.isfinite(out)
        if vmask.any():
            vals = out[vmask]
            row = {
                "year": y,
                "min": float(vals.min()),
                "mean": float(vals.mean()),
                "median": float(np.median(vals)),
                "max": float(vals.max()),
                "std": float(vals.std()),
                "valid_count": int(vals.size),
                "total_pixels": int(out.size),
                "coverage_pct": float(vals.size / out.size * 100.0),
                "pct_outside_0_1_set_nodata": float(bad / out.size * 100.0),
                "note": "Snapped to DEM; AOI hard mask; strict [0,1] via NODATA"
            }
            logger.info(f"P {y} stats: min={row['min']:.4f} mean={row['mean']:.4f} "
                        f"median={row['median']:.4f} max={row['max']:.4f} std={row['std']:.4f} "
                        f"n={row['valid_count']} (coverage {row['coverage_pct']:.2f}%)")
            master_rows.append(row)
        else:
            logger.error(f"No valid pixels after processing {y}.")

        out_tif = FACTORS_DIR / f"p_factor_{y}.tif"
        out_prof = dem_prof.copy()
        out_prof.update({"dtype":"float32","nodata":-9999.0})
        save_geotiff(out_tif, out, out_prof)
        logger.info(f"Saved cleaned P raster: {out_tif}")

        # Optional figure
        try:
            import matplotlib.pyplot as plt
            view = np.where(out <= 0, np.nan, out)
            plt.figure(figsize=(10,7))
            im = plt.imshow(view, cmap="PuBuGn", vmin=0, vmax=1)
            plt.title(f"P-Factor (Prepared) {y}")
            cbar = plt.colorbar(im, shrink=0.8)
            cbar.set_label("P (0–1)")
            plt.tight_layout()
            fig_path = FIGURES_DIR / f"p_factor_{y}.png"
            plt.savefig(fig_path, dpi=150)
            plt.close()
            logger.info(f"Saved P figure: {fig_path}")
        except Exception as e:
            logger.warning(f"Could not create PNG preview ({y}): {e}")

    if master_rows:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        master_csv = STATS_DIR / f"p_prep_stats_{ts}.csv"
        with open(master_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(master_rows[0].keys()))
            w.writeheader()
            w.writerows(master_rows)
        logger.info(f"Saved master P prep stats CSV: {master_csv}")

    logger.info("P-factor prep completed.")
    logger.info("=" * 80)
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
