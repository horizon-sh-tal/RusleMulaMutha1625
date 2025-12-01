#!/usr/bin/env python3
"""
RUSLE LS-Factor (Topography) - Static from SRTM DEM @ 90 m
Portable, ASCII-safe, no exotic dependencies.

What it does
------------
1) Reads master DEM (90 m) in EPSG:4326
2) Reprojects to a metric CRS (UTM zone) for correct slope/flow math
3) Light depression handling (1-pass carve) to avoid spurious sinks
4) Computes slope (degrees), D8 flow direction, and flow accumulation
5) Computes LS (Moore & Burch style; m,n exponents adjustable)
6) Reprojects LS back to the DEM grid (EPSG:4326, 90 m)
7) Forces LS >= 0 (negatives, if any, set to 0 and counted)
8) Saves:
   - temp/factors/ls_factor.tif               (final to use downstream)
   - outputs/figures/ls_factor_map.png        (preview only)

Notes
-----
- No hard clipping in the saved LS raster. PNG preview uses a display cap
  to keep the color scale readable.
"""

import sys
import os
from pathlib import Path
import math
import logging
from datetime import datetime

import numpy as np
import rasterio
from rasterio import warp
from rasterio.enums import Resampling
from rasterio.transform import Affine

# -----------------------------------------------------------------------------
# Try to load project config (optional). Fall back to defaults if missing.
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]

FACTORS_DIR = BASE_DIR / "temp" / "factors"
FIGURES_DIR = BASE_DIR / "outputs" / "figures"
STATS_DIR   = BASE_DIR / "outputs" / "statistics"
DEM_PATH    = BASE_DIR / "temp" / "dem_srtm_90m.tif"
AOI_MASK_LL = BASE_DIR / "temp" / "aoi" / "aoi_mask.tif"   # optional, EPSG:4326

