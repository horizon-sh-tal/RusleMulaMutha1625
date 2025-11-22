# # # #!/usr/bin/env python3
# # # """
# # # RUSLE Annual Soil Loss (A) = R * K * LS * C * P
# # # - Uses already prepared per-year rasters aligned to the DEM grid @ 90 m.
# # # - Applies AOI mask if available.
# # # - Writes outputs to separate folders (GeoTIFF/PNG/CSV) per your request.
# # # """

# # # import sys
# # # import os
# # # from pathlib import Path
# # # from datetime import datetime
# # # import logging
# # # import csv
# # # import numpy as np
# # # import rasterio
# # # from rasterio.enums import Resampling
# # # from rasterio import warp
# # # from rasterio.features import rasterize

# # # # ----------------------------
# # # # Project paths / configuration
# # # # ----------------------------
# # # BASE_DIR = Path(__file__).resolve().parents[1]
# # # SCRIPTS_DIR = BASE_DIR / "scripts"

# # # FACTORS_DIR = BASE_DIR / "temp" / "factors"
# # # EROSION_DIR = BASE_DIR / "temp" / "erosion"                  # GeoTIFFs (A)
# # # FIG_DIR = BASE_DIR / "outputs" / "figures" / "erosion"       # PNGs
# # # STATS_DIR = BASE_DIR / "outputs" / "statistics" / "erosion"  # CSVs
# # # AOI_SHP = BASE_DIR / "catchment" / "Mula_Mutha_Catchment.shp"

# # # DEM_PATH = BASE_DIR / "temp" / "dem_srtm_90m.tif"

# # # LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# # # LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# # # YEARS = list(range(2016, 2026))  # 2016..2025

# # # # Optional config import (for color ranges or overrides)
# # # DISPLAY_MIN = 0.0
# # # DISPLAY_MAX = None  # autoscale for A quicklook; we’ll robust-clip by percentile
# # # USE_CONFIG = False

# # # try:
# # #     sys.path.insert(0, str(SCRIPTS_DIR))
# # #     import config as _cfg  # type: ignore
# # #     USE_CONFIG = True
# # #     # allow folder overrides if present
# # #     FACTORS_DIR = getattr(_cfg, "FACTORS_DIR", FACTORS_DIR)
# # #     print("[OK] Configuration loaded successfully!")
# # #     print("Analysis period: 2016-2025 (10 years)")
# # #     print(f"Output directory: {BASE_DIR/'outputs'}")
# # #     print(f"Target CRS: {getattr(_cfg, 'TARGET_CRS', 'EPSG:4326')}")
# # #     try:
# # #         import color_config as _cc  # type: ignore
# # #         print("[OK] Standardized color configuration loaded")
# # #     except Exception:
# # #         pass
# # # except Exception:
# # #     print("[INFO] Using internal defaults (no scripts/config.py found)")

# # # # ensure dirs
# # # EROSION_DIR.mkdir(parents=True, exist_ok=True)
# # # FIG_DIR.mkdir(parents=True, exist_ok=True)
# # # STATS_DIR.mkdir(parents=True, exist_ok=True)

# # # # ----------------------------
# # # # Logging
# # # # ----------------------------
# # # logger = logging.getLogger(__name__)
# # # logger.setLevel(logging.INFO)
# # # log_file = EROSION_DIR / f"07_a_factor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
# # # for h in (logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)):
# # #     h.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
# # #     logger.addHandler(h)

# # # # ----------------------------
# # # # Helpers
# # # # ----------------------------
# # # def read_raster(path):
# # #     with rasterio.open(path) as src:
# # #         arr = src.read(1)
# # #         prof = src.profile
# # #     return arr, prof

# # # def reproject_to_match(source_arr, source_prof, match_prof, categorical=False):
# # #     dst = np.full((match_prof["height"], match_prof["width"]),
# # #                   match_prof.get("nodata", -9999), dtype=np.float32)
# # #     resamp = Resampling.nearest if categorical else Resampling.bilinear
# # #     warp.reproject(
# # #         source=source_arr.astype(np.float32),
# # #         destination=dst,
# # #         src_transform=source_prof["transform"],
# # #         src_crs=source_prof["crs"],
# # #         dst_transform=match_prof["transform"],
# # #         dst_crs=match_prof["crs"],
# # #         dst_nodata=match_prof.get("nodata", -9999),
# # #         resampling=resamp,
# # #     )
# # #     return dst

# # # def load_aoi_mask(match_prof):
# # #     if not AOI_SHP.exists():
# # #         return None
# # #     try:
# # #         import geopandas as gpd
# # #         gdf = gpd.read_file(AOI_SHP)
# # #         if gdf.crs is None or gdf.crs.to_string() != str(match_prof["crs"]):
# # #             gdf = gdf.to_crs(match_prof["crs"])
# # #         shapes = [(geom, 1) for geom in gdf.geometry if geom is not None]
# # #         if not shapes:
# # #             return None
# # #         mask = rasterize(
# # #             shapes=shapes,
# # #             out_shape=(match_prof["height"], match_prof["width"]),
# # #             transform=match_prof["transform"],
# # #             fill=0,
# # #             dtype="uint8",
# # #         )
# # #         return mask.astype(bool)
# # #     except Exception as e:
# # #         logger.warning(f"AOI mask not applied: {e}")
# # #         return None

# # # def save_geotiff(path, data, profile):
# # #     prof = profile.copy()
# # #     prof.update({
# # #         "driver": "GTiff",
# # #         "count": 1,
# # #         "dtype": "float32",
# # #         "compress": "lzw",
# # #         "nodata": -9999.0
# # #     })
# # #     with rasterio.open(path, "w", **prof) as dst:
# # #         dst.write(data.astype(np.float32), 1)

# # # def robust_limits(a, vmin_pct=2.0, vmax_pct=98.0):
# # #     vals = a[np.isfinite(a) & (a > 0)]
# # #     if vals.size == 0:
# # #         return 0.0, 1.0
# # #     lo = np.percentile(vals, vmin_pct)
# # #     hi = np.percentile(vals, vmax_pct)
# # #     if hi <= lo:
# # #         hi = float(vals.max())
# # #         lo = float(vals.min())
# # #     return float(lo), float(hi)

# # # def save_quicklook_png(path, data, vmin=None, vmax=None, title="A-factor (t/ha/yr)"):
# # #     try:
# # #         import matplotlib.pyplot as plt
# # #         view = np.where(data <= 0, np.nan, data)
# # #         if vmin is None or vmax is None:
# # #             vmin, vmax = robust_limits(view)
# # #         plt.figure(figsize=(10, 7))
# # #         im = plt.imshow(view, cmap="YlOrRd", vmin=vmin, vmax=vmax)
# # #         cbar = plt.colorbar(im, shrink=0.8)
# # #         cbar.set_label("A (t·ha⁻¹·yr⁻¹)")
# # #         plt.title(title)
# # #         plt.xlabel("pixels (lon)")
# # #         plt.ylabel("pixels (lat)")
# # #         plt.tight_layout()
# # #         plt.savefig(path, dpi=150)
# # #         plt.close()
# # #     except Exception as e:
# # #         logger.warning(f"Could not create PNG: {e}")

