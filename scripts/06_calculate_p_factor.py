# #!/usr/bin/env python3
# """
# RUSLE P-Factor (2016–2025) — standardize, clamp [0,1], align to DEM, export

# Primary expected inputs (preferred):
#   temp/factors/p_factor_<year>.tif                 (from 06_prepare_p_inputs.py)

# Fallback inputs (if the above is missing):
#   temp/RUSLE_P90m/p_factor_<year>_90m.tif          (raw GEE exports)

# Outputs (per year):
#   temp/factors/p_factor_<year>.tif                 (standardized to DEM grid)
#   outputs/figures/p_factor_<year>.png
#   outputs/statistics/p_factor_stats_<year>.csv
# Plus a master CSV:
#   outputs/statistics/p_factor_stats_master_<timestamp>.csv
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
# # Paths / Config
# # ----------------------------
# BASE_DIR    = Path(__file__).resolve().parents[1]
# SCRIPTS_DIR = BASE_DIR / "scripts"

# DEM_PATH    = BASE_DIR / "temp" / "dem_srtm_90m.tif"
# FACT_DIR    = BASE_DIR / "temp" / "factors"
# RAW_P_DIR   = BASE_DIR / "temp" / "RUSLE_P90m"   # fallback
# FIG_DIR     = BASE_DIR / "outputs" / "figures"
# STATS_DIR   = BASE_DIR / "outputs" / "statistics"
# AOI_SHP     = BASE_DIR / "catchment" / "Mula_Mutha_Catchment.shp"

# for d in (FACT_DIR, RAW_P_DIR, FIG_DIR, STATS_DIR):
#     d.mkdir(parents=True, exist_ok=True)

# # Optional project config (colors/paths)
# try:
#     sys.path.insert(0, str(SCRIPTS_DIR))
#     import config as _cfg  # type: ignore
#     FACT_DIR = getattr(_cfg, "FACTORS_DIR", FACT_DIR)
#     FIG_DIR  = getattr(_cfg, "FIGURES_DIR", FIG_DIR)
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

# # ----------------------------
# # Logging
# # ----------------------------
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
# log_file = FACT_DIR / f"06_p_factor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
# handlers = [logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)]
# for h in handlers:
#     h.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#                                      "%Y-%m-%d %H:%M:%S"))
#     logger.addHandler(h)

# # ----------------------------
# # Helpers
# # ----------------------------
# def read1(path):
#     with rasterio.open(path) as src:
#         return src.read(1), src.profile

# def reproject_to_match(arr, src_prof, match_prof, resampling=Resampling.bilinear, nodata=-9999.0):
#     dst = np.full((match_prof["height"], match_prof["width"]), nodata, dtype=np.float32)
#     warp.reproject(
#         source=arr.astype(np.float32),
#         destination=dst,
#         src_transform=src_prof["transform"],
#         src_crs=src_prof["crs"],
#         dst_transform=match_prof["transform"],
#         dst_crs=match_prof["crs"],
#         dst_nodata=nodata,
#         resampling=resampling,
#     )
#     return dst

# def load_aoi_mask(match_prof):
#     """Rasterize AOI polygon to target grid; returns boolean mask (True=inside) or None."""
#     if not AOI_SHP.exists():
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

# def save_tif(path, data, match_prof):
#     prof = match_prof.copy()
#     prof.update({"driver": "GTiff", "count": 1, "dtype": "float32", "compress": "lzw", "nodata": -9999.0})
#     with rasterio.open(path, "w", **prof) as dst:
#         dst.write(data.astype(np.float32), 1)

# def write_stats_csv(path, row):
#     with open(path, "w", newline="", encoding="utf-8") as f:
#         w = csv.DictWriter(f, fieldnames=list(row.keys()))
#         w.writeheader()
#         w.writerow(row)

# def make_stats(year, data, note=""):
#     nodata = -9999.0
#     mask = (data != nodata) & np.isfinite(data)
#     if not mask.any():
#         return {"year": year, "min": None, "mean": None, "median": None, "max": None, "std": None,
#                 "valid_count": 0, "total_pixels": int(data.size), "coverage_pct": 0.0, "note": note}
#     vals = data[mask]
#     return {
#         "year": year,
#         "min": float(vals.min()),
#         "mean": float(vals.mean()),
#         "median": float(np.median(vals)),
#         "max": float(vals.max()),
#         "std": float(vals.std()),
#         "valid_count": int(vals.size),
#         "total_pixels": int(data.size),
#         "coverage_pct": float(vals.size / data.size * 100.0),
#         "note": note
#     }

# # ----------------------------
# # Main
# # ----------------------------
# def main():
#     logger.info("")
#     logger.info("=" * 80)
#     logger.info("RUSLE P-FACTOR CALCULATION (standardize/clamp to [0,1])")
#     logger.info("=" * 80)

