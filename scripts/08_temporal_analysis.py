# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# """
# Temporal analysis for RUSLE soil loss (A-factor), 2016–2025

# Outputs:
#   - outputs/temporal/arrays/
#       a_stack.npy                 (float32, [T,H,W])
#       a_slope.tif / .png          (slope [t/ha/yr per year])
#       a_intercept.tif             (for reference)
#       a_change_2016_2025.tif/.png (absolute change over period)
#       a_change_YYYY_YYYY.tif/.png (year-to-year diffs)
#   - outputs/statistics/temporal/
#       temporal_summary.csv        (per-year AOI stats)
#       trend_summary.csv           (slope stats)
#       change_summary.csv          (2016→2025 stats)
#   - outputs/figures/temporal/
#       mean_timeseries.png
#       slope_map.png
#       change_2016_2025_map.png

# Assumptions:
#   - A rasters exist at: temp/erosion/a_factor_<YEAR>.tif
#   - Reference grid (DEM or any aligned factor) is auto-discovered.
#   - AOI mask optional at temp/aoi/aoi_mask_90m.tif (1 inside AOI). Fallback = finite reference grid.
# """

# import os
# import sys
# import glob
# import logging
# import numpy as np
# import pandas as pd
# import rasterio
# import matplotlib
# matplotlib.use("Agg")
# import matplotlib.pyplot as plt

# # --------------------------
# # Config (matches prior scripts)
# # --------------------------
# YEARS = list(range(2016, 2026))  # 2016..2025 inclusive
# ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# TEMP = os.path.join(ROOT, "temp")
# OUTPUTS = os.path.join(ROOT, "outputs")

# A_DIR = os.path.join(TEMP, "erosion")
# DEM_DIR = os.path.join(TEMP, "dem")
# AOI_DIR = os.path.join(TEMP, "aoi")
# FACTORS_DIR = os.path.join(TEMP, "factors")

# FIG_DIR = os.path.join(OUTPUTS, "figures", "temporal")
# STATS_DIR = os.path.join(OUTPUTS, "statistics", "temporal")
# TMPARR_DIR = os.path.join(OUTPUTS, "temporal", "arrays")
# TMPOUT_DIR = os.path.join(OUTPUTS, "temporal")

# os.makedirs(FIG_DIR, exist_ok=True)
# os.makedirs(STATS_DIR, exist_ok=True)
# os.makedirs(TMPARR_DIR, exist_ok=True)
# os.makedirs(TMPOUT_DIR, exist_ok=True)

# # --------------------------
# # Logging
# # --------------------------
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
# )
# log = logging.getLogger(__name__)

# # --------------------------
# # Helpers
# # --------------------------
# def _first_existing(paths):
#     for p in paths:
#         if p and os.path.exists(p):
#             return p
#     return None

# def _discover_aoi_mask():
#     candidates = [
#         os.path.join(AOI_DIR, "aoi_mask_90m.tif"),
#         os.path.join(AOI_DIR, "aoi_mask.tif"),
#     ]
#     mask_path = _first_existing(candidates)
#     if mask_path:
#         return mask_path
#     globs = glob.glob(os.path.join(AOI_DIR, "*aoi*mask*.tif"))
#     return globs[0] if globs else None

# def _discover_ref_grid():
#     """
#     Find a suitable reference raster providing CRS/transform/shape (not necessarily DEM).
#     Priority:
#       1) temp/dem/ (typical aligned DEM names)
#       2) temp/ root (e.g., dem_srtm_90m.tif in your case)
#       3) temp/factors/ (ls_factor.tif, k_factor.tif, or any .tif)
#       4) temp/erosion/a_factor_2016.tif (guaranteed by pipeline)
#     """
#     # 1) DEM_DIR
#     dem_candidates = [
#         os.path.join(DEM_DIR, "dem_90m_aligned.tif"),
#         os.path.join(DEM_DIR, "dem_aligned_90m.tif"),
#         os.path.join(DEM_DIR, "dem_90m.tif"),
#         os.path.join(DEM_DIR, "dem.tif"),
#     ]
#     p = _first_existing(dem_candidates)
#     if p: return p
#     gl = (
#         glob.glob(os.path.join(DEM_DIR, "*90*m*align*.*tif*")) +
#         glob.glob(os.path.join(DEM_DIR, "*align*90*m*.*tif*")) +
#         glob.glob(os.path.join(DEM_DIR, "dem*.tif")) +
#         glob.glob(os.path.join(DEM_DIR, "*.tif"))
#     )
#     if gl: return gl[0]