# # # def stats_dict(arr):
# # #     m = (arr > 0) & np.isfinite(arr)
# # #     if not m.any():
# # #         return None
# # #     vals = arr[m]
# # #     return {
# # #         "min": float(vals.min()),
# # #         "mean": float(vals.mean()),
# # #         "median": float(np.median(vals)),
# # #         "max": float(vals.max()),
# # #         "std": float(vals.std()),
# # #         "valid_count": int(vals.size),
# # #         "total_pixels": int(arr.size),
# # #         "coverage_pct": float(vals.size / arr.size * 100.0),
# # #     }

# # # def write_csv_row(path, row, header=None):
# # #     new = not Path(path).exists()
# # #     with open(path, "a", newline="", encoding="utf-8") as f:
# # #         w = csv.DictWriter(f, fieldnames=header or list(row.keys()))
# # #         if new:
# # #             w.writeheader()
# # #         w.writerow(row)

# # # # ----------------------------
# # # # Main
# # # # ----------------------------
# # # def main():
# # #     logger.info("")
# # #     logger.info("=" * 80)
# # #     logger.info("RUSLE A-FACTOR (soil loss) CALCULATION")
# # #     logger.info("=" * 80)

# # #     # DEM (master grid)
# # #     dem, dem_prof = read_raster(DEM_PATH)
# # #     if dem_prof.get("nodata", None) is None:
# # #         dem_prof["nodata"] = -9999.0
# # #     logger.info(f"DEM grid: CRS={dem_prof['crs']}  shape={dem.shape}  nodata={dem_prof.get('nodata')}")

# # #     # AOI mask
# # #     aoi_mask = load_aoi_mask(dem_prof)
# # #     if aoi_mask is None:
# # #         logger.info("AOI mask: not available.")
# # #     else:
# # #         logger.info("AOI mask: available.")

# # #     # helper to load and align a factor
# # #     def load_factor(path, categorical=False):
# # #         arr, prof = read_raster(path)
# # #         # quick acceptance if exactly matching
# # #         if (prof["crs"] == dem_prof["crs"] and
# # #             prof["transform"] == dem_prof["transform"] and
# # #             prof["width"] == dem_prof["width"] and
# # #             prof["height"] == dem_prof["height"]):
# # #             aligned = arr.astype(np.float32)
# # #         else:
# # #             aligned = reproject_to_match(arr, prof, dem_prof, categorical=categorical)
# # #         # AOI & DEM nodata
# # #         if aoi_mask is not None:
# # #             aligned[~aoi_mask] = -9999.0
# # #         if dem_prof.get("nodata", None) is not None:
# # #             aligned[dem == dem_prof["nodata"]] = -9999.0
# # #         # sanitize negatives/NaN to nodata
# # #         bad = ~np.isfinite(aligned) | (aligned <= 0)
# # #         aligned[bad] = -9999.0
# # #         return aligned

# # #     master_stats_csv = STATS_DIR / f"a_factor_stats_master_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# # #     for y in YEARS:
# # #         # input file paths (as produced by your previous scripts)
# # #         r_path  = FACTORS_DIR / f"r_factor_{y}.tif"
# # #         k_path  = FACTORS_DIR / "k_factor.tif"        # static
# # #         ls_path = FACTORS_DIR / "ls_factor.tif"       # static
# # #         c_path  = FACTORS_DIR / f"c_factor_{y}.tif"
# # #         p_path  = FACTORS_DIR / f"p_factor_{y}.tif"

# # #         # existence checks
# # #         for p in [r_path, k_path, ls_path, c_path, p_path]:
# # #             if not p.exists():
# # #                 logger.error(f"Missing factor raster: {p}")
# # #                 return False

# # #         logger.info(f"Computing A for {y}…")

# # #         # load & align
# # #         R  = load_factor(r_path,  categorical=False)
# # #         K  = load_factor(k_path,  categorical=False)
# # #         LS = load_factor(ls_path, categorical=False)
# # #         C  = load_factor(c_path,  categorical=False)
# # #         P  = load_factor(p_path,  categorical=False)

# # #         # multiply with strict nodata propagation
# # #         nodata = -9999.0
# # #         A = np.full_like(R, nodata, dtype=np.float32)

# # #         valid = (R > 0) & (K > 0) & (LS > 0) & (C >= 0) & (P >= 0) \
# # #                 & np.isfinite(R) & np.isfinite(K) & np.isfinite(LS) \
# # #                 & np.isfinite(C) & np.isfinite(P)

# # #         A[valid] = R[valid] * K[valid] * LS[valid] * C[valid] * P[valid]

# # #         # remove any inf/nan / negative
# # #         badA = ~np.isfinite(A) | (A <= 0)
# # #         A[badA] = nodata

# # #         # save GeoTIFF
# # #         a_tif = EROSION_DIR / f"a_factor_{y}.tif"
# # #         out_prof = dem_prof.copy()
# # #         out_prof.update({"dtype": "float32", "nodata": nodata})
# # #         save_geotiff(a_tif, A, out_prof)
# # #         logger.info(f"Saved A raster: {a_tif}")

# # #         # stats
# # #         s = stats_dict(A)
# # #         if s is None:
# # #             logger.error(f"No valid A pixels for {y}.")
# # #             continue
# # #         s_row = {"year": y, **s}
# # #         write_csv_row(STATS_DIR / f"a_factor_stats_{y}.csv", s_row)
# # #         write_csv_row(master_stats_csv, s_row, header=list(s_row.keys()))
# # #         logger.info(f"A stats {y}: min={s['min']:.4f}  mean={s['mean']:.4f}  median={s['median']:.4f}  "
# # #                     f"max={s['max']:.4f}  std={s['std']:.4f}  n={s['valid_count']} (coverage {s['coverage_pct']:.2f}%)")

# # #         # quicklook PNG
# # #         fig_path = FIG_DIR / f"a_factor_{y}.png"
# # #         save_quicklook_png(fig_path, A, title=f"A-factor {y} (t/ha/yr)")
# # #         logger.info(f"Saved A figure: {fig_path}")

# # #     logger.info(f"Saved master A stats CSV: {master_stats_csv}")
# # #     logger.info("A-factor calculation completed.")
# # #     logger.info("=" * 80)
# # #     return True

# # # if __name__ == "__main__":
# # #     sys.exit(0 if main() else 1)


# # #!/usr/bin/env python3

