#     # DEM as master grid
#     if not DEM_PATH.exists():
#         logger.error(f"DEM not found: {DEM_PATH}")
#         return False
#     dem, dem_prof = read1(DEM_PATH)
#     if dem_prof.get("nodata", None) is None:
#         dem_prof["nodata"] = -9999.0
#     logger.info(f"DEM grid: CRS={dem_prof['crs']}  shape={dem.shape}  nodata={dem_prof['nodata']}")

#     aoi_mask = load_aoi_mask(dem_prof)
#     if aoi_mask is None:
#         logger.info("AOI mask: not available (will only honor DEM nodata).")
#     else:
#         logger.info("AOI mask: available.")

#     years = list(range(2016, 2026))
#     master = []

#     for y in years:
#         preferred = FACT_DIR / f"p_factor_{y}.tif"
#         fallback  = RAW_P_DIR / f"p_factor_{y}_90m.tif"

#         if preferred.exists():
#             src_path = preferred
#         elif fallback.exists():
#             src_path = fallback
#         else:
#             logger.warning(f"Skipping {y}: no P input found ({preferred} or {fallback}).")
#             continue

#         arr_raw, prof_raw = read1(src_path)

#         # Align to DEM grid if needed
#         if (prof_raw["crs"] != dem_prof["crs"]) or \
#            (prof_raw["transform"] != dem_prof["transform"]) or \
#            (prof_raw["width"] != dem_prof["width"]) or \
#            (prof_raw["height"] != dem_prof["height"]):
#             logger.info(f"P {y}: reprojecting to DEM grid…")
#             p = reproject_to_match(arr_raw, prof_raw, dem_prof, Resampling.bilinear)
#         else:
#             p = arr_raw.astype(np.float32)

#         nodata = -9999.0

#         # Apply AOI nodata (strict) if available
#         if aoi_mask is not None:
#             outside = ~aoi_mask
#             p[outside] = nodata
#             logger.info(f"P {y}: AOI mask applied: {int(outside.sum())} pixels -> nodata")

#         # Honor DEM nodata
#         dem_is_nodata = (dem == dem_prof["nodata"])
#         p[dem_is_nodata] = nodata

#         # Clamp valid pixels to [0,1] WITHOUT counting nodata as out-of-range
#         valid = np.isfinite(p) & (p != nodata)
#         over  = (p > 1.0) & valid
#         under = (p < 0.0) & valid
#         if over.any() or under.any():
#             logger.info(f"P {y}: clamped {int(over.sum())} pixels >1 and {int(under.sum())} pixels <0.")
#             p[over] = 1.0
#             p[under] = 0.0

#         # Save standardized P into FACTORS_DIR
#         out_tif = FACT_DIR / f"p_factor_{y}.tif"
#         save_tif(out_tif, p, dem_prof)
#         logger.info(f"Saved P raster: {out_tif}")

#         # Stats
#         row = make_stats(y, p, note="P clamped to [0,1], AOI+DEM nodata applied")
#         logger.info(f"P stats {y}: min={row['min']:.4f}  mean={row['mean']:.4f}  median={row['median']:.4f}  "
#                     f"max={row['max']:.4f}  std={row['std']:.4f}  n={row['valid_count']} "
#                     f"(coverage {row['coverage_pct']:.2f}%)")

#         per_csv = STATS_DIR / f"p_factor_stats_{y}.csv"
#         write_stats_csv(per_csv, row)
#         logger.info(f"Saved P stats CSV: {per_csv}")

#         # Figure
#         try:
#             import matplotlib.pyplot as plt
#             view = np.where((p == nodata) | ~np.isfinite(p), np.nan, p)
#             plt.figure(figsize=(10, 7))
#             im = plt.imshow(view, cmap="PuBuGn", vmin=0, vmax=1)
#             cbar = plt.colorbar(im, shrink=0.8)
#             cbar.set_label("P (support practice factor)")
#             plt.title(f"P-Factor {y}")
#             plt.xlabel("pixels (lon)")
#             plt.ylabel("pixels (lat)")
#             plt.tight_layout()
#             fig_path = FIG_DIR / f"p_factor_{y}.png"
#             plt.savefig(fig_path, dpi=150)
#             plt.close()
#             logger.info(f"Saved P figure: {fig_path}")
#         except Exception as e:
#             logger.warning(f"P {y}: PNG render failed: {e}")

#         master.append(row)