#     # 2) TEMP root (your 'dem_srtm_90m.tif' lives here)
#     root_candidates = [
#         os.path.join(TEMP, "dem_srtm_90m.tif"),
#         os.path.join(TEMP, "dem_90m.tif"),
#         os.path.join(TEMP, "dem.tif"),
#     ]
#     p = _first_existing(root_candidates)
#     if p: return p
#     gl = (
#         glob.glob(os.path.join(TEMP, "*dem*90*.tif")) +
#         glob.glob(os.path.join(TEMP, "*dem*.tif")) +
#         glob.glob(os.path.join(TEMP, "*.tif"))
#     )
#     # Prefer files that look like DEMs
#     dem_like = [x for x in gl if "dem" in os.path.basename(x).lower()]
#     if dem_like: return dem_like[0]
#     if gl: return gl[0]

#     # 3) FACTORS_DIR (ls/k or anything aligned)
#     fac_candidates = [
#         os.path.join(FACTORS_DIR, "ls_factor.tif"),
#         os.path.join(FACTORS_DIR, "k_factor.tif"),
#     ]
#     p = _first_existing(fac_candidates)
#     if p: return p
#     gl = glob.glob(os.path.join(FACTORS_DIR, "*.tif"))
#     if gl: return gl[0]

#     # 4) A_DIR: use first yearly A raster as reference
#     a_candidates = [os.path.join(A_DIR, f"a_factor_{y}.tif") for y in YEARS]
#     p = _first_existing(a_candidates)
#     if p: return p

#     return None

# def read_raster(path):
#     with rasterio.open(path) as ds:
#         arr = ds.read(1, masked=False)
#         prof = ds.profile
#         nodata = prof.get("nodata", None)
#     return arr, prof, nodata

# def write_raster(path, arr, ref_profile, nodata_val=None, dtype="float32"):
#     prof = ref_profile.copy()
#     prof.update(
#         dtype=dtype,
#         count=1,
#         compress="deflate",
#         predictor=3 if dtype.startswith("float") else 2,
#         BIGTIFF="IF_SAFER",
#         tiled=True,
#         blockxsize=min(256, ref_profile["width"]),
#         blockysize=min(256, ref_profile["height"]),
#         nodata=nodata_val if nodata_val is not None else ref_profile.get("nodata", None),
#     )
#     with rasterio.open(path, "w", **prof) as ds:
#         ds.write(arr.astype(dtype), 1)

# def save_png(path, img2d, vmin=None, vmax=None, cmap="viridis"):
#     plt.figure(figsize=(9, 6))
#     im = plt.imshow(img2d, vmin=vmin, vmax=vmax, cmap=cmap)
#     plt.colorbar(im, fraction=0.046, pad=0.04)
#     plt.axis("off")
#     plt.tight_layout()
#     plt.savefig(path, dpi=200)
#     plt.close()

# def masked_stats(arr, mask):
#     data = arr[mask]
#     if data.size == 0:
#         return dict(min=np.nan, mean=np.nan, median=np.nan, max=np.nan, std=np.nan, n=0)
#     return dict(
#         min=float(np.nanmin(data)),
#         mean=float(np.nanmean(data)),
#         median=float(np.nanmedian(data)),
#         max=float(np.nanmax(data)),
#         std=float(np.nanstd(data)),
#         n=int(data.size),
#     )

# def ensure_same_grid(ref_prof, prof):
#     keys = ["crs", "transform", "width", "height"]
#     for k in keys:
#         if str(ref_prof[k]) != str(prof[k]):
#             return False
#     return True

# # --------------------------
# # Main
# # --------------------------
# def main():
#     log.info("\n" + "="*78)
#     log.info("FINAL TEMPORAL ANALYSIS: Soil Loss (A) 2016–2025")
#     log.info("="*78)

#     # --- Discover reference grid (DEM or aligned factor)
#     ref_path = _discover_ref_grid()
#     if not ref_path:
#         raise FileNotFoundError(
#             "No suitable reference raster found. "
#             "Expected under temp/dem/, temp/, temp/factors/ or temp/erosion/."
#         )
#     log.info(f"Using reference grid: {ref_path}")
#     ref_arr, ref_prof, ref_nodata = read_raster(ref_path)
#     H, W = ref_arr.shape