# # """
# # RUSLE Annual Soil Loss (A) = R * K * LS * C * P
# # - Uses already prepared per-year rasters aligned to the DEM grid @ 90 m.
# # - Multiplies STRICTLY inside AOI (if available).
# # - Keeps C/P = 0 as valid (do NOT convert to nodata).
# # - Enforces consistent nodata (-9999.0) across intermediates and outputs.
# # - Outputs:
# #     GeoTIFFs:  temp/erosion/a_factor_<year>.tif
# #     Figures:   outputs/figures/erosion/a_factor_<year>.png
# #     Stats:     outputs/statistics/erosion/a_factor_stats_<year>.csv
# #     Master:    outputs/statistics/erosion/a_factor_stats_master_<ts>.csv
# # """

# # import sys
# # from pathlib import Path
# # from datetime import datetime
# # import logging
# # import csv
# # import numpy as np
# # import rasterio
# # from rasterio.enums import Resampling
# # from rasterio import warp
# # from rasterio.features import rasterize

# # # ----------------------------
# # # Project paths / configuration
# # # ----------------------------
# # BASE_DIR = Path(__file__).resolve().parents[1]
# # SCRIPTS_DIR = BASE_DIR / "scripts"

# # FACTORS_DIR = BASE_DIR / "temp" / "factors"
# # EROSION_DIR = BASE_DIR / "temp" / "erosion"                  # GeoTIFFs (A)
# # FIG_DIR     = BASE_DIR / "outputs" / "figures" / "erosion"   # PNGs
# # STATS_DIR   = BASE_DIR / "outputs" / "statistics" / "erosion"# CSVs
# # AOI_SHP     = BASE_DIR / "catchment" / "Mula_Mutha_Catchment.shp"
# # DEM_PATH    = BASE_DIR / "temp" / "dem_srtm_90m.tif"
# # AOI_DIR    = BASE_DIR / "temp" / "aoi"  # added
# # AOI_MASK_CANDIDATES = [AOI_DIR / "aoi_mask_90m.tif", AOI_DIR / "aoi_mask.tif"]  # added

# # YEARS = list(range(2016, 2026))  # 2016..2025
# # NODATA = -9999.0

# # # Optional config (colors/paths)
# # try:
# #     sys.path.insert(0, str(SCRIPTS_DIR))
# #     import config as _cfg  # type: ignore
# #     FACTORS_DIR = getattr(_cfg, "FACTORS_DIR", FACTORS_DIR)
# #     print("[OK] Configuration loaded successfully!")
# #     print("Analysis period: 2016-2025 (10 years)")
# #     print(f"Output directory: {BASE_DIR/'outputs'}")
# #     print(f"Target CRS: {getattr(_cfg, 'TARGET_CRS', 'EPSG:4326')}")
# #     try:
# #         import color_config as _cc  # type: ignore
# #         print("[OK] Standardized color configuration loaded")
# #     except Exception:
# #         pass
# # except Exception:
# #     print("[INFO] Using internal defaults (no scripts/config.py found)")

# # # ensure dirs
# # EROSION_DIR.mkdir(parents=True, exist_ok=True)
# # FIG_DIR.mkdir(parents=True, exist_ok=True)
# # STATS_DIR.mkdir(parents=True, exist_ok=True)

# # # ----------------------------
# # # Logging
# # # ----------------------------
# # logger = logging.getLogger(__name__)
# # logger.setLevel(logging.INFO)
# # log_file = EROSION_DIR / f"07_a_factor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
# # for h in (logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)):
# #     h.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s",
# #                                      "%Y-%m-%d %H:%M:%S"))
# #     logger.addHandler(h)

# # # ----------------------------
# # # Helpers
# # # ----------------------------
# # def read_raster(path):
# #     with rasterio.open(path) as src:
# #         arr = src.read(1)
# #         prof = src.profile
# #     return arr, prof

# # def reproject_to_match(source_arr, source_prof, match_prof, categorical=False):
# #     dst = np.full((match_prof["height"], match_prof["width"]), NODATA, dtype=np.float32)
# #     resamp = Resampling.nearest if categorical else Resampling.bilinear
# #     warp.reproject(
# #         source=source_arr.astype(np.float32),
# #         destination=dst,
# #         src_transform=source_prof["transform"],
# #         src_crs=source_prof["crs"],
# #         dst_transform=match_prof["transform"],
# #         dst_crs=match_prof["crs"],
# #         dst_nodata=NODATA,
# #         resampling=resamp,
# #     )
# #     return dst

# # def load_aoi_mask(match_prof):
# #     if not AOI_SHP.exists():
# #         return None
# #     try:
# #         import geopandas as gpd
# #         gdf = gpd.read_file(AOI_SHP)
# #         if gdf.crs is None or gdf.crs.to_string() != str(match_prof["crs"]):
# #             gdf = gdf.to_crs(match_prof["crs"])
# #         shapes = [(geom, 1) for geom in gdf.geometry if geom is not None]
# #         if not shapes:
# #             return None
# #         mask = rasterize(
# #             shapes=shapes,
# #             out_shape=(match_prof["height"], match_prof["width"]),
# #             transform=match_prof["transform"],
# #             fill=0,
# #             dtype="uint8",
# #         ).astype(bool)
# #         logger.info(f"AOI mask: {int(mask.sum())} / {mask.size} pixels inside ({100*mask.mean():.2f}%).")
# #         return mask
# #     except Exception as e:
# #         logger.warning(f"AOI mask not applied: {e}")
# #         return None

# # def save_geotiff(path, data, profile):
# #     prof = profile.copy()
# #     prof.update({
# #         "driver": "GTiff",
# #         "count": 1,
# #         "dtype": "float32",
# #         "compress": "lzw",
# #         "nodata": NODATA
# #     })
# #     with rasterio.open(path, "w", **prof) as dst:
# #         dst.write(data.astype(np.float32), 1)

# # def robust_limits(a, vmin_pct=2.0, vmax_pct=98.0):
# #     vals = a[np.isfinite(a) & (a > 0)]
# #     if vals.size == 0:
# #         return 0.0, 1.0
# #     lo = np.percentile(vals, vmin_pct)
# #     hi = np.percentile(vals, vmax_pct)
# #     if hi <= lo:
# #         hi = float(vals.max())
# #         lo = float(vals.min())
# #     return float(lo), float(hi)

# # def save_quicklook_png(path, data, title="A-factor (t/ha/yr)"):
# #     try:
# #         import matplotlib.pyplot as plt
# #         view = np.where((~np.isfinite(data)) | (data == NODATA) | (data <= 0), np.nan, data)
# #         vmin, vmax = robust_limits(view)
# #         plt.figure(figsize=(10, 7))
# #         im = plt.imshow(view, cmap="YlOrRd", vmin=vmin, vmax=vmax)
# #         cbar = plt.colorbar(im, shrink=0.8)
# #         cbar.set_label("A (t·ha⁻¹·yr⁻¹)")
# #         plt.title(title)
# #         plt.xlabel("pixels (lon)")
# #         plt.ylabel("pixels (lat)")
# #         plt.tight_layout()
# #         plt.savefig(path, dpi=150)
# #         plt.close()
# #     except Exception as e:
# #         logger.warning(f"Could not create PNG: {e}")