TARGET_CRS = "EPSG:4326"   # master grid (matches your DEM)
DISPLAY_LS_CAP = 50.0      # for PNG only, not applied to data
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Optional: pull from scripts/config.py and scripts/color_config.py if present
try:
    sys.path.insert(0, str((BASE_DIR / "scripts").resolve()))
    import config as _cfg  # type: ignore
    FACTORS_DIR = getattr(_cfg, "FACTORS_DIR", FACTORS_DIR)
    FIGURES_DIR = getattr(_cfg, "FIGURES_DIR", FIGURES_DIR)
    TARGET_CRS  = getattr(_cfg, "TARGET_CRS", TARGET_CRS)
    print("[OK] Configuration loaded successfully!")
    print(f"Analysis period: 2016-2025 (10 years)")
    print(f"Output directory: {BASE_DIR/'outputs'}")
    print(f"Target CRS: {TARGET_CRS}")
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

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handlers = [
    logging.FileHandler(FACTORS_DIR / f"02_ls_factor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding="utf-8"),
    logging.StreamHandler(sys.stdout),
]
for h in _handlers:
    h.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(h)

# -----------------------------------------------------------------------------
# Parameters for LS
# -----------------------------------------------------------------------------
M_EXP = 0.4
N_EXP = 1.3
MIN_SLOPE_DEG = 0.1  # to avoid zero-division
NODATA_F = -9999.0   # consistent float nodata for all reprojections

# -----------------------------------------------------------------------------
# Utility: choose UTM zone for a lon value
# -----------------------------------------------------------------------------
def utm_epsg_from_lonlat(lon, lat):
    zone = int((lon + 180.0) // 6) + 1
    if lat >= 0:
        epsg = 32600 + zone
    else:
        epsg = 32700 + zone
    return f"EPSG:{epsg}"

# -----------------------------------------------------------------------------
# Read DEM and pick a suitable metric CRS (UTM)
# -----------------------------------------------------------------------------
def read_dem_and_pick_metric_crs(dem_path):
    with rasterio.open(dem_path) as src:
        dem = src.read(1, masked=True)
        dem_profile = src.profile
        crs = src.crs
        transform = src.transform

        # compute center lon/lat
        h, w = dem.shape
        cx = w // 2
        cy = h // 2
        center_lon, center_lat = transform * (cx, cy)
        if crs and crs.to_string() != "EPSG:4326":
            center_lon, center_lat = warp.transform(
                crs, "EPSG:4326", [center_lon], [center_lat]
            )
            center_lon, center_lat = center_lon[0], center_lat[0]

    metric_epsg = utm_epsg_from_lonlat(center_lon, center_lat)
    return dem, dem_profile, metric_epsg

# -----------------------------------------------------------------------------
# Reproject raster array to target CRS with given resolution (approx 90 m)
# -----------------------------------------------------------------------------
def reproject_raster(data, src_profile, dst_crs, dst_res_m=90.0, resampling=Resampling.bilinear):
    src_transform = src_profile["transform"]
    src_crs = src_profile["crs"]

    # Safe nodata fallback: handle cases where nodata key exists but is None
    nodata = src_profile.get("nodata")
    if nodata is None:
        nodata = NODATA_F
    # bounds in source CRS
    left, bottom, right, top = rasterio.transform.array_bounds(
        data.shape[0], data.shape[1], src_transform
    )
    # bounds -> destination CRS
    left_d, bottom_d, right_d, top_d = warp.transform_bounds(
        src_crs, dst_crs, left, bottom, right, top, densify_pts=21
    )

    dst_transform = Affine.translation(left_d, top_d) * Affine.scale(dst_res_m, -dst_res_m)
    width = max(1, int(math.ceil((right_d - left_d) / dst_res_m)))
    height = max(1, int(math.ceil((top_d - bottom_d) / dst_res_m)))

    dst_profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "crs": dst_crs,
        "transform": dst_transform,
        "nodata": float(nodata),
        "compress": "lzw",
        "tiled": True,
    }

    dst = np.full((height, width), nodata, dtype=np.float32)
    warp.reproject(
        source=data.astype(np.float32),
        destination=dst,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        src_nodata=nodata,
        dst_nodata=nodata,
        resampling=resampling,
        num_threads=0,
    )
    return dst, dst_profile

# -----------------------------------------------------------------------------
# Reproject a mask (0/1) with NEAREST (keeps discrete mask)
# -----------------------------------------------------------------------------
def reproject_mask(mask_data, src_profile, dst_profile):
    out = np.full((dst_profile["height"], dst_profile["width"]), 0, dtype=np.uint8)
    warp.reproject(
        source=mask_data.astype(np.uint8),
        destination=out,
        src_transform=src_profile["transform"],
        src_crs=src_profile["crs"],
        dst_transform=dst_profile["transform"],
        dst_crs=dst_profile["crs"],
        src_nodata=0,
        dst_nodata=0,
        resampling=Resampling.nearest,
    )
    # normalize to 0/1
    return (out > 0).astype(np.uint8)

# -----------------------------------------------------------------------------
# Simple 1-pass carve to reduce tiny pits (keeps speed, avoids heavy deps)
# -----------------------------------------------------------------------------
def light_carve(dem, nodata):
    arr = dem.filled(np.nan).astype(np.float64)
    mask = np.isnan(arr)
    if not mask.any():
        return np.ma.masked_invalid(arr)
    for _ in range(2):
        up = np.roll(arr, 1, axis=0); up[0,:] = np.nan
        dn = np.roll(arr, -1, axis=0); dn[-1,:] = np.nan
        lf = np.roll(arr, 1, axis=1); lf[:,0] = np.nan
        rt = np.roll(arr, -1, axis=1); rt[:,-1] = np.nan
        stack = np.dstack([up, dn, lf, rt])
        nbr = np.nanmean(stack, axis=2)
        arr[mask] = np.where(np.isnan(nbr[mask]), arr[mask], nbr[mask])
        mask = np.isnan(arr)
        if not mask.any():
            break
    return np.ma.masked_invalid(arr)

# -----------------------------------------------------------------------------
# Slope (degrees) from metric grid using 3x3 finite differences
# -----------------------------------------------------------------------------
def slope_degrees(dem, transform):
    sx = abs(transform.a)
    sy = abs(transform.e)
    z = dem.filled(np.nan)

    z00 = np.roll(np.roll(z, 1, axis=0), 1, axis=1)
    z01 = np.roll(z, 1, axis=0)
    z02 = np.roll(np.roll(z, 1, axis=0), -1, axis=1)
    z10 = np.roll(z, 1, axis=1)
    z12 = np.roll(z, -1, axis=1)
    z20 = np.roll(np.roll(z, -1, axis=0), 1, axis=1)
    z21 = np.roll(z, -1, axis=0)
    z22 = np.roll(np.roll(z, -1, axis=0), -1, axis=1)

    dzdx = ((z02 + 2*z12 + z22) - (z00 + 2*z10 + z20)) / (8.0 * sx)
    dzdy = ((z20 + 2*z21 + z22) - (z00 + 2*z01 + z02)) / (8.0 * sy)

    slope_rad = np.arctan(np.sqrt(np.nan_to_num(dzdx)**2 + np.nan_to_num(dzdy)**2))
    slope_deg = np.degrees(slope_rad)
    slope_deg = np.ma.masked_invalid(slope_deg)

    # Edge-safe: mask 1-pixel border to remove roll wrap artifacts
    slope_deg = slope_deg.copy()
    slope_deg[:1, :] = np.ma.masked
    slope_deg[-1:, :] = np.ma.masked
    slope_deg[:, :1] = np.ma.masked
    slope_deg[:, -1:] = np.ma.masked
    return slope_deg

# -----------------------------------------------------------------------------
# D8 flow direction and accumulation (cells)
# -----------------------------------------------------------------------------
_NEIGHBORS = [(-1,-1), (-1,0), (-1,1),
              ( 0,-1),         ( 0,1),
              ( 1,-1), ( 1,0),  ( 1,1)]

def d8_flow_direction(dem):
    """
    Returns dir_idx array with values 0..7 indicating which neighbor is downslope.
    -1 for flats/sinks.
    """
    z = dem.filled(np.nan)
    h, w = z.shape
    dir_idx = -np.ones((h,w), dtype=np.int8)

    for i in range(1, h-1):
        zi = z[i]
        for j in range(1, w-1):
            if np.isnan(zi[j]):
                continue
            max_drop = 0.0
            best_k = -1
            for k, (di, dj) in enumerate(_NEIGHBORS):
                nij = z[i+di, j+dj]
                if np.isnan(nij):
                    continue
                drop = zi[j] - nij
                if drop > max_drop:
                    max_drop = drop
                    best_k = k
            dir_idx[i, j] = best_k
    return dir_idx

def flow_accumulation_cells(dir_idx):
    """
    Counts number of upslope cells draining through each cell (including itself).
    """
    h, w = dir_idx.shape
    indeg = np.zeros((h,w), dtype=np.int32)
    for i in range(1, h-1):
        for j in range(1, w-1):
            k = dir_idx[i, j]
            if k >= 0:
                di, dj = _NEIGHBORS[k]
                indeg[i+di, j+dj] += 1

    from collections import deque
    q = deque()
    acc = np.ones((h,w), dtype=np.float32)  # each cell contributes itself
    for i in range(h):
        for j in range(w):
            if indeg[i, j] == 0:
                q.append((i, j))

    while q:
        i, j = q.popleft()
        k = dir_idx[i, j]
        if k >= 0:
            di, dj = _NEIGHBORS[k]
            ii, jj = i+di, j+dj
            acc[ii, jj] += acc[i, j]
            indeg[ii, jj] -= 1
            if indeg[ii, jj] == 0:
                q.append((ii, jj))
    return acc

# -----------------------------------------------------------------------------
# LS computation (Moore & Burch style)
# -----------------------------------------------------------------------------
def compute_ls(acc_cells, slope_deg, cellsize_m, m_exp=M_EXP, n_exp=N_EXP):
    with np.errstate(invalid='ignore', divide='ignore'):
        A = np.maximum(acc_cells, 1.0) * cellsize_m
        slope_safe_deg = np.maximum(slope_deg.filled(0.0), MIN_SLOPE_DEG)
        slope_rad = np.deg2rad(slope_safe_deg)
        L = (A / 22.13) ** m_exp
        S = (np.sin(slope_rad)) ** n_exp
        LS = L * S
    return np.ma.masked_invalid(LS)

# -----------------------------------------------------------------------------
# Save raster
# -----------------------------------------------------------------------------
def save_geotiff(path, data, profile):
    out_profile = profile.copy()
    out_profile.update({
        "driver": "GTiff",
        "count": 1,
        "dtype": "float32",
        "compress": "lzw",
        "tiled": True,
    })
    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(data.astype(np.float32), 1)

# -----------------------------------------------------------------------------
# Export concise LS stats to CSV
# -----------------------------------------------------------------------------
def export_ls_stats_csv(ls_path, out_dir, logger, nodata=NODATA_F):
    try:
        import pandas as pd
        with rasterio.open(ls_path) as src:
            arr = src.read(1).astype(np.float64)
            nd = src.nodata if src.nodata is not None else nodata
            mask = np.isfinite(arr)
            if nd is not None:
                mask &= (arr != nd)

        vals = arr[mask]
        if vals.size == 0:
            logger.warning("LS stats CSV: no valid pixels found; skipping.")
            return None

        q = np.percentile(vals, [5, 25, 50, 75, 95])
        stats = {
            "count": int(vals.size),
            "min": float(np.min(vals)),
            "p05": float(q[0]),
            "p25": float(q[1]),
            "median": float(q[2]),
            "p75": float(q[3]),
            "p95": float(q[4]),
            "max": float(np.max(vals)),
            "mean": float(np.mean(vals)),
            "std": float(np.std(vals, ddof=1)) if vals.size > 1 else 0.0,
        }

        df = pd.DataFrame([stats])
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = out_dir / f"ls_factor_stats_{stamp}.csv"
        df.to_csv(csv_path, index=False)

        logger.info(f"Saved LS stats CSV: {csv_path}")
        return csv_path
    except Exception as e:
        logger.exception(f"Failed to export LS stats CSV: {e}")
        return None

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    logger.info("")
    logger.info("=" * 80)
    logger.info("RUSLE LS-FACTOR CALCULATION (STATIC: SRTM DEM)")
    logger.info("=" * 80)

    if not DEM_PATH.exists():
        logger.error(f"DEM not found: {DEM_PATH}")
        return False

    # 1) Read DEM and pick metric CRS (UTM)
    with rasterio.open(DEM_PATH) as _src_dbg:
        dbg_nodata = _src_dbg.profile.get("nodata", None)
        dem_ll_transform = _src_dbg.transform
        dem_ll_crs = _src_dbg.crs
        dem_ll_shape = (_src_dbg.height, _src_dbg.width)
    dem_ll, dem_profile_ll, metric_epsg = read_dem_and_pick_metric_crs(DEM_PATH)
    logger.info(f"Master grid (DEM): CRS={dem_profile_ll['crs']}, shape={dem_ll.shape}, nodata={dbg_nodata}")
    logger.info(f"Projected CRS for terrain/hydrology: {metric_epsg}")

    # Optional AOI mask at DEM grid (EPSG:4326). If present, load now.
    aoi_ll = None
    aoi_ll_profile = None
    if AOI_MASK_LL.exists():
        try:
            with rasterio.open(AOI_MASK_LL) as msrc:
                aoi_ll = msrc.read(1)
                aoi_ll_profile = msrc.profile
            # Ensure binary 0/1 in DEM grid
            aoi_ll = (aoi_ll > 0).astype(np.uint8)
            logger.info(f"AOI mask detected: {AOI_MASK_LL.name} (EPSG:4326), will constrain computations.")
        except Exception as e:
            logger.warning(f"Could not read AOI mask, proceeding without it: {e}")

    # 2) Reproject DEM to metric CRS with ~90 m pixels
    dem_m, prof_m = reproject_raster(
        dem_ll.filled(NODATA_F), dem_profile_ll, dst_crs=metric_epsg,
        dst_res_m=90.0, resampling=Resampling.bilinear
    )
    prof_m["nodata"] = prof_m.get("nodata", NODATA_F)
    dem_m = np.ma.masked_equal(dem_m, prof_m["nodata"])
    logger.info(f"Projected DEM: shape={dem_m.shape}, approx cellsize = 90.00 m")

    # If AOI exists, reproject AOI mask to metric grid and apply
    if aoi_ll is not None:
        # Build a temporary profile to represent DEM grid (LL)
        dem_ll_profile_tmp = {
            "transform": dem_ll_transform,
            "crs": dem_ll_crs,
            "height": dem_ll_shape[0],
            "width": dem_ll_shape[1],
            "nodata": 0,
        }
        aoi_m = reproject_mask(aoi_ll, dem_ll_profile_tmp, prof_m)
        if aoi_m.sum() == 0:
            logger.warning("Reprojected AOI mask to metric grid has no valid pixels; ignoring mask.")
        else:
            dem_m = np.ma.array(dem_m, mask=np.logical_or(dem_m.mask, aoi_m == 0))
            logger.info("Applied AOI mask in metric space.")

    # 3) Light depression handling (quick carve)
    logger.info("Filling depressions (Priority-Flood light substitute)...")
    dem_carved = light_carve(dem_m, prof_m["nodata"])

    # 4) Slope (degrees)
    logger.info("Computing slope (degrees)...")
    slope_deg = slope_degrees(dem_carved, prof_m["transform"])

    # 5) D8 flow direction and accumulation (cells)
    logger.info("Computing flow direction (D8)...")
    dir_idx = d8_flow_direction(dem_carved)
    logger.info("Computing flow accumulation (cells)...")
    acc_cells = flow_accumulation_cells(dir_idx)

    # 6) Compute LS in metric grid
    logger.info("Computing LS factor...")
    cellsize_m = abs(prof_m["transform"].a)
    ls_m = compute_ls(acc_cells, slope_deg, cellsize_m)

    # Enforce non-negative LS (hard guarantee)
    neg_count = np.sum(ls_m.filled(0.0) < 0.0)
    if neg_count > 0:
        logger.warning(f"Negative LS values detected: {int(neg_count)}. Forcing to zero.")
    ls_m = np.maximum(ls_m.filled(np.nan), 0.0)
    ls_m = np.ma.masked_invalid(ls_m)

    # 7) Reproject LS back to match DEM grid EXACTLY (single precise step)
    ls_match = np.full(dem_ll.shape, NODATA_F, dtype=np.float32)
    warp.reproject(
        source=ls_m.filled(np.nan).astype(np.float32),
        destination=ls_match,
        src_transform=prof_m["transform"],
        src_crs=prof_m["crs"],
        dst_transform=dem_profile_ll["transform"],
        dst_crs=dem_profile_ll["crs"],
        src_nodata=np.nan,
        dst_nodata=NODATA_F,
        resampling=Resampling.bilinear,
    )
    ls_match = np.ma.masked_equal(ls_match, NODATA_F)

    # If AOI exists, also reapply mask at the DEM grid before saving
    if aoi_ll is not None:
        # Ensure AOI aligns to DEM grid (it already should, but keep it robust)
        aoi_ll_aligned = aoi_ll
        if (aoi_ll.shape != ls_match.shape) or (aoi_ll_profile is not None and aoi_ll_profile.get("transform") != dem_profile_ll["transform"]):
            # Reproject AOI to DEM grid (rare case)
            aoi_ll_aligned = reproject_mask(
                aoi_ll,
                {"transform": dem_ll_transform, "crs": dem_ll_crs, "height": dem_ll_shape[0], "width": dem_ll_shape[1], "nodata": 0},
                dem_profile_ll
            )
        ls_match = np.ma.array(ls_match, mask=np.logical_or(ls_match.mask, aoi_ll_aligned == 0))
        logger.info("Reapplied AOI mask at DEM grid.")

    # Final non-negativity enforcement after reprojection
    neg2 = np.sum(ls_match.filled(0.0) < 0.0)
    if neg2 > 0:
        logger.warning(f"Negative LS values after reprojection: {int(neg2)}. Forcing to zero.")

        # Preserve mask while enforcing non-negativity
    ls_match = np.ma.maximum(ls_match, 0.0)


    # 8) Stats and save
    valid = ~ls_match.mask if isinstance(ls_match, np.ma.MaskedArray) else np.isfinite(ls_match)
    if valid.any():
        v = ls_match[valid]
        logger.info(f"LS stats (final, no hard cap in data): min={v.min():.6f}  mean={v.mean():.3f}  median={np.median(v):.3f}  max={v.max():.3f}  count={v.size}")

    out_tif = FACTORS_DIR / "ls_factor.tif"
    out_prof = dem_profile_ll.copy()
    out_prof.update({"dtype": "float32", "nodata": NODATA_F, "compress": "lzw", "tiled": True})
    save_geotiff(out_tif, ls_match.filled(NODATA_F), out_prof)
    logger.info(f"Saved LS raster: {out_tif}")

    # Optional preview PNG (display cap only for readability)
    try:
        import matplotlib.pyplot as plt
        fig_path = FIGURES_DIR / "ls_factor_map.png"
        arr = ls_match.filled(np.nan)
        view = np.where(np.isfinite(arr), np.clip(arr, 0.0, DISPLAY_LS_CAP), np.nan)
        plt.figure(figsize=(10, 7))
        im = plt.imshow(view, cmap="YlOrRd")
        plt.title("LS Factor (display clipped at {:.0f})".format(DISPLAY_LS_CAP))
        cbar = plt.colorbar(im, shrink=0.8)
        cbar.set_label("LS (display units)")
        plt.xlabel("pixels (lon)")
        plt.ylabel("pixels (lat)")
        plt.tight_layout()
        plt.savefig(fig_path, dpi=150)
        plt.close()
        logger.info(f"Saved LS figure: {fig_path}")
    except Exception as e:
        logger.warning(f"Could not create PNG preview: {e}")

    # Export concise stats CSV
    export_ls_stats_csv(
        ls_path=out_tif,
        out_dir=STATS_DIR,
        logger=logger
    )

    logger.info("LS computation completed.")
    logger.info("=" * 80)
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
