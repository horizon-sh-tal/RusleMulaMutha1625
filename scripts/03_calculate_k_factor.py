#!/usr/bin/env python3
"""
RUSLE K-Factor (Soil Erodibility) from OpenLandMap USDA Texture (static ~2016)
Portable, ASCII-safe, no GEE/geemap required at runtime.

Pipeline
--------
1) Read Soil (USDA classes, 250 m)  -> temp/soil_texture_mula_mutha_250m.tif
2) Read DEM master grid (EPSG:4326, 90 m) -> temp/dem_srtm_90m.tif
3) Reproject soil -> DEM grid (NEAREST)
4) Load AOI (prefer temp/aoi/aoi_mask.tif), align to DEM, mask soil to AOI
5) Reclass USDA class -> K (config.SOIL_K_VALUES if available)
6) Compute AOI-only stats and class coverage
7) Save:
   - temp/factors/k_factor.tif
   - outputs/figures/k_factor_map.png
   - outputs/statistics/k_factor_stats_<timestamp>.csv
   - logs in temp/factors/
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

# ------------------------------------------------------------------------------------
# Project paths / configuration
# ------------------------------------------------------------------------------------
BASE_DIR    = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / "scripts"

DEM_PATH    = BASE_DIR / "temp" / "dem_srtm_90m.tif"
SOIL_PATH   = BASE_DIR / "temp" / "soil_texture_mula_mutha_250m.tif"
AOI_SHP     = BASE_DIR / "catchment" / "Mula_Mutha_Catchment.shp"
AOI_MASK_LL = BASE_DIR / "temp" / "aoi" / "aoi_mask.tif"   # preferred AOI (EPSG:4326 DEM grid)

FACTORS_DIR = BASE_DIR / "temp" / "factors"
FIGURES_DIR = BASE_DIR / "outputs" / "figures"
STATS_DIR   = BASE_DIR / "outputs" / "statistics"
LOGS_DIR    = FACTORS_DIR

DISPLAY_MIN = 0.005  # PNG color scale
DISPLAY_MAX = 0.070
NODATA_F    = -9999.0

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Default K lookup (overridden by scripts/config.py if present)
SOIL_K_VALUES = {
    1: 0.020,  # Clay
    2: 0.025,  # Silty Clay
    3: 0.030,  # Silty Clay Loam
    4: 0.020,  # Sandy Clay
    5: 0.030,  # Sandy Clay Loam
    6: 0.035,  # Clay Loam
    7: 0.045,  # Silt Loam
    8: 0.040,  # Loam
    9: 0.060,  # Silt
    10: 0.030, # Sandy Loam
    11: 0.025, # Loamy Sand
    12: 0.020  # Sand
}
FACTOR_RANGES = {"K": (0.005, 0.070)}

# Try to import project config overrides
try:
    sys.path.insert(0, str(SCRIPTS_DIR))
    import config as _cfg  # type: ignore
    SOIL_K_VALUES = getattr(_cfg, "SOIL_K_VALUES", SOIL_K_VALUES)
    FACTOR_RANGES = getattr(_cfg, "FACTOR_RANGES", FACTOR_RANGES)
    FACTORS_DIR   = getattr(_cfg, "FACTORS_DIR", FACTORS_DIR)
    FIGURES_DIR   = getattr(_cfg, "FIGURES_DIR", FIGURES_DIR)
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

# Ensure dirs exist
FACTORS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
STATS_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_file = LOGS_DIR / f"03_k_factor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
handlers = [
    logging.FileHandler(log_file, encoding="utf-8"),
    logging.StreamHandler(sys.stdout),
]
for h in handlers:
    h.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(h)

# ------------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------------
TEXTURE_NAMES = {
    1: "Clay", 2: "Silty Clay", 3: "Silty Clay Loam", 4: "Sandy Clay",
    5: "Sandy Clay Loam", 6: "Clay Loam", 7: "Silt Loam", 8: "Loam",
    9: "Silt", 10: "Sandy Loam", 11: "Loamy Sand", 12: "Sand"
}

def read_raster(path: Path):
    with rasterio.open(path) as src:
        arr = src.read(1)
        prof = src.profile
        nod = src.nodata
    return arr, prof, nod

def reproject_to_match(src_arr, src_prof, match_prof, categorical=True, src_nodata=None, dst_nodata=NODATA_F):
    """Reproject/Resample source into the exact grid of match_prof."""
    dst = np.full((match_prof["height"], match_prof["width"]), dst_nodata, dtype=np.float32)
    resamp = Resampling.nearest if categorical else Resampling.bilinear
    warp.reproject(
        source=src_arr.astype(np.float32),
        destination=dst,
        src_transform=src_prof["transform"],
        src_crs=src_prof["crs"],
        dst_transform=match_prof["transform"],
        dst_crs=match_prof["crs"],
        src_nodata=src_nodata,
        dst_nodata=dst_nodata,
        resampling=resamp,
    )
    return dst

def rasterize_aoi_from_shp(match_prof):
    """Fallback: Rasterize AOI shapefile onto match grid; returns boolean mask or None."""
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
            all_touched=False,
        )
        return mask.astype(bool)
    except Exception as e:
        logger.warning(f"AOI mask not applied (shapefile fallback failed): {e}")
        return None

def load_aoi_mask(match_prof):
    """
    Preferred: load AOI mask raster from temp/aoi/aoi_mask.tif and reproject (nearest) to match grid.
    Fallback: rasterize shapefile if the raster is missing.
    Returns boolean mask (True inside AOI) or None.
    """
    if AOI_MASK_LL.exists():
        try:
            with rasterio.open(AOI_MASK_LL) as msrc:
                aoi = msrc.read(1)
                aoi_prof = msrc.profile
            # ensure binary 0/1 first
            aoi = (aoi > 0).astype(np.uint8)
            # reproject to match grid if needed
            if (aoi_prof["crs"] != match_prof["crs"]) or \
               (aoi_prof["transform"] != match_prof["transform"]) or \
               (aoi_prof["height"] != match_prof["height"]) or \
               (aoi_prof["width"]  != match_prof["width"]):
                aoi = reproject_to_match(
                    aoi, aoi_prof, match_prof,
                    categorical=True, src_nodata=0, dst_nodata=0
                )
            aoi = (aoi > 0).astype(bool)
            logger.info(f"AOI mask loaded: {AOI_MASK_LL.name} (preferred raster)")
            return aoi
        except Exception as e:
            logger.warning(f"AOI raster load failed ({e}); falling back to shapefile…")
    return rasterize_aoi_from_shp(match_prof)

def reclass_texture_to_k(texture_arr, nodata_value, k_lookup, k_min, k_max, aoi_mask=None):
    """
    Map USDA class codes (1–12) to K float values.
    - Stats and class coverage computed *inside AOI* if aoi_mask is provided.
    """
    out = np.full(texture_arr.shape, nodata_value, dtype=np.float32)

    # Valid where: not nodata, finite, not 0; and inside AOI (if provided)
    valid = np.isfinite(texture_arr)
    valid &= (texture_arr != nodata_value)
    valid &= (texture_arr != 0)
    if aoi_mask is not None:
        valid &= aoi_mask

    # AOI size for coverage denominator
    aoi_pixels = int(aoi_mask.sum()) if aoi_mask is not None else int(valid.size)

    logger.info("Class coverage (AOI-only if AOI provided):")
    logger.info(f"{'Code':<6} {'Texture':<20} {'K':<8} {'Pixels':<12} {'%':<8}")
    logger.info("-" * 60)

    for code, kval in sorted(k_lookup.items()):
        pick = (texture_arr == code) & valid
        cnt = int(pick.sum())
        if cnt > 0:
            out[pick] = float(kval)
        pct = (cnt / aoi_pixels * 100.0) if aoi_pixels > 0 else 0.0
        name = TEXTURE_NAMES.get(code, f"Class{code}")
        logger.info(f"{code:<6} {name:<20} {kval:<8.4f} {cnt:<12d} {pct:>6.2f}")

    # Stats only on AOI-valid K
    mask_vals = (out != nodata_value) & np.isfinite(out)
    if aoi_mask is not None:
        mask_vals &= aoi_mask

    if mask_vals.any():
        vals = out[mask_vals]
        vmin, vmax = float(vals.min()), float(vals.max())
        vmean, vmed, vstd = float(vals.mean()), float(np.median(vals)), float(vals.std())
        logger.info(
            f"K stats (AOI-only): min={vmin:.4f}  mean={vmean:.4f}  median={vmed:.4f}  "
            f"max={vmax:.4f}  std={vstd:.4f}  n={vals.size}  "
            f"(coverage {vals.size / aoi_pixels * 100.0:.2f}% of AOI)"
        )
        if (vmin < k_min) or (vmax > k_max):
            logger.warning(f"Warning: K values outside expected range {k_min}-{k_max}")
        return out, {
            "min": vmin, "mean": vmean, "median": vmed, "max": vmax, "std": vstd,
            "count_valid": int(vals.size), "aoi_pixels": aoi_pixels,
            "coverage_pct": float(vals.size / aoi_pixels * 100.0 if aoi_pixels else 0.0),
            "expected_min": k_min, "expected_max": k_max
        }
    else:
        logger.error("No valid K pixels inside AOI after reclassification.")
        return out, None

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

def save_stats_csv(path, stats_dict):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        for k, v in stats_dict.items():
            w.writerow([k, v])

# ------------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------------
def main():
    logger.info("")
    logger.info("=" * 80)
    logger.info("RUSLE K-FACTOR CALCULATION (STATIC: OpenLandMap USDA Texture ~2016)")
    logger.info("=" * 80)

    # 1) DEM (master grid)
    if not DEM_PATH.exists():
        logger.error(f"DEM not found: {DEM_PATH}")
        return False
    dem, dem_prof, dem_nodata = read_raster(DEM_PATH)
    if dem_prof.get("nodata", None) is None:
        dem_prof["nodata"] = NODATA_F
    logger.info(f"Master DEM grid: CRS={dem_prof['crs']}  shape={dem.shape}  nodata={dem_prof['nodata']}")

    # 2) Soil 250 m (USDA classes)
    if not SOIL_PATH.exists():
        logger.error(f"Soil texture file not found: {SOIL_PATH}")
        return False
    soil_raw, soil_prof, soil_nodata = read_raster(SOIL_PATH)
    # OpenLandMap class rasters commonly use 0 as nodata; fall back if missing
    if soil_nodata is None:
        soil_nodata = 0
    logger.info(f"Soil raster (raw): CRS={soil_prof['crs']}  shape={soil_raw.shape}  nodata={soil_nodata}")

    # 3) Reproject soil -> DEM grid (NEAREST to preserve categories)
    logger.info("Reprojecting soil texture to match DEM grid (nearest-neighbor)…")
    soil_match = reproject_to_match(
        soil_raw, soil_prof, dem_prof,
        categorical=True, src_nodata=soil_nodata, dst_nodata=NODATA_F
    )
    soil_match = np.rint(soil_match).astype(np.int16)  # ensure integer classes

    # 4) AOI: prefer existing raster mask; fallback to shapefile
    aoi_mask = load_aoi_mask(dem_prof)
    if aoi_mask is None:
        logger.warning("AOI not available. Proceeding without AOI mask.")
        aoi_pixels = soil_match.size
    else:
        outside = (~aoi_mask).sum()
        logger.info(f"Applying AOI mask: setting {int(outside)} pixels to nodata outside catchment")
        soil_match[~aoi_mask] = int(NODATA_F)
        aoi_pixels = int(aoi_mask.sum())

    # 5) Reclass USDA -> K (AOI-only stats & coverage)
    k_min, k_max = FACTOR_RANGES.get("K", (0.005, 0.070))
    logger.info("Reclassifying USDA texture classes -> K values…")
    k_raster, stats = reclass_texture_to_k(
        soil_match, nodata_value=NODATA_F,
        k_lookup=SOIL_K_VALUES, k_min=k_min, k_max=k_max,
        aoi_mask=aoi_mask
    )
    if stats is None:
        return False

    # Honor DEM nodata footprint
    if dem_prof.get("nodata", None) is not None:
        k_raster[dem == dem_prof["nodata"]] = NODATA_F

    # 6) Save outputs
    out_tif = FACTORS_DIR / "k_factor.tif"
    out_prof = dem_prof.copy()
    out_prof.update({"dtype": "float32", "nodata": NODATA_F})
    save_geotiff(out_tif, k_raster, out_prof)
    logger.info(f"Saved K raster: {out_tif}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = STATS_DIR / f"k_factor_stats_{ts}.csv"
    save_stats_csv(out_csv, {
        "min": stats["min"],
        "mean": stats["mean"],
        "median": stats["median"],
        "max": stats["max"],
        "std": stats["std"],
        "count_valid": stats["count_valid"],
        "aoi_pixels": stats["aoi_pixels"],
        "coverage_pct": stats["coverage_pct"],
        "expected_min": stats["expected_min"],
        "expected_max": stats["expected_max"],
        "note": "Soil reprojected (nearest) to DEM grid; AOI mask applied; stats AOI-only"
    })
    logger.info(f"Saved K stats CSV: {out_csv}")

    # Preview PNG
    try:
        import matplotlib.pyplot as plt
        from matplotlib.colors import Normalize
        view = np.where(k_raster <= 0, np.nan, k_raster)
        plt.figure(figsize=(12, 8))
        im = plt.imshow(view, cmap="YlOrRd", norm=Normalize(vmin=DISPLAY_MIN, vmax=DISPLAY_MAX))
        plt.title("K-Factor (Soil Erodibility)")
        cbar = plt.colorbar(im, shrink=0.85)
        cbar.set_label("K (t·ha·h / ha·MJ·mm)")
        plt.xlabel("pixels (lon)")
        plt.ylabel("pixels (lat)")
        plt.tight_layout()
        fig_path = FIGURES_DIR / "k_factor_map.png"
        plt.savefig(fig_path, dpi=150)
        plt.close()
        logger.info(f"Saved K figure: {fig_path}")
    except Exception as e:
        logger.warning(f"Could not create PNG preview: {e}")

    logger.info("K-factor computation completed.")
    logger.info("=" * 80)
    return True


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