# # def stats_row(year, arr):
# #     m = np.isfinite(arr) & (arr != NODATA)   # include zeros if they exist
# #     if not m.any():
# #         return {"year": year, "min": None, "mean": None, "median": None, "max": None,
# #                 "std": None, "valid_count": 0, "total_pixels": int(arr.size), "coverage_pct": 0.0}
# #     vals = arr[m]
# #     return {
# #         "year": year,
# #         "min": float(vals.min()),
# #         "mean": float(vals.mean()),
# #         "median": float(np.median(vals)),
# #         "max": float(vals.max()),
# #         "std": float(vals.std()),
# #         "valid_count": int(vals.size),
# #         "total_pixels": int(arr.size),
# #         "coverage_pct": float(vals.size / arr.size * 100.0),
# #     }

# # def write_csv(path, row):
# #     new = not Path(path).exists()
# #     with open(path, "a", newline="", encoding="utf-8") as f:
# #         w = csv.DictWriter(f, fieldnames=list(row.keys()))
# #         if new:
# #             w.writeheader()
# #         w.writerow(row)

# # # factor loader with zero-policy control
# # def load_factor(path, dem_prof, dem, aoi_mask, allow_zero=False):
# #     arr, prof = read_raster(path)
# #     # accept exact matches fast
# #     if (prof["crs"] == dem_prof["crs"] and
# #         prof["transform"] == dem_prof["transform"] and
# #         prof["width"] == dem_prof["width"] and
# #         prof["height"] == dem_prof["height"]):
# #         aligned = arr.astype(np.float32)
# #     else:
# #         aligned = reproject_to_match(arr, prof, dem_prof, categorical=False)

# #     # AOI hard mask first
# #     if aoi_mask is not None:
# #         aligned[~aoi_mask] = NODATA
# #     # respect DEM nodata
# #     if dem_prof.get("nodata", None) is not None:
# #         aligned[dem == dem_prof["nodata"]] = NODATA

# #     # sanitize per zero-policy:
# #     #  - if allow_zero=True (C,P): keep zeros; only <0 or non-finite -> nodata
# #     #  - else (R,K,LS): require >0; <=0 or non-finite -> nodata
# #     if allow_zero:
# #         bad = (~np.isfinite(aligned)) | (aligned < 0)
# #     else:
# #         bad = (~np.isfinite(aligned)) | (aligned <= 0)
# #     aligned[bad] = NODATA
# #     return aligned

# # # ----------------------------
# # # Main
# # # ----------------------------
# # def main():
# #     logger.info("")
# #     logger.info("=" * 80)
# #     logger.info("RUSLE A-FACTOR (soil loss) CALCULATION")
# #     logger.info("=" * 80)

# #     # DEM (master grid)
# #     dem, dem_prof = read_raster(DEM_PATH)
# #     if dem_prof.get("nodata", None) is None:
# #         dem_prof["nodata"] = NODATA
# #     logger.info(f"DEM grid: CRS={dem_prof['crs']}  shape={dem.shape}  nodata={dem_prof.get('nodata')}")

# #     # AOI mask (and a mask of ones if missing so we still run)
# #     aoi_mask = load_aoi_mask(dem_prof)
# #     if aoi_mask is None:
# #         logger.info("AOI mask: not available (multiplying over full grid).")
# #         aoi_mask = np.ones_like(dem, dtype=bool)

# #     master_stats_csv = STATS_DIR / f"a_factor_stats_master_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# #     for y in YEARS:
# #         r_path  = FACTORS_DIR / f"r_factor_{y}.tif"
# #         k_path  = FACTORS_DIR / "k_factor.tif"
# #         ls_path = FACTORS_DIR / "ls_factor.tif"
# #         c_path  = FACTORS_DIR / f"c_factor_{y}.tif"
# #         p_path  = FACTORS_DIR / f"p_factor_{y}.tif"

# #         # existence checks
# #         for pth in (r_path, k_path, ls_path, c_path, p_path):
# #             if not pth.exists():
# #                 logger.error(f"Missing factor raster: {pth}")
# #                 return False

# #         logger.info(f"Computing A for {y}…")

# #         # load with correct zero policy
# #         R  = load_factor(r_path,  dem_prof, dem, aoi_mask, allow_zero=False)
# #         K  = load_factor(k_path,  dem_prof, dem, aoi_mask, allow_zero=False)
# #         LS = load_factor(ls_path, dem_prof, dem, aoi_mask, allow_zero=False)
# #         C  = load_factor(c_path,  dem_prof, dem, aoi_mask, allow_zero=True)   # keep 0 valid
# #         P  = load_factor(p_path,  dem_prof, dem, aoi_mask, allow_zero=True)   # keep 0 valid

# #         # valid where ALL factors are valid AND inside AOI
# #         valid = (R != NODATA) & (K != NODATA) & (LS != NODATA) & \
# #                 (C != NODATA) & (P != NODATA) & aoi_mask

# #         # multiply
# #         A = np.full_like(R, NODATA, dtype=np.float32)
# #         A[valid] = R[valid] * K[valid] * LS[valid] * C[valid] * P[valid]

# #         # clean up infinities / negatives; keep zeros as zeros
# #         badA = (~np.isfinite(A)) | (A < 0)
# #         A[badA] = NODATA

# #         # save GeoTIFF
# #         a_tif = EROSION_DIR / f"a_factor_{y}.tif"
# #         out_prof = dem_prof.copy()
# #         out_prof.update({"dtype": "float32", "nodata": NODATA})
# #         save_geotiff(a_tif, A, out_prof)
# #         logger.info(f"Saved A raster: {a_tif}")

# #         # stats (+ master)
# #         s = stats_row(y, A)
# #         per_csv = STATS_DIR / f"a_factor_stats_{y}.csv"
# #         write_csv(per_csv, s)
# #         write_csv(master_stats_csv, s)
# #         logger.info(f"A stats {y}: min={s['min']}  mean={s['mean']}  median={s['median']}  "
# #                     f"max={s['max']}  std={s['std']}  n={s['valid_count']} (coverage {s['coverage_pct']:.2f}%)")

# #         # quicklook PNG
# #         fig_path = FIG_DIR / f"a_factor_{y}.png"
# #         save_quicklook_png(fig_path, A, title=f"A-factor {y} (t/ha/yr)")
# #         logger.info(f"Saved A figure: {fig_path}")

# #     logger.info(f"Saved master A stats CSV: {master_stats_csv}")
# #     logger.info("A-factor calculation completed.")
# #     logger.info("=" * 80)
# #     return True