#     # --- AOI mask discovery
#     aoi_mask = None
#     aoi_path = _discover_aoi_mask()
#     if aoi_path and os.path.exists(aoi_path):
#         am, am_prof, _ = read_raster(aoi_path)
#         if not ensure_same_grid(ref_prof, am_prof):
#             log.warning("AOI mask grid mismatch; ignoring AOI mask.")
#         else:
#             aoi_mask = (am == 1)
#             log.info(f"Using AOI mask: {aoi_path}")
#     if aoi_mask is None:
#         # fallback: finite reference pixels
#         if ref_nodata is None:
#             log.warning("Reference nodata missing; using finite() as AOI.")
#             aoi_mask = np.isfinite(ref_arr)
#         else:
#             aoi_mask = (ref_arr != ref_nodata)
#         log.info("AOI mask not found; using reference-grid-valid pixels as AOI.")

#     # --- Load A rasters into stack
#     stack = []
#     per_year_stats = []
#     for y in YEARS:
#         a_path = os.path.join(A_DIR, f"a_factor_{y}.tif")
#         if not os.path.exists(a_path):
#             log.error(f"Missing A raster: {a_path}")
#             sys.exit(1)

#         a_arr, a_prof, a_nodata = read_raster(a_path)
#         if not ensure_same_grid(ref_prof, a_prof):
#             log.error(f"Grid mismatch in {a_path}. Stop.")
#             sys.exit(1)

#         valid = np.ones_like(a_arr, dtype=bool)
#         if a_prof.get("nodata") is not None:
#             valid &= (a_arr != a_prof["nodata"])
#         valid &= np.isfinite(a_arr)
#         valid &= aoi_mask

#         a_ma = np.where(valid, a_arr, np.nan).astype("float32")
#         stack.append(a_ma)

#         st = masked_stats(a_ma, ~np.isnan(a_ma))
#         st.update(dict(year=y, coverage_pct=100.0 * st["n"] / (H * W)))
#         log.info(
#             f"A {y}: min={st['min']:.4f}  mean={st['mean']:.4f}  median={st['median']:.4f}  "
#             f"max={st['max']:.4f}  std={st['std']:.4f}  n={st['n']} (coverage {st['coverage_pct']:.2f}%)"
#         )
#         per_year_stats.append(st)

#     stack = np.stack(stack, axis=0)  # [T,H,W]
#     np.save(os.path.join(TMPARR_DIR, "a_stack.npy"), stack)

#     # --- Year-to-year change maps
#     for i in range(len(YEARS) - 1):
#         y0, y1 = YEARS[i], YEARS[i + 1]
#         diff = stack[i + 1] - stack[i]
#         out_tif = os.path.join(TMPOUT_DIR, f"a_change_{y0}_{y1}.tif")
#         out_png = os.path.join(FIG_DIR, f"a_change_{y0}_{y1}.png")
#         write_raster(out_tif, np.where(np.isnan(diff), -9999, diff), ref_prof, nodata_val=-9999)
#         finite = diff[np.isfinite(diff)]
#         vmax = float(np.nanpercentile(np.abs(finite), 98)) if finite.size > 0 else 1.0
#         save_png(out_png, diff, vmin=-vmax, vmax=vmax, cmap="RdBu_r")
#         log.info(f"Saved year-to-year ΔA: {y0}->{y1}")

#     # --- Change 2016 → 2025
#     change_1625 = stack[-1] - stack[0]
#     ch_tif = os.path.join(TMPOUT_DIR, "a_change_2016_2025.tif")
#     ch_png = os.path.join(FIG_DIR, "change_2016_2025_map.png")
#     write_raster(ch_tif, np.where(np.isnan(change_1625), -9999, change_1625), ref_prof, nodata_val=-9999)
#     finite = change_1625[np.isfinite(change_1625)]
#     vmax = float(np.nanpercentile(np.abs(finite), 98)) if finite.size > 0 else 1.0
#     save_png(ch_png, change_1625, vmin=-vmax, vmax=vmax, cmap="RdBu_r")
#     ch_stats = masked_stats(change_1625, ~np.isnan(change_1625))
#     pd.DataFrame([dict(period="2016→2025", **ch_stats)]).to_csv(
#         os.path.join(STATS_DIR, "change_summary.csv"), index=False
#     )
#     log.info("Saved 2016→2025 change products.")