#     # Master CSV
#     if master:
#         ts = datetime.now().strftime("%Y%m%d_%H%M%S")
#         master_csv = STATS_DIR / f"p_factor_stats_master_{ts}.csv"
#         with open(master_csv, "w", newline="", encoding="utf-8") as f:
#             w = csv.DictWriter(f, fieldnames=list(master[0].keys()))
#             w.writeheader()
#             w.writerows(master)
#         logger.info(f"Saved master P stats CSV: {master_csv}")
#     else:
#         logger.warning("No P layers produced (nothing to summarize).")

#     logger.info("P-factor calculation completed.")
#     logger.info("=" * 80)
#     return True

# if __name__ == "__main__":
#     sys.exit(0 if main() else 1)


#!/usr/bin/env python3
"""
RUSLE P-Factor (2016–2025) — standardize, clamp [0,1], align to DEM, export

Preferred inputs (already prepared):
  temp/factors/p_factor_<year>.tif

Fallback inputs:
  temp/RUSLE_P_90m/p_factor_<year>_90m.tif   or   temp/RUSLE_P90m/p_factor_<year>_90m.tif
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

BASE_DIR    = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / "scripts"

DEM_PATH    = BASE_DIR / "temp" / "dem_srtm_90m.tif"
FACT_DIR    = BASE_DIR / "temp" / "factors"
RAW_P_DIR1  = BASE_DIR / "temp" / "RUSLE_P_90m"
RAW_P_DIR2  = BASE_DIR / "temp" / "RUSLE_P90m"
FIG_DIR     = BASE_DIR / "outputs" / "figures"
STATS_DIR   = BASE_DIR / "outputs" / "statistics"
AOI_SHP     = BASE_DIR / "catchment" / "Mula_Mutha_Catchment.shp"
AOI_RASTER  = BASE_DIR / "temp" / "aoi" / "aoi_mask.tif"

for d in (FACT_DIR, RAW_P_DIR1, RAW_P_DIR2, FIG_DIR, STATS_DIR):
    d.mkdir(parents=True, exist_ok=True)

try:
    sys.path.insert(0, str(SCRIPTS_DIR))
    import config as _cfg  # type: ignore
    FACT_DIR = getattr(_cfg, "FACTORS_DIR", FACT_DIR)
    FIG_DIR  = getattr(_cfg, "FIGURES_DIR", FIG_DIR)
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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_file = FACT_DIR / f"06_p_factor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
handlers = [logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)]
for h in handlers:
    h.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                                     "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(h)

def read1(path):
    with rasterio.open(path) as src:
        return src.read(1), src.profile

def reproject_to_match(arr, src_prof, match_prof, resampling=Resampling.bilinear, nodata=-9999.0):
    dst = np.full((match_prof["height"], match_prof["width"]), nodata, dtype=np.float32)
    warp.reproject(
        source=arr.astype(np.float32),
        destination=dst,
        src_transform=src_prof["transform"],
        src_crs=src_prof["crs"],
        dst_transform=match_prof["transform"],
        dst_crs=match_prof["crs"],
        dst_nodata=nodata,
        resampling=resampling,
    )
    return dst

def load_aoi_mask(match_prof):
    if AOI_RASTER.exists():
        with rasterio.open(AOI_RASTER) as src:
            am = src.read(1)
            if (src.crs == match_prof["crs"] and src.transform == match_prof["transform"]
                and src.width == match_prof["width"] and src.height == match_prof["height"]):
                logger.info("AOI mask loaded: aoi_mask.tif (preferred raster)")
                return (am > 0)
            else:
                logger.info("AOI raster grid differs; falling back to shapefile rasterization.")
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
        logger.info("AOI mask rasterized from shapefile.")
        return mask.astype(bool)
    except Exception as e:
        logger.warning(f"AOI mask not applied: {e}")
        return None

def save_tif(path, data, match_prof):
    prof = match_prof.copy()
    prof.update({"driver":"GTiff","count":1,"dtype":"float32","compress":"lzw","nodata":-9999.0})
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(data.astype(np.float32), 1)

def write_stats_csv(path, row):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        w.writeheader()
        w.writerow(row)

def make_stats(year, data, note=""):
    nodata = -9999.0
    mask = (data != nodata) & np.isfinite(data)
    if not mask.any():
        return {"year": year, "min": None, "mean": None, "median": None, "max": None, "std": None,
                "valid_count": 0, "total_pixels": int(data.size), "coverage_pct": 0.0, "note": note}
    vals = data[mask]
    return {
        "year": year,
        "min": float(vals.min()),
        "mean": float(vals.mean()),
        "median": float(np.median(vals)),
        "max": float(vals.max()),
        "std": float(vals.std()),
        "valid_count": int(vals.size),
        "total_pixels": int(data.size),
        "coverage_pct": float(vals.size / data.size * 100.0),
        "note": note
    }

def main():
    logger.info("")
    logger.info("=" * 80)
    logger.info("RUSLE P-FACTOR CALCULATION (standardize/clamp to [0,1])")
    logger.info("=" * 80)

    if not DEM_PATH.exists():
        logger.error(f"DEM not found: {DEM_PATH}")
        return False
    dem, dem_prof = read1(DEM_PATH)
    if dem_prof.get("nodata", None) is None:
        dem_prof["nodata"] = -9999.0
    logger.info(f"DEM grid: CRS={dem_prof['crs']}  shape={dem.shape}  nodata={dem_prof['nodata']}")

    aoi_mask = load_aoi_mask(dem_prof)
    if aoi_mask is None:
        logger.info("AOI mask: not available (will only honor DEM nodata).")
    else:
        logger.info(f"AOI pixels: {int(aoi_mask.sum())} / {aoi_mask.size} ({aoi_mask.mean()*100:.2f}%)")

    years = list(range(2016, 2026))
    master = []

    for y in years:
        preferred = FACT_DIR / f"p_factor_{y}.tif"
        raw1     = RAW_P_DIR1 / f"p_factor_{y}_90m.tif"
        raw2     = RAW_P_DIR2 / f"p_factor_{y}_90m.tif"

        if preferred.exists():
            src_path = preferred
        elif raw1.exists():
            src_path = raw1
        elif raw2.exists():
            src_path = raw2
        else:
            logger.warning(f"Skipping {y}: P input not found ({preferred} / {raw1} / {raw2}).")
            continue

        arr_raw, prof_raw = read1(src_path)

        if (prof_raw["crs"] != dem_prof["crs"]) or \
           (prof_raw["transform"] != dem_prof["transform"]) or \
           (prof_raw["width"] != dem_prof["width"]) or \
           (prof_raw["height"] != dem_prof["height"]):
            logger.info(f"P {y}: reprojecting to DEM grid…")
            p = reproject_to_match(arr_raw, prof_raw, dem_prof, Resampling.bilinear)
        else:
            p = arr_raw.astype(np.float32)

        nodata = -9999.0

        if aoi_mask is not None:
            outside = ~aoi_mask
            p[outside] = nodata
            logger.info(f"P {y}: AOI mask applied: {int(outside.sum())} pixels -> nodata")

        dem_is_nodata = (dem == dem_prof["nodata"])
        p[dem_is_nodata] = nodata

        # Clamp valid pixels to [0,1] (calculate step clamps, not drops)
        valid = np.isfinite(p) & (p != nodata)
        over  = (p > 1.0) & valid
        under = (p < 0.0) & valid
        if over.any() or under.any():
            logger.info(f"P {y}: clamped {int(over.sum())} pixels >1 and {int(under.sum())} pixels <0.")
            p[over] = 1.0
            p[under] = 0.0

        out_tif = FACT_DIR / f"p_factor_{y}.tif"
        save_tif(out_tif, p, dem_prof)
        logger.info(f"Saved P raster: {out_tif}")

        row = make_stats(y, p, note="P clamped to [0,1], AOI+DEM nodata applied")
        logger.info(f"P stats {y}: min={row['min']:.4f}  mean={row['mean']:.4f}  "
                    f"median={row['median']:.4f}  max={row['max']:.4f}  std={row['std']:.4f}  "
                    f"n={row['valid_count']} (coverage {row['coverage_pct']:.2f}%)")

        per_csv = STATS_DIR / f"p_factor_stats_{y}.csv"
        write_stats_csv(per_csv, row)
        logger.info(f"Saved P stats CSV: {per_csv}")

        try:
            import matplotlib.pyplot as plt
            view = np.where((p == nodata) | ~np.isfinite(p), np.nan, p)
            plt.figure(figsize=(10, 7))
            im = plt.imshow(view, cmap="PuBuGn", vmin=0, vmax=1)
            cbar = plt.colorbar(im, shrink=0.8)
            cbar.set_label("P (support practice factor)")
            plt.title(f"P-Factor {y}")
            plt.xlabel("pixels (lon)")
            plt.ylabel("pixels (lat)")
            plt.tight_layout()
            fig_path = FIG_DIR / f"p_factor_{y}.png"
            plt.savefig(fig_path, dpi=150)
            plt.close()
            logger.info(f"Saved P figure: {fig_path}")
        except Exception as e:
            logger.warning(f"P {y}: PNG render failed: {e}")

        master.append(row)

    if master:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        master_csv = STATS_DIR / f"p_factor_stats_master_{ts}.csv"
        with open(master_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(master[0].keys()))
            w.writeheader()
            w.writerows(master)
        logger.info(f"Saved master P stats CSV: {master_csv}")
    else:
        logger.warning("No P layers produced (nothing to summarize).")

    logger.info("P-factor calculation completed.")
    logger.info("=" * 80)
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