# # if __name__ == "__main__":
# #     sys.exit(0 if main() else 1)







# """
# RUSLE Annual Soil Loss (A) = R * K * LS * C * P
# - Uses already prepared per-year rasters aligned to the DEM grid @ 90 m.
# - Multiplies STRICTLY inside AOI (if available).
# - Keeps C/P = 0 as valid (do NOT convert to nodata).
# - Enforces consistent nodata (-9999.0) across intermediates and outputs.
# - Outputs:
#     GeoTIFFs:  temp/erosion/a_factor_<year>.tif
#     Figures:   outputs/figures/erosion/a_factor_<year>.png
#     Stats:     outputs/statistics/erosion/a_factor_stats_<year>.csv
#     Master:    outputs/statistics/erosion/a_factor_stats_master_<ts>.csv
# """

# import sys
# from pathlib import Path
# from datetime import datetime
# import logging
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

# FACTORS_DIR = BASE_DIR / "temp" / "factors"
# EROSION_DIR = BASE_DIR / "temp" / "erosion"                  # GeoTIFFs (A)
# FIG_DIR     = BASE_DIR / "outputs" / "figures" / "erosion"   # PNGs
# STATS_DIR   = BASE_DIR / "outputs" / "statistics" / "erosion"# CSVs
# AOI_SHP     = BASE_DIR / "catchment" / "Mula_Mutha_Catchment.shp"
# DEM_PATH    = BASE_DIR / "temp" / "dem_srtm_90m.tif"

# AOI_DIR    = BASE_DIR / "temp" / "aoi"
# AOI_MASK_CANDIDATES = [
#     AOI_DIR / "aoi_mask_90m.tif",
#     AOI_DIR / "aoi_mask.tif",
# ]

# YEARS = list(range(2016, 2026))  # 2016..2025
# NODATA = -9999.0

# # Optional config (colors/paths)
# try:
#     sys.path.insert(0, str(SCRIPTS_DIR))
#     import config as _cfg  # type: ignore
#     # pull overrides from config if defined
#     FACTORS_DIR = getattr(_cfg, "FACTORS_DIR", FACTORS_DIR)
#     DEM_PATH    = getattr(_cfg, "DEM_PATH", DEM_PATH)
#     YEARS       = getattr(_cfg, "YEARS", YEARS)
#     AOI_MASK_CANDIDATES = getattr(
#         _cfg, "AOI_MASK_RASTER_CANDIDATES", AOI_MASK_CANDIDATES
#     )
#     print("[OK] Configuration loaded successfully!")
#     print(f"Analysis period: {YEARS[0]}-{YEARS[-1]} ({len(YEARS)} years)")
#     print(f"Output directory: {BASE_DIR/'outputs'}")
#     print(f"Target CRS: {getattr(_cfg, 'TARGET_CRS', 'EPSG:4326')}")
#     try:
#         import color_config as _cc  # type: ignore
#         print("[OK] Standardized color configuration loaded")
#     except Exception:
#         pass
# except Exception:
#     print("[INFO] Using internal defaults (no scripts/config.py found)")

# # ensure dirs
# EROSION_DIR.mkdir(parents=True, exist_ok=True)
# FIG_DIR.mkdir(parents=True, exist_ok=True)
# STATS_DIR.mkdir(parents=True, exist_ok=True)

# # ----------------------------
# # Logging
# # ----------------------------
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
# log_file = EROSION_DIR / f"07_a_factor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
# for h in (logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)):
#     h.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#                                      "%Y-%m-%d %H:%M:%S"))
#     logger.addHandler(h)

# # ----------------------------
# # Helpers
# # ----------------------------
# def read_raster(path):
#     with rasterio.open(path) as src:
#         arr = src.read(1)
#         prof = src.profile
#     return arr, prof

# def reproject_to_match(source_arr, source_prof, match_prof, categorical=False):
#     dst = np.full((match_prof["height"], match_prof["width"]), NODATA, dtype=np.float32)
#     resamp = Resampling.nearest if categorical else Resampling.bilinear
#     warp.reproject(
#         source=source_arr.astype(np.float32),
#         destination=dst,
#         src_transform=source_prof["transform"],
#         src_crs=source_prof["crs"],
#         dst_transform=match_prof["transform"],
#         dst_crs=match_prof["crs"],
#         dst_nodata=NODATA,
#         resampling=resamp,
#     )
#     return dst

# def _load_aoi_mask_from_raster(match_prof):
#     """Try to load AOI mask from any AOI_MASK_CANDIDATES path.
#        Reproject (nearest) to match DEM grid if needed. Returns bool mask or None."""
#     for p in AOI_MASK_CANDIDATES:
#         try:
#             if not p.exists():
#                 continue
#             arr, prof = read_raster(p)
#             # if not same grid, reproject with nearest (categorical)
#             if (prof["crs"] != match_prof["crs"] or
#                 prof["transform"] != match_prof["transform"] or
#                 prof["width"] != match_prof["width"] or
#                 prof["height"] != match_prof["height"]):
#                 logger.info(f"AOI raster grid mismatch for {p.name}; reprojecting to DEM grid.")
#                 arr = reproject_to_match(arr, prof, match_prof, categorical=True)
#             mask = (arr > 0).astype(bool)
#             cov = 100.0 * mask.mean()
#             logger.info(f"Using AOI raster: {p} (coverage on DEM grid: {cov:.2f}%)")
#             return mask
#         except Exception as e:
#             logger.warning(f"Failed loading AOI raster {p}: {e}")
#     return None

# def _load_aoi_mask_from_shapefile(match_prof):
#     """Rasterize AOI from catchment shapefile (fallback)."""
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
#         ).astype(bool)
#         logger.info(f"Using AOI from shapefile: {AOI_SHP}")
#         logger.info(f"AOI mask: {int(mask.sum())} / {mask.size} pixels inside ({100*mask.mean():.2f}%).")
#         return mask
#     except Exception as e:
#         logger.warning(f"AOI mask from shapefile failed: {e}")
#         return None

# def load_aoi_mask(match_prof):
#     """Prefer AOI raster; fallback to shapefile; else None."""
#     m = _load_aoi_mask_from_raster(match_prof)
#     if m is not None:
#         return m
#     return _load_aoi_mask_from_shapefile(match_prof)

# def save_geotiff(path, data, profile):
#     prof = profile.copy()
#     prof.update({
#         "driver": "GTiff",
#         "count": 1,
#         "dtype": "float32",
#         "compress": "lzw",
#         "nodata": NODATA
#     })
#     with rasterio.open(path, "w", **prof) as dst:
#         dst.write(data.astype(np.float32), 1)