#     # --- Per-pixel linear trend (slope per year)
#     T = stack.shape[0]
#     x = np.arange(T, dtype=np.float32)
#     n = float(T)
#     sx = np.sum(x)
#     sxx = np.sum(x * x)
#     denom = (n * sxx - sx * sx)

#     valid_all = np.all(np.isfinite(stack), axis=0)  # require all years valid
#     slope = np.full((H, W), np.nan, dtype="float32")
#     intercept = np.full((H, W), np.nan, dtype="float32")

#     Y = stack  # [T,H,W]
#     Sy = np.nansum(Y, axis=0)
#     Sxy = np.nansum(Y * x[:, None, None], axis=0)

#     a = (n * Sxy - sx * Sy) / denom  # slope
#     b = (Sy - a * sx) / n            # intercept

#     slope[valid_all] = a[valid_all]
#     intercept[valid_all] = b[valid_all]

#     slope_tif = os.path.join(TMPOUT_DIR, "a_slope.tif")
#     write_raster(slope_tif, np.where(np.isfinite(slope), slope, -9999), ref_prof, nodata_val=-9999)
#     slope_png = os.path.join(FIG_DIR, "slope_map.png")
#     finite = slope[np.isfinite(slope)]
#     vmax = float(np.nanpercentile(np.abs(finite), 98)) if finite.size > 0 else 0.1
#     save_png(slope_png, slope, vmin=-vmax, vmax=vmax, cmap="RdBu_r")

#     int_tif = os.path.join(TMPOUT_DIR, "a_intercept.tif")
#     write_raster(int_tif, np.where(np.isfinite(intercept), intercept, -9999), ref_prof, nodata_val=-9999)

#     tr_stats = masked_stats(slope, np.isfinite(slope))
#     pd.DataFrame([tr_stats]).to_csv(os.path.join(STATS_DIR, "trend_summary.csv"), index=False)
#     log.info("Saved trend (slope/intercept) products.")

#     # --- AOI mean/median time-series plot
#     means = [s["mean"] for s in per_year_stats]
#     medians = [s["median"] for s in per_year_stats]
#     plt.figure(figsize=(9, 4))
#     plt.plot(YEARS, means, marker="o", label="Mean A")
#     plt.plot(YEARS, medians, marker="s", label="Median A")
#     plt.grid(True, alpha=0.3)
#     plt.xlabel("Year")
#     plt.ylabel("A (t/ha/yr)")
#     plt.title("AOI Soil Loss Time Series (2016–2025)")
#     plt.legend()
#     plt.tight_layout()
#     plt.savefig(os.path.join(FIG_DIR, "mean_timeseries.png"), dpi=200)
#     plt.close()

#     # --- Per-year summary CSV
#     df_year = pd.DataFrame(per_year_stats)
#     df_year = df_year[["year", "min", "mean", "median", "max", "std", "n", "coverage_pct"]]
#     df_year.to_csv(os.path.join(STATS_DIR, "temporal_summary.csv"), index=False)

#     log.info("Temporal analysis complete.")
#     log.info("="*78)

# if __name__ == "__main__":
#     main()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Temporal analysis for RUSLE soil loss (A-factor), 2016–2025

Outputs:
  - outputs/temporal/arrays/
      a_stack.npy                 (float32, [T,H,W])
      a_slope.tif / .png          (slope [t/ha/yr per year])
      a_intercept.tif             (for reference)
      a_change_2016_2025.tif/.png (absolute change over period)
      a_change_YYYY_YYYY.tif/.png (year-to-year diffs)
  - outputs/statistics/temporal/
      temporal_summary.csv        (per-year AOI stats)
      trend_summary.csv           (slope stats)
      change_summary.csv          (2016→2025 stats)
  - outputs/figures/temporal/
      mean_timeseries.png
      slope_map.png
      change_2016_2025_map.png
  - NEW:
      a_mean_all_years.tif
      a_mean_all_years.png
      all_years_summary.csv

Assumptions:
  - A rasters exist at: temp/erosion/a_factor_<YEAR>.tif
  - ALL-YEARS mean raster exists at: temp/erosion/a_factor_all_years_mean.tif
"""

import os
import sys
import glob
import logging
import numpy as np
import pandas as pd
import rasterio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --------------------------
# Config (matches prior scripts)
# --------------------------
YEARS = list(range(2016, 2026))  # 2016..2025 inclusive
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMP = os.path.join(ROOT, "temp")
OUTPUTS = os.path.join(ROOT, "outputs")

A_DIR = os.path.join(TEMP, "erosion")
DEM_DIR = os.path.join(TEMP, "dem")
AOI_DIR = os.path.join(TEMP, "aoi")
FACTORS_DIR = os.path.join(TEMP, "factors")

FIG_DIR = os.path.join(OUTPUTS, "figures", "temporal")
STATS_DIR = os.path.join(OUTPUTS, "statistics", "temporal")
TMPARR_DIR = os.path.join(OUTPUTS, "temporal", "arrays")
TMPOUT_DIR = os.path.join(OUTPUTS, "temporal")

os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(STATS_DIR, exist_ok=True)
os.makedirs(TMPARR_DIR, exist_ok=True)
os.makedirs(TMPOUT_DIR, exist_ok=True)

# --------------------------
# Logging
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

# --------------------------
# Helpers
# --------------------------
def _first_existing(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None

def _discover_aoi_mask():
    candidates = [
        os.path.join(AOI_DIR, "aoi_mask_90m.tif"),
        os.path.join(AOI_DIR, "aoi_mask.tif"),
    ]
    mask_path = _first_existing(candidates)
    if mask_path:
        return mask_path
    globs = glob.glob(os.path.join(AOI_DIR, "*aoi*mask*.tif"))
    return globs[0] if globs else None

def _discover_ref_grid():
    # exactly same as before
    dem_candidates = [
        os.path.join(DEM_DIR, "dem_90m_aligned.tif"),
        os.path.join(DEM_DIR, "dem_aligned_90m.tif"),
        os.path.join(DEM_DIR, "dem_90m.tif"),
        os.path.join(DEM_DIR, "dem.tif"),
    ]
    p = _first_existing(dem_candidates)
    if p: return p
    gl = (
        glob.glob(os.path.join(DEM_DIR, "*90*m*align*.*tif*")) +
        glob.glob(os.path.join(DEM_DIR, "*align*90*m*.*tif*")) +
        glob.glob(os.path.join(DEM_DIR, "dem*.tif")) +
        glob.glob(os.path.join(DEM_DIR, "*.tif"))
    )
    if gl: return gl[0]

    root_candidates = [
        os.path.join(TEMP, "dem_srtm_90m.tif"),
        os.path.join(TEMP, "dem_90m.tif"),
        os.path.join(TEMP, "dem.tif"),
    ]
    p = _first_existing(root_candidates)
    if p: return p

    gl = (
        glob.glob(os.path.join(TEMP, "*dem*90*.tif")) +
        glob.glob(os.path.join(TEMP, "*dem*.tif")) +
        glob.glob(os.path.join(TEMP, "*.tif"))
    )
    dem_like = [x for x in gl if "dem" in os.path.basename(x).lower()]
    if dem_like: return dem_like[0]
    if gl: return gl[0]

    fac_candidates = [
        os.path.join(FACTORS_DIR, "ls_factor.tif"),
        os.path.join(FACTORS_DIR, "k_factor.tif"),
    ]
    p = _first_existing(fac_candidates)
    if p: return p

    a_candidates = [os.path.join(A_DIR, f"a_factor_{y}.tif") for y in YEARS]
    return _first_existing(a_candidates)

def read_raster(path):
    with rasterio.open(path) as ds:
        arr = ds.read(1, masked=False)
        prof = ds.profile
        nodata = prof.get("nodata", None)
    return arr, prof, nodata

def write_raster(path, arr, ref_profile, nodata_val=None, dtype="float32"):
    prof = ref_profile.copy()
    prof.update(
        dtype=dtype,
        count=1,
        compress="deflate",
        predictor=3 if dtype.startswith("float") else 2,
        BIGTIFF="IF_SAFER",
        tiled=True,
        blockxsize=min(256, ref_profile["width"]),
        blockysize=min(256, ref_profile["height"]),
        nodata=nodata_val if nodata_val is not None else ref_profile.get("nodata", None),
    )
    with rasterio.open(path, "w", **prof) as ds:
        ds.write(arr.astype(dtype), 1)

def save_png(path, img2d, vmin=None, vmax=None, cmap="viridis"):
    plt.figure(figsize=(9, 6))
    im = plt.imshow(img2d, vmin=vmin, vmax=vmax, cmap=cmap)
    plt.colorbar(im, fraction=0.046, pad=0.04)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()

def masked_stats(arr, mask):
    data = arr[mask]
    if data.size == 0:
        return dict(min=np.nan, mean=np.nan, median=np.nan, max=np.nan, std=np.nan, n=0)
    return dict(
        min=float(np.nanmin(data)),
        mean=float(np.nanmean(data)),
        median=float(np.nanmedian(data)),
        max=float(np.nanmax(data)),
        std=float(np.nanstd(data)),
        n=int(data.size),
    )

def ensure_same_grid(ref_prof, prof):
    keys = ["crs", "transform", "width", "height"]
    return all(str(ref_prof[k]) == str(prof[k]) for k in keys)

# --------------------------
# Main
# --------------------------
def main():
    log.info("\n" + "="*78)
    log.info("FINAL TEMPORAL ANALYSIS: Soil Loss (A) 2016–2025")
    log.info("="*78)

    ref_path = _discover_ref_grid()
    if not ref_path:
        raise FileNotFoundError("No suitable reference raster found.")
    log.info(f"Using reference grid: {ref_path}")

    ref_arr, ref_prof, ref_nodata = read_raster(ref_path)
    H, W = ref_arr.shape

    # AOI mask
    aoi_mask = None
    aoi_path = _discover_aoi_mask()
    if aoi_path:
        am, am_prof, _ = read_raster(aoi_path)
        if ensure_same_grid(ref_prof, am_prof):
            aoi_mask = (am == 1)
            log.info(f"Using AOI mask: {aoi_path}")
    if aoi_mask is None:
        aoi_mask = np.isfinite(ref_arr) if ref_nodata is None else (ref_arr != ref_nodata)
        log.info("AOI mask not found; using reference-grid-valid pixels.")

    # Load yearly rasters
    stack = []
    per_year_stats = []

    for y in YEARS:
        p = os.path.join(A_DIR, f"a_factor_{y}.tif")
        if not os.path.exists(p):
            log.error(f"Missing A raster: {p}")
            sys.exit(1)

        a_arr, a_prof, a_nd = read_raster(p)
        if not ensure_same_grid(ref_prof, a_prof):
            log.error(f"Grid mismatch in {p}.")
            sys.exit(1)

        valid = np.isfinite(a_arr)
        if a_prof.get("nodata") is not None:
            valid &= (a_arr != a_prof["nodata"])
        valid &= aoi_mask

        a_ma = np.where(valid, a_arr, np.nan).astype("float32")
        stack.append(a_ma)

        stats = masked_stats(a_ma, ~np.isnan(a_ma))
        stats.update(dict(year=y, coverage_pct=100 * stats["n"] / (H * W)))
        log.info(
            f"A {y}: min={stats['min']:.4f} mean={stats['mean']:.4f} "
            f"median={stats['median']:.4f} max={stats['max']:.4f} "
            f"n={stats['n']} cov={stats['coverage_pct']:.2f}%"
        )
        per_year_stats.append(stats)

    stack = np.stack(stack, axis=0)
    np.save(os.path.join(TMPARR_DIR, "a_stack.npy"), stack)

    # Year-to-year change
    for i in range(len(YEARS)-1):
        y0, y1 = YEARS[i], YEARS[i+1]
        diff = stack[i+1] - stack[i]
        out_tif = os.path.join(TMPOUT_DIR, f"a_change_{y0}_{y1}.tif")
        out_png = os.path.join(FIG_DIR, f"a_change_{y0}_{y1}.png")

        write_raster(out_tif, np.where(np.isnan(diff), -9999, diff), ref_prof, nodata_val=-9999)
        finite = diff[np.isfinite(diff)]
        vmax = float(np.nanpercentile(np.abs(finite), 98)) if finite.size else 1.0
        save_png(out_png, diff, vmin=-vmax, vmax=vmax, cmap="RdBu_r")

    # 2016→2025 change
    change_1625 = stack[-1] - stack[0]
    write_raster(os.path.join(TMPOUT_DIR, "a_change_2016_2025.tif"),
                 np.where(np.isnan(change_1625), -9999, change_1625),
                 ref_prof, nodata_val=-9999)
    finite = change_1625[np.isfinite(change_1625)]
    vmax = float(np.nanpercentile(np.abs(finite), 98)) if finite.size else 1.0
    save_png(os.path.join(FIG_DIR, "change_2016_2025_map.png"),
             change_1625, vmin=-vmax, vmax=vmax, cmap="RdBu_r")
    pd.DataFrame([masked_stats(change_1625, ~np.isnan(change_1625))]).to_csv(
        os.path.join(STATS_DIR, "change_summary.csv"), index=False)

    # Slope (trend)
    T = stack.shape[0]
    x = np.arange(T, dtype=np.float32)
    n = float(T)
    sx = np.sum(x)
    sxx = np.sum(x * x)
    denom = n * sxx - sx * sx

    valid_all = np.all(np.isfinite(stack), axis=0)
    slope = np.full((H, W), np.nan, dtype=np.float32)
    intercept = np.full((H, W), np.nan, dtype=np.float32)

    Y = stack
    Sy = np.nansum(Y, axis=0)
    Sxy = np.nansum(Y * x[:, None, None], axis=0)

    a = (n*Sxy - sx*Sy) / denom
    b = (Sy - a*sx) / n

    slope[valid_all] = a[valid_all]
    intercept[valid_all] = b[valid_all]

    write_raster(os.path.join(TMPOUT_DIR, "a_slope.tif"),
                 np.where(np.isfinite(slope), slope, -9999),
                 ref_prof, nodata_val=-9999)
    finite = slope[np.isfinite(slope)]
    vmax = float(np.nanpercentile(np.abs(finite), 98)) if finite.size else 0.1
    save_png(os.path.join(FIG_DIR, "slope_map.png"), slope, vmin=-vmax, vmax=vmax, cmap="RdBu_r")

    write_raster(os.path.join(TMPOUT_DIR, "a_intercept.tif"),
                 np.where(np.isfinite(intercept), intercept, -9999),
                 ref_prof, nodata_val=-9999)

    pd.DataFrame([masked_stats(slope, np.isfinite(slope))]).to_csv(
        os.path.join(STATS_DIR, "trend_summary.csv"), index=False)

    # Time-series plot
    means = [s["mean"] for s in per_year_stats]
    medians = [s["median"] for s in per_year_stats]
    plt.figure(figsize=(9, 4))
    plt.plot(YEARS, means, marker="o", label="Mean A")
    plt.plot(YEARS, medians, marker="s", label="Median A")
    plt.grid(True, alpha=0.3)
    plt.xlabel("Year")
    plt.ylabel("A (t/ha/yr)")
    plt.title("AOI Soil Loss Time Series (2016–2025)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "mean_timeseries.png"), dpi=200)
    plt.close()

    pd.DataFrame(per_year_stats)[
        ["year", "min", "mean", "median", "max", "std", "n", "coverage_pct"]
    ].to_csv(os.path.join(STATS_DIR, "temporal_summary.csv"), index=False)

    # ---------------------------------------------------------
    # NEW: ALL-YEARS MEAN TEMPORAL PRODUCT (from 07 script)
    # ---------------------------------------------------------
    all_years_path = os.path.join(A_DIR, "a_factor_all_years_mean.tif")
    if os.path.exists(all_years_path):
        log.info("Loading ALL-YEARS mean raster…")

        arr, prof, nd = read_raster(all_years_path)
        valid = np.isfinite(arr)
        if nd is not None:
            valid &= (arr != nd)
        valid &= aoi_mask

        arr_ma = np.where(valid, arr, np.nan).astype("float32")

        # save cleaned aligned version in temporal folder
        out_tif = os.path.join(TMPOUT_DIR, "a_mean_all_years.tif")
        write_raster(out_tif, np.where(np.isnan(arr_ma), -9999, arr_ma),
                     ref_prof, nodata_val=-9999)

        finite = arr_ma[np.isfinite(arr_ma)]
        vmax = float(np.nanpercentile(finite, 98)) if finite.size else 1.0
        out_png = os.path.join(FIG_DIR, "a_mean_all_years.png")
        save_png(out_png, arr_ma, vmin=0, vmax=vmax, cmap="YlOrRd")

        stats = masked_stats(arr_ma, ~np.isnan(arr_ma))
        pd.DataFrame([stats]).to_csv(
            os.path.join(STATS_DIR, "all_years_summary.csv"), index=False)

        log.info("ALL-YEARS temporal products saved.")
    else:
        log.warning("ALL-YEARS mean raster not found. Skipping.")

    log.info("Temporal analysis complete.")
    log.info("="*78)

if __name__ == "__main__":
    main()