# def robust_limits(a, vmin_pct=2.0, vmax_pct=98.0):
#     vals = a[np.isfinite(a) & (a > 0)]
#     if vals.size == 0:
#         return 0.0, 1.0
#     lo = np.percentile(vals, vmin_pct)
#     hi = np.percentile(vals, vmax_pct)
#     if hi <= lo:
#         hi = float(vals.max())
#         lo = float(vals.min())
#     return float(lo), float(hi)

# def save_quicklook_png(path, data, title="A-factor (t/ha/yr)"):
#     try:
#         import matplotlib.pyplot as plt
#         view = np.where((~np.isfinite(data)) | (data == NODATA) | (data <= 0), np.nan, data)
#         vmin, vmax = robust_limits(view)
#         plt.figure(figsize=(10, 7))
#         im = plt.imshow(view, cmap="YlOrRd", vmin=vmin, vmax=vmax)
#         cbar = plt.colorbar(im, shrink=0.8)
#         cbar.set_label("A (t·ha⁻¹·yr⁻¹)")
#         plt.title(title)
#         plt.xlabel("pixels (lon)")
#         plt.ylabel("pixels (lat)")
#         plt.tight_layout()
#         plt.savefig(path, dpi=150)
#         plt.close()
#     except Exception as e:
#         logger.warning(f"Could not create PNG: {e}")

# def stats_row(year, arr):
#     m = np.isfinite(arr) & (arr != NODATA)   # include zeros if they exist
#     if not m.any():
#         return {"year": year, "min": None, "mean": None, "median": None, "max": None,
#                 "std": None, "valid_count": 0, "total_pixels": int(arr.size), "coverage_pct": 0.0}
#     vals = arr[m]
#     return {
#         "year": year,
#         "min": float(vals.min()),
#         "mean": float(vals.mean()),
#         "median": float(np.median(vals)),
#         "max": float(vals.max()),
#         "std": float(vals.std()),
#         "valid_count": int(vals.size),
#         "total_pixels": int(arr.size),
#         "coverage_pct": float(vals.size / arr.size * 100.0),
#     }

# def write_csv(path, row):
#     new = not Path(path).exists()
#     with open(path, "a", newline="", encoding="utf-8") as f:
#         w = csv.DictWriter(f, fieldnames=list(row.keys()))
#         if new:
#             w.writeheader()
#         w.writerow(row)

# # factor loader with zero-policy control
# def load_factor(path, dem_prof, dem, aoi_mask, allow_zero=False):
#     arr, prof = read_raster(path)
#     # accept exact matches fast
#     if (prof["crs"] == dem_prof["crs"] and
#         prof["transform"] == dem_prof["transform"] and
#         prof["width"] == dem_prof["width"] and
#         prof["height"] == dem_prof["height"]):
#         aligned = arr.astype(np.float32)
#     else:
#         aligned = reproject_to_match(arr, prof, dem_prof, categorical=False)

#     # AOI hard mask first
#     if aoi_mask is not None:
#         aligned[~aoi_mask] = NODATA
#     # respect DEM nodata
#     if dem_prof.get("nodata", None) is not None:
#         aligned[dem == dem_prof["nodata"]] = NODATA

#     # sanitize per zero-policy:
#     #  - if allow_zero=True (C,P): keep zeros; only <0 or non-finite -> nodata
#     #  - else (R,K,LS): require >0; <=0 or non-finite -> nodata
#     if allow_zero:
#         bad = (~np.isfinite(aligned)) | (aligned < 0)
#     else:
#         bad = (~np.isfinite(aligned)) | (aligned <= 0)
#     aligned[bad] = NODATA
#     return aligned

# # ----------------------------
# # Main
# # ----------------------------
# def main():
#     logger.info("")
#     logger.info("=" * 80)
#     logger.info("RUSLE A-FACTOR (soil loss) CALCULATION")
#     logger.info("=" * 80)

#     # DEM (master grid)
#     dem, dem_prof = read_raster(DEM_PATH)
#     if dem_prof.get("nodata", None) is None:
#         dem_prof["nodata"] = NODATA
#     logger.info(f"DEM grid: CRS={dem_prof['crs']}  shape={dem.shape}  nodata={dem_prof.get('nodata')}")

#     # AOI mask (prefer AOI raster; fallback to shapefile; else full grid)
#     aoi_mask = load_aoi_mask(dem_prof)
#     if aoi_mask is None:
#         logger.info("AOI mask: not available (multiplying over full grid).")
#         aoi_mask = np.ones_like(dem, dtype=bool)

#     master_stats_csv = STATS_DIR / f"a_factor_stats_master_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

#     for y in YEARS:
#         r_path  = FACTORS_DIR / f"r_factor_{y}.tif"
#         k_path  = FACTORS_DIR / "k_factor.tif"
#         ls_path = FACTORS_DIR / "ls_factor.tif"
#         c_path  = FACTORS_DIR / f"c_factor_{y}.tif"
#         p_path  = FACTORS_DIR / f"p_factor_{y}.tif"

#         # existence checks
#         for pth in (r_path, k_path, ls_path, c_path, p_path):
#             if not pth.exists():
#                 logger.error(f"Missing factor raster: {pth}")
#                 return False

#         logger.info(f"Computing A for {y}…")

#         # load with correct zero policy
#         R  = load_factor(r_path,  dem_prof, dem, aoi_mask, allow_zero=False)
#         K  = load_factor(k_path,  dem_prof, dem, aoi_mask, allow_zero=False)
#         LS = load_factor(ls_path, dem_prof, dem, aoi_mask, allow_zero=False)
#         C  = load_factor(c_path,  dem_prof, dem, aoi_mask, allow_zero=True)   # keep 0 valid
#         P  = load_factor(p_path,  dem_prof, dem, aoi_mask, allow_zero=True)   # keep 0 valid

#         # valid where ALL factors are valid AND inside AOI
#         valid = (R != NODATA) & (K != NODATA) & (LS != NODATA) & \
#                 (C != NODATA) & (P != NODATA) & aoi_mask

#         # multiply
#         A = np.full_like(R, NODATA, dtype=np.float32)
#         A[valid] = R[valid] * K[valid] * LS[valid] * C[valid] * P[valid]

#         # clean up infinities / negatives; keep zeros as zeros
#         badA = (~np.isfinite(A)) | (A < 0)
#         A[badA] = NODATA

#         # save GeoTIFF
#         a_tif = EROSION_DIR / f"a_factor_{y}.tif"
#         out_prof = dem_prof.copy()
#         out_prof.update({"dtype": "float32", "nodata": NODATA})
#         save_geotiff(a_tif, A, out_prof)
#         logger.info(f"Saved A raster: {a_tif}")

#         # stats (+ master)
#         s = stats_row(y, A)
#         per_csv = STATS_DIR / f"a_factor_stats_{y}.csv"
#         write_csv(per_csv, s)
#         write_csv(master_stats_csv, s)
#         logger.info(f"A stats {y}: min={s['min']}  mean={s['mean']}  median={s['median']}  "
#                     f"max={s['max']}  std={s['std']}  n={s['valid_count']} (coverage {s['coverage_pct']:.2f}%)")

#         # quicklook PNG
#         fig_path = FIG_DIR / f"a_factor_{y}.png"
#         save_quicklook_png(fig_path, A, title=f"A-factor {y} (t/ha/yr)")
#         logger.info(f"Saved A figure: {fig_path}")

#     logger.info(f"Saved master A stats CSV: {master_stats_csv}")
#     logger.info("A-factor calculation completed.")
#     logger.info("=" * 80)
#     return True

# if __name__ == "__main__":
#     sys.exit(0 if main() else 1)
"""
RUSLE Annual Soil Loss (A) = R * K * LS * C * P
- Uses already prepared per-year rasters aligned to the DEM grid @ 90 m.
- Multiplies STRICTLY inside AOI (if available).
- Keeps C/P = 0 as valid (do NOT convert to nodata).
- Enforces consistent nodata (-9999.0) across intermediates and outputs.
- Outputs:
    GeoTIFFs:  temp/erosion/a_factor_<year>.tif
    Figures:   outputs/figures/erosion/a_factor_<year>.png
    Stats:     outputs/statistics/erosion/a_factor_stats_<year>.csv
    Master:    outputs/statistics/erosion/a_factor_stats_master_<ts>.csv
"""

import sys
from pathlib import Path
from datetime import datetime
import logging
import csv
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

FACTORS_DIR = BASE_DIR / "temp" / "factors"
EROSION_DIR = BASE_DIR / "temp" / "erosion"                  # GeoTIFFs (A)
FIG_DIR     = BASE_DIR / "outputs" / "figures" / "erosion"   # PNGs
STATS_DIR   = BASE_DIR / "outputs" / "statistics" / "erosion"# CSVs
AOI_SHP     = BASE_DIR / "catchment" / "Mula_Mutha_Catchment.shp"
DEM_PATH    = BASE_DIR / "temp" / "dem_srtm_90m.tif"

AOI_DIR    = BASE_DIR / "temp" / "aoi"
AOI_MASK_CANDIDATES = [
    AOI_DIR / "aoi_mask_90m.tif",
    AOI_DIR / "aoi_mask.tif",
]

YEARS = list(range(2016, 2026))  # 2016..2025
NODATA = -9999.0

# Optional config (colors/paths)
try:
    sys.path.insert(0, str(SCRIPTS_DIR))
    import config as _cfg  # type: ignore
    # pull overrides from config if defined
    FACTORS_DIR = getattr(_cfg, "FACTORS_DIR", FACTORS_DIR)
    DEM_PATH    = getattr(_cfg, "DEM_PATH", DEM_PATH)
    YEARS       = getattr(_cfg, "YEARS", YEARS)
    AOI_MASK_CANDIDATES = getattr(
        _cfg, "AOI_MASK_RASTER_CANDIDATES", AOI_MASK_CANDIDATES
    )
    print("[OK] Configuration loaded successfully!")
    print(f"Analysis period: {YEARS[0]}-{YEARS[-1]} ({len(YEARS)} years)")
    print(f"Output directory: {BASE_DIR/'outputs'}")
    print(f"Target CRS: {getattr(_cfg, 'TARGET_CRS', 'EPSG:4326')}")
    try:
        import color_config as _cc  # type: ignore
        print("[OK] Standardized color configuration loaded")
    except Exception:
        pass
except Exception:
    print("[INFO] Using internal defaults (no scripts/config.py found)")

# ensure dirs
EROSION_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)
STATS_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------
# Logging
# ----------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_file = EROSION_DIR / f"07_a_factor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
for h in (logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)):
    h.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                                     "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(h)

# ----------------------------
# Helpers
# ----------------------------
def read_raster(path):
    with rasterio.open(path) as src:
        arr = src.read(1)
        prof = src.profile
    return arr, prof

def reproject_to_match(source_arr, source_prof, match_prof, categorical=False):
    dst = np.full((match_prof["height"], match_prof["width"]), NODATA, dtype=np.float32)
    resamp = Resampling.nearest if categorical else Resampling.bilinear
    warp.reproject(
        source=source_arr.astype(np.float32),
        destination=dst,
        src_transform=source_prof["transform"],
        src_crs=source_prof["crs"],
        dst_transform=match_prof["transform"],
        dst_crs=match_prof["crs"],
        dst_nodata=NODATA,
        resampling=resamp,
    )
    return dst

def _load_aoi_mask_from_raster(match_prof):
    """Try to load AOI mask from any AOI_MASK_CANDIDATES path.
       Reproject (nearest) to match DEM grid if needed. Returns bool mask or None."""
    for p in AOI_MASK_CANDIDATES:
        try:
            if not p.exists():
                continue
            arr, prof = read_raster(p)
            # if not same grid, reproject with nearest (categorical)
            if (prof["crs"] != match_prof["crs"] or
                prof["transform"] != match_prof["transform"] or
                prof["width"] != match_prof["width"] or
                prof["height"] != match_prof["height"]):
                logger.info(f"AOI raster grid mismatch for {p.name}; reprojecting to DEM grid.")
                arr = reproject_to_match(arr, prof, match_prof, categorical=True)
            mask = (arr > 0).astype(bool)
            cov = 100.0 * mask.mean()
            logger.info(f"Using AOI raster: {p} (coverage on DEM grid: {cov:.2f}%)")
            return mask
        except Exception as e:
            logger.warning(f"Failed loading AOI raster {p}: {e}")
    return None

def _load_aoi_mask_from_shapefile(match_prof):
    """Rasterize AOI from catchment shapefile (fallback)."""
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
        ).astype(bool)
        logger.info(f"Using AOI from shapefile: {AOI_SHP}")
        logger.info(f"AOI mask: {int(mask.sum())} / {mask.size} pixels inside ({100*mask.mean():.2f}%).")
        return mask
    except Exception as e:
        logger.warning(f"AOI mask from shapefile failed: {e}")
        return None

def load_aoi_mask(match_prof):
    """Prefer AOI raster; fallback to shapefile; else None."""
    m = _load_aoi_mask_from_raster(match_prof)
    if m is not None:
        return m
    return _load_aoi_mask_from_shapefile(match_prof)

def save_geotiff(path, data, profile):
    prof = profile.copy()
    prof.update({
        "driver": "GTiff",
        "count": 1,
        "dtype": "float32",
        "compress": "lzw",
        "nodata": NODATA
    })
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(data.astype(np.float32), 1)

def robust_limits(a, vmin_pct=2.0, vmax_pct=98.0):
    vals = a[np.isfinite(a) & (a > 0)]
    if vals.size == 0:
        return 0.0, 1.0
    lo = np.percentile(vals, vmin_pct)
    hi = np.percentile(vals, vmax_pct)
    if hi <= lo:
        hi = float(vals.max())
        lo = float(vals.min())
    return float(lo), float(hi)

def save_quicklook_png(path, data, title="A-factor (t/ha/yr)"):
    try:
        import matplotlib.pyplot as plt
        view = np.where((~np.isfinite(data)) | (data == NODATA) | (data <= 0), np.nan, data)
        vmin, vmax = robust_limits(view)
        plt.figure(figsize=(10, 7))
        im = plt.imshow(view, cmap="YlOrRd", vmin=vmin, vmax=vmax)
        cbar = plt.colorbar(im, shrink=0.8)
        cbar.set_label("A (t·ha⁻¹·yr⁻¹)")
        plt.title(title)
        plt.xlabel("pixels (lon)")
        plt.ylabel("pixels (lat)")
        plt.tight_layout()
        plt.savefig(path, dpi=150)
        plt.close()
    except Exception as e:
        logger.warning(f"Could not create PNG: {e}")

def stats_row(year, arr):
    m = np.isfinite(arr) & (arr != NODATA)   # include zeros if they exist
    if not m.any():
        return {"year": year, "min": None, "mean": None, "median": None, "max": None,
                "std": None, "valid_count": 0, "total_pixels": int(arr.size), "coverage_pct": 0.0}
    vals = arr[m]
    return {
        "year": year,
        "min": float(vals.min()),
        "mean": float(vals.mean()),
        "median": float(np.median(vals)),
        "max": float(vals.max()),
        "std": float(vals.std()),
        "valid_count": int(vals.size),
        "total_pixels": int(arr.size),
        "coverage_pct": float(vals.size / arr.size * 100.0),
    }

def write_csv(path, row):
    new = not Path(path).exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if new:
            w.writeheader()
        w.writerow(row)

# factor loader with zero-policy control
def load_factor(path, dem_prof, dem, aoi_mask, allow_zero=False):
    arr, prof = read_raster(path)
    # accept exact matches fast
    if (prof["crs"] == dem_prof["crs"] and
        prof["transform"] == dem_prof["transform"] and
        prof["width"] == dem_prof["width"] and
        prof["height"] == dem_prof["height"]):
        aligned = arr.astype(np.float32)
    else:
        aligned = reproject_to_match(arr, prof, dem_prof, categorical=False)

    # AOI hard mask first
    if aoi_mask is not None:
        aligned[~aoi_mask] = NODATA
    # respect DEM nodata
    if dem_prof.get("nodata", None) is not None:
        aligned[dem == dem_prof["nodata"]] = NODATA

    # sanitize per zero-policy:
    #  - if allow_zero=True (C,P): keep zeros; only <0 or non-finite -> nodata
    #  - else (R,K,LS): require >0; <=0 or non-finite -> nodata
    if allow_zero:
        bad = (~np.isfinite(aligned)) | (aligned < 0)
    else:
        bad = (~np.isfinite(aligned)) | (aligned <= 0)
    aligned[bad] = NODATA
    return aligned

# ----------------------------
# Main
# ----------------------------
def main():
    logger.info("")
    logger.info("=" * 80)
    logger.info("RUSLE A-FACTOR (soil loss) CALCULATION")
    logger.info("=" * 80)

    # DEM (master grid)
    dem, dem_prof = read_raster(DEM_PATH)
    if dem_prof.get("nodata", None) is None:
        dem_prof["nodata"] = NODATA
    logger.info(f"DEM grid: CRS={dem_prof['crs']}  shape={dem.shape}  nodata={dem_prof.get('nodata')}")

    # AOI mask (prefer AOI raster; fallback to shapefile; else full grid)
    aoi_mask = load_aoi_mask(dem_prof)
    if aoi_mask is None:
        logger.info("AOI mask: not available (multiplying over full grid).")
        aoi_mask = np.ones_like(dem, dtype=bool)

    master_stats_csv = STATS_DIR / f"a_factor_stats_master_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    for y in YEARS:
        r_path  = FACTORS_DIR / f"r_factor_{y}.tif"
        k_path  = FACTORS_DIR / "k_factor.tif"
        ls_path = FACTORS_DIR / "ls_factor.tif"
        c_path  = FACTORS_DIR / f"c_factor_{y}.tif"
        p_path  = FACTORS_DIR / f"p_factor_{y}.tif"

        # existence checks
        for pth in (r_path, k_path, ls_path, c_path, p_path):
            if not pth.exists():
                logger.error(f"Missing factor raster: {pth}")
                return False

        logger.info(f"Computing A for {y}…")

        # load with correct zero policy
        R  = load_factor(r_path,  dem_prof, dem, aoi_mask, allow_zero=False)
        K  = load_factor(k_path,  dem_prof, dem, aoi_mask, allow_zero=False)
        LS = load_factor(ls_path, dem_prof, dem, aoi_mask, allow_zero=False)
        C  = load_factor(c_path,  dem_prof, dem, aoi_mask, allow_zero=True)   # keep 0 valid
        P  = load_factor(p_path,  dem_prof, dem, aoi_mask, allow_zero=True)   # keep 0 valid

        # valid where ALL factors are valid AND inside AOI
        valid = (R != NODATA) & (K != NODATA) & (LS != NODATA) & \
                (C != NODATA) & (P != NODATA) & aoi_mask

        # multiply
        A = np.full_like(R, NODATA, dtype=np.float32)
        A[valid] = R[valid] * K[valid] * LS[valid] * C[valid] * P[valid]

        # clean up infinities / negatives; keep zeros as zeros
        badA = (~np.isfinite(A)) | (A < 0)
        A[badA] = NODATA

        # save GeoTIFF
        a_tif = EROSION_DIR / f"a_factor_{y}.tif"
        out_prof = dem_prof.copy()
        out_prof.update({"dtype": "float32", "nodata": NODATA})
        save_geotiff(a_tif, A, out_prof)
        logger.info(f"Saved A raster: {a_tif}")

        # stats (+ master)
        s = stats_row(y, A)
        per_csv = STATS_DIR / f"a_factor_stats_{y}.csv"
        write_csv(per_csv, s)
        write_csv(master_stats_csv, s)
        logger.info(f"A stats {y}: min={s['min']}  mean={s['mean']}  median={s['median']}  "
                    f"max={s['max']}  std={s['std']}  n={s['valid_count']} (coverage {s['coverage_pct']:.2f}%)")

        # quicklook PNG
        fig_path = FIG_DIR / f"a_factor_{y}.png"
        save_quicklook_png(fig_path, A, title=f"A-factor {y} (t/ha/yr)")
        logger.info(f"Saved A figure: {fig_path}")

    logger.info(f"Saved master A stats CSV: {master_stats_csv}")
    logger.info("A-factor calculation completed.")
    logger.info("=" * 80)
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
