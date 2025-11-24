# # # scripts/make_overlay_maps.py  (patched)
# # from pathlib import Path
# # import numpy as np
# # import rasterio
# # from rasterio.enums import Resampling
# # from rasterio import warp as rio_warp
# # import geopandas as gpd
# # import matplotlib.pyplot as plt
# # from matplotlib.patches import Patch
# # import contextily as ctx
# # import matplotlib.colors as mcolors

# # BASE = Path(__file__).resolve().parents[1]
# # A_DIR = BASE / "temp" / "erosion"
# # AOI_MASK = BASE / "temp" / "aoi" / "aoi_mask.tif"
# # AOI_SHP  = BASE / "catchment" / "Mula_Mutha_Catchment.shp"
# # OUT_DIR  = BASE / "outputs" / "maps"
# # OUT_DIR.mkdir(parents=True, exist_ok=True)

# # NODATA = -9999.0
# # PALETTE = ["#006837", "#7CB342", "#FFEB3B", "#FF9800", "#D32F2F"]  # Very Low..Very High
# # BINS = np.array([0, 5, 10, 20, 40, np.inf])  # t/ha/yr

# # def _read1(path):
# #     with rasterio.open(path) as src:
# #         arr = src.read(1)
# #         prof = src.profile
# #     return arr, prof

# # def _to_mercator_raster(arr, src_prof):
# #     dst_crs = "EPSG:3857"
# #     left, bottom, right, top = rasterio.transform.array_bounds(
# #         src_prof["height"], src_prof["width"], src_prof["transform"]
# #     )
# #     dst_transform, width, height = rio_warp.calculate_default_transform(
# #         src_prof["crs"], dst_crs, src_prof["width"], src_prof["height"],
# #         left=left, bottom=bottom, right=right, top=top
# #     )
# #     dst = np.full((height, width), NODATA, dtype=np.float32)
# #     rio_warp.reproject(
# #         source=arr.astype(np.float32),
# #         destination=dst,
# #         src_transform=src_prof["transform"],
# #         src_crs=src_prof["crs"],
# #         dst_transform=dst_transform,
# #         dst_crs=dst_crs,
# #         dst_nodata=NODATA,
# #         resampling=Resampling.nearest,
# #     )
# #     return dst, dst_transform

# # def _extent(transform, width, height):
# #     left = transform.c
# #     top = transform.f
# #     right = left + transform.a * width
# #     bottom = top + transform.e * height
# #     # contextily expects (W, E, S, N) for extent on imshow
# #     return (left, right, bottom, top)

# # def _classify(a_float):
# #     m = np.isfinite(a_float) & (a_float != NODATA) & (a_float >= 0)
# #     classes = np.full(a_float.shape, -1, dtype=np.int16)
# #     classes[m] = np.digitize(a_float[m], BINS, right=False) - 1  # 0..4
# #     return classes

# # def _fetch_basemap(W, S, E, N, source, zooms=(12, 11, 10, 9)):
# #     last_err = None
# #     for z in zooms:
# #         try:
# #             img, ext = ctx.bounds2img(W, S, E, N, zoom=z, source=source)
# #             return img, ext, z
# #         except Exception as e:
# #             last_err = e
# #     raise last_err if last_err else RuntimeError("Basemap fetch failed")

# # def make_overlay(year: int, alpha=0.55, basemap=ctx.providers.Esri.WorldImagery):
# #     a_path = A_DIR / f"a_factor_{year}.tif"
# #     if not a_path.exists():
# #         raise FileNotFoundError(a_path)

# #     a_arr, a_prof = _read1(a_path)

# #     # AOI mask (prefer raster)
# #     aoi_mask = None
# #     if AOI_MASK.exists():
# #         mask_arr, m_prof = _read1(AOI_MASK)
# #         if (m_prof["crs"] != a_prof["crs"] or
# #             m_prof["transform"] != a_prof["transform"] or
# #             m_prof["width"] != a_prof["width"] or
# #             m_prof["height"] != a_prof["height"]):
# #             mask_dst = np.zeros_like(a_arr, dtype=np.float32)
# #             rio_warp.reproject(
# #                 source=mask_arr.astype(np.float32),
# #                 destination=mask_dst,
# #                 src_transform=m_prof["transform"],
# #                 src_crs=m_prof["crs"],
# #                 dst_transform=a_prof["transform"],
# #                 dst_crs=a_prof["crs"],
# #                 dst_nodata=0,
# #                 resampling=Resampling.nearest,
# #             )
# #             aoi_mask = (mask_dst > 0.5)
# #         else:
# #             aoi_mask = (mask_arr > 0.5)
# #     if aoi_mask is not None:
# #         a_arr = np.where(aoi_mask, a_arr, NODATA)

# #     # Reproject to Web Mercator
# #     a_m, a_m_tx = _to_mercator_raster(a_arr, a_prof)
# #     W, E, S, N = _extent(a_m_tx, a_m.shape[1], a_m.shape[0])

# #     # Optional AOI outline
# #     aoi_outline = None
# #     if AOI_SHP.exists():
# #         try:
# #             gdf = gpd.read_file(AOI_SHP)
# #             if gdf.crs is None or gdf.crs.to_string() != "EPSG:3857":
# #                 gdf = gdf.to_crs("EPSG:3857")
# #             aoi_outline = gdf
# #         except Exception:
# #             aoi_outline = None

# #     # Get basemap tiles with robust zoom selection
# #     img, ext, used_zoom = _fetch_basemap(W, S, E, N, source=basemap)

# #     # Build RGBA overlay
# #     classes = _classify(a_m)
# #     rgba = np.zeros((classes.shape[0], classes.shape[1], 4), dtype=np.float32)
# #     color_list = [mcolors.to_rgba(c, alpha=alpha) for c in PALETTE]
# #     for k in range(5):
# #         m = (classes == k)
# #         if m.any():
# #             rgba[m] = color_list[k]

# #     # Plot
# #     fig, ax = plt.subplots(figsize=(10.5, 7.5), dpi=150)
# #     ax.imshow(img, extent=ext)  # basemap
# #     ax.imshow(rgba, extent=ext, interpolation="nearest")  # overlay

# #     # AOI outline
# #     if aoi_outline is not None and not aoi_outline.empty:
# #         aoi_outline.boundary.plot(ax=ax, color="white", linewidth=1.2, alpha=0.9, zorder=9)
# #         aoi_outline.boundary.plot(ax=ax, color="black", linewidth=0.6, alpha=0.9, zorder=10)

# #     # Legend
# #     handles = [
# #         Patch(facecolor=PALETTE[0], edgecolor='black', label='Very Low (<5)'),
# #         Patch(facecolor=PALETTE[1], edgecolor='black', label='Low (5–10)'),
# #         Patch(facecolor=PALETTE[2], edgecolor='black', label='Moderate (10–20)'),
# #         Patch(facecolor=PALETTE[3], edgecolor='black', label='High (20–40)'),
# #         Patch(facecolor=PALETTE[4], edgecolor='black', label='Very High (>40)'),
# #     ]
# #     ax.legend(handles=handles, loc="lower left", frameon=True, fontsize=8)
# #     ax.set_title(f"Soil Loss (A) on Physical Basemap — {year}  [zoom {used_zoom}]", fontsize=12, weight="bold")
# #     ax.set_xlim([W, E]); ax.set_ylim([S, N])
# #     ax.axis("off")
# #     fig.tight_layout()

# #     out = OUT_DIR / f"soil_loss_on_basemap_{year}.png"
# #     fig.savefig(out, bbox_inches="tight", pad_inches=0.1)
# #     plt.close(fig)
# #     print(f"[OK] Saved {out}")

# # def make_all():
# #     for y in range(2016, 2026):
# #         try:
# #             make_overlay(y)
# #         except Exception as e:
# #             print(f"[WARN] {y}: {e}")

# # if __name__ == "__main__":
# #     make_all()


# # scripts/make_overlay_maps.py  — labeled + high-contrast overlay
# from pathlib import Path
# import numpy as np
# import rasterio
# from rasterio.enums import Resampling
# from rasterio import warp as rio_warp
# import geopandas as gpd
# import matplotlib.pyplot as plt
# from matplotlib.patches import Patch
# import matplotlib.colors as mcolors
# import contextily as ctx
# from pyproj import Transformer

# BASE = Path(__file__).resolve().parents[1]
# A_DIR     = BASE / "temp" / "erosion"
# AOI_MASK  = BASE / "temp" / "aoi" / "aoi_mask.tif"
# AOI_SHP   = BASE / "catchment" / "Mula_Mutha_Catchment.shp"
# OUT_DIR   = BASE / "outputs" / "maps"
# OUT_DIR.mkdir(parents=True, exist_ok=True)

# NODATA   = -9999.0
# PALETTE  = ["#006837", "#7CB342", "#FFEB3B", "#FF9800", "#D32F2F"]   # Very Low..Very High
# FIXED_BINS = np.array([0, 5, 10, 20, 40, np.inf])                    # t/ha/yr

# # Labelled basemap
# BASEMAP = ctx.providers.CartoDB.Positron  # clean with city/road labels

# # Major locations (lon, lat) to annotate (expand if you want)
# CITY_POINTS = [
#     ("Pune",               73.8567, 18.5204),
#     ("Pimpri-Chinchwad",   73.7997, 18.6298),
#     ("Hadapsar",           73.9345, 18.5039),
#     ("Kothrud",            73.8077, 18.5074),
#     ("Sinhagad Fort",      73.7550, 18.3660),
#     ("Lonavala",           73.4070, 18.7557),
#     ("Talegaon",           73.6760, 18.7260),
#     ("Saswad",             74.0316, 18.3438),
# ]

# def _read1(path):
#     with rasterio.open(path) as src:
#         arr = src.read(1)
#         prof = src.profile
#     return arr, prof

# def _extent(transform, width, height):
#     left = transform.c
#     top = transform.f
#     right = left + transform.a * width
#     bottom = top + transform.e * height
#     # contextily expects (W, E, S, N)
#     return (left, right, bottom, top)

# def _to_mercator_raster(arr, src_prof):
#     dst_crs = "EPSG:3857"
#     left, bottom, right, top = rasterio.transform.array_bounds(
#         src_prof["height"], src_prof["width"], src_prof["transform"]
#     )
#     dst_transform, width, height = rio_warp.calculate_default_transform(
#         src_prof["crs"], dst_crs, src_prof["width"], src_prof["height"],
#         left=left, bottom=bottom, right=right, top=top
#     )
#     dst = np.full((height, width), NODATA, dtype=np.float32)
#     rio_warp.reproject(
#         source=arr.astype(np.float32),
#         destination=dst,
#         src_transform=src_prof["transform"],
#         src_crs=src_prof["crs"],
#         dst_transform=dst_transform,
#         dst_crs=dst_crs,
#         dst_nodata=NODATA,
#         resampling=Resampling.nearest,
#     )
#     return dst, dst_transform

# def _fetch_basemap(W, S, E, N, source, zooms=(12, 11, 10, 9)):
#     last_err = None
#     for z in zooms:
#         try:
#             img, ext = ctx.bounds2img(W, S, E, N, zoom=z, source=source)
#             return img, ext, z
#         except Exception as e:
#             last_err = e
#     raise last_err if last_err else RuntimeError("Basemap fetch failed")

# def _classify_fixed(a):
#     m = np.isfinite(a) & (a != NODATA) & (a >= 0)
#     classes = np.full(a.shape, -1, dtype=np.int16)
#     classes[m] = np.digitize(a[m], FIXED_BINS, right=False) - 1  # 0..4
#     return classes, ["Very Low (<5)", "Low (5–10)", "Moderate (10–20)", "High (20–40)", "Very High (>40)"]

# def _classify_quantiles(a, q=(0.60, 0.80, 0.90, 0.97)):
#     # Spread colors across your actual distribution for visibility
#     m = np.isfinite(a) & (a != NODATA) & (a >= 0)
#     classes = np.full(a.shape, -1, dtype=np.int16)
#     if not np.any(m):
#         return classes, ["Q1","Q2","Q3","Q4","Q5"]
#     vals = a[m]
#     # protect against degenerate distributions
#     qs = np.unique(np.clip(np.quantile(vals, q), a_min=0.0, a_max=np.nanmax(vals)))
#     # Build monotonically increasing bin edges from 0 -> max with these quantiles
#     edges = [0.0] + list(qs) + [float(np.nanmax(vals)) + 1e-6]
#     edges = np.array(edges)
#     classes[m] = np.digitize(vals, edges, right=False) - 1
#     labels = [
#         f"{edges[0]:.2f}–{edges[1]:.2f}",
#         f"{edges[1]:.2f}–{edges[2]:.2f}",
#         f"{edges[2]:.2f}–{edges[3]:.2f}",
#         f"{edges[3]:.2f}–{edges[4]:.2f}",
#         f">{edges[4]:.2f}",
#     ] if len(edges) == 6 else ["Q1","Q2","Q3","Q4","Q5"]
#     return classes, labels

# def _annotate_cities(ax, extent, crs_from="EPSG:4326", crs_to="EPSG:3857"):
#     transformer = Transformer.from_crs(crs_from, crs_to, always_xy=True)
#     for name, lon, lat in CITY_POINTS:
#         x, y = transformer.transform(lon, lat)
#         # Only draw if inside map extent
#         W, E, S, N = extent
#         if (W <= x <= E) and (S <= y <= N):
#             ax.plot(x, y, marker='o', markersize=3.5, color='black', zorder=12)
#             ax.text(x + 500, y + 500, name, fontsize=8, weight='bold',
#                     color='black', zorder=12,
#                     path_effects=[], ha='left', va='bottom',
#                     bbox=dict(facecolor='white', edgecolor='none', alpha=0.65, boxstyle='round,pad=0.2'))

# def make_overlay(year: int, mode="quantile", alpha=0.70):
#     """
#     mode: "quantile" (better contrast) or "fixed" (publication bins)
#     """
#     a_path = A_DIR / f"a_factor_{year}.tif"
#     if not a_path.exists():
#         raise FileNotFoundError(a_path)

#     a_arr, a_prof = _read1(a_path)

#     # AOI mask application (prefer raster)
#     if AOI_MASK.exists():
#         mask_arr, m_prof = _read1(AOI_MASK)
#         if (m_prof["crs"] != a_prof["crs"] or
#             m_prof["transform"] != a_prof["transform"] or
#             m_prof["width"] != a_prof["width"] or
#             m_prof["height"] != a_prof["height"]):
#             mask_dst = np.zeros_like(a_arr, dtype=np.float32)
#             rio_warp.reproject(
#                 source=mask_arr.astype(np.float32),
#                 destination=mask_dst,
#                 src_transform=m_prof["transform"],
#                 src_crs=m_prof["crs"],
#                 dst_transform=a_prof["transform"],
#                 dst_crs=a_prof["crs"],
#                 dst_nodata=0,
#                 resampling=Resampling.nearest,
#             )
#             a_arr = np.where(mask_dst > 0.5, a_arr, NODATA)
#         else:
#             a_arr = np.where(mask_arr > 0.5, a_arr, NODATA)

#     # Reproject to Web Mercator
#     a_m, a_m_tx = _to_mercator_raster(a_arr, a_prof)
#     W, E, S, N = _extent(a_m_tx, a_m.shape[1], a_m.shape[0])

#     # Classify
#     if mode == "fixed":
#         classes, labels = _classify_fixed(a_m)
#         title_suffix = "(Fixed bins: <5, 5–10, 10–20, 20–40, >40)"
#     else:
#         classes, labels = _classify_quantiles(a_m)
#         title_suffix = "(Quantile bins for visibility)"

#     # Basemap with labels
#     img, ext, z = _fetch_basemap(W, S, E, N, source=BASEMAP)

#     # Build RGBA overlay
#     rgba = np.zeros((classes.shape[0], classes.shape[1], 4), dtype=np.float32)
#     color_list = [mcolors.to_rgba(c, alpha=alpha) for c in PALETTE]
#     for k in range(5):
#         mask = (classes == k)
#         if mask.any():
#             rgba[mask] = color_list[k]

#     # AOI outline (optional but nice)
#     aoi_outline = None
#     if AOI_SHP.exists():
#         try:
#             gdf = gpd.read_file(AOI_SHP)
#             if gdf.crs is None or gdf.crs.to_string() != "EPSG:3857":
#                 gdf = gdf.to_crs("EPSG:3857")
#             aoi_outline = gdf
#         except Exception:
#             aoi_outline = None

#     # Plot
#     fig, ax = plt.subplots(figsize=(10.5, 7.5), dpi=150)
#     ax.imshow(img, extent=ext)                               # basemap (with labels)
#     ax.imshow(rgba, extent=ext, interpolation="nearest")     # our A overlay

#     if aoi_outline is not None and not aoi_outline.empty:
#         aoi_outline.boundary.plot(ax=ax, color="white", linewidth=1.2, alpha=0.9, zorder=11)
#         aoi_outline.boundary.plot(ax=ax, color="black", linewidth=0.6, alpha=0.9, zorder=12)

#     # City names
#     _annotate_cities(ax, ext)

#     # Legend
#     handles = [Patch(facecolor=PALETTE[i], edgecolor='black', label=lab) for i, lab in enumerate(labels)]
#     ax.legend(handles=handles, loc="lower left", frameon=True, fontsize=8)
#     ax.set_title(f"Soil Loss (A) on Labeled Basemap — {year}  {title_suffix}", fontsize=12, weight="bold")
#     ax.set_xlim([W, E]); ax.set_ylim([S, N])
#     ax.axis("off")
#     fig.tight_layout()

#     out = OUT_DIR / f"soil_loss_on_basemap_{year}.png"
#     fig.savefig(out, bbox_inches="tight", pad_inches=0.1)
#     plt.close(fig)
#     print(f"[OK] Saved {out}")

# def make_all(mode="quantile"):
#     for y in range(2016, 2026):
#         try:
#             make_overlay(y, mode=mode)
#         except Exception as e:
#             print(f"[WARN] {y}: {e}")

# if __name__ == "__main__":
#     # Choose "quantile" for contrast, "fixed" for publication-ready bins
#     make_all(mode="quantile")


# scripts/make_overlay_maps.py — bigger colored basemap + global bins
from pathlib import Path
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio import warp as rio_warp
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import matplotlib.colors as mcolors
import contextily as ctx
from pyproj import Transformer

BASE = Path(__file__).resolve().parents[1]
A_DIR     = BASE / "temp" / "erosion"
AOI_MASK  = BASE / "temp" / "aoi" / "aoi_mask.tif"
AOI_SHP   = BASE / "catchment" / "Mula_Mutha_Catchment.shp"
OUT_DIR   = BASE / "outputs" / "maps"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# SciHawk Soil Degradation palette (Very Low → Very High)
PALETTE = ["#006837", "#7CB342", "#FFEB3B", "#FF9800", "#D32F2F"]
NODATA  = -9999.0

# Colored, labelled basemap (no white)
BASEMAP = ctx.providers.Esri.WorldTopoMap

# more surroundings visible
PADDING_FRAC = 0.18      # 18% padding around AOI extent
FIGSIZE       = (12.5, 9)  # bigger figure
DPI           = 170
ALPHA         = 0.70

YEARS = list(range(2016, 2026))

CITY_POINTS = [
    ("Pune",               73.8567, 18.5204),
    ("Pimpri-Chinchwad",   73.7997, 18.6298),
    ("Lonavala",           73.4070, 18.7557),
    ("Talegaon",           73.6760, 18.7260),
    ("Sinhagad Fort",      73.7550, 18.3660),
    ("Hadapsar",           73.9345, 18.5039),
    ("Saswad",             74.0316, 18.3438),
]

def _read1(path):
    with rasterio.open(path) as src:
        return src.read(1), src.profile

def _to_mercator_raster(arr, prof):
    dst_crs = "EPSG:3857"
    left, bottom, right, top = rasterio.transform.array_bounds(
        prof["height"], prof["width"], prof["transform"]
    )
    dst_tx, w, h = rio_warp.calculate_default_transform(
        prof["crs"], dst_crs, prof["width"], prof["height"],
        left=left, bottom=bottom, right=right, top=top
    )
    dst = np.full((h, w), NODATA, dtype=np.float32)
    rio_warp.reproject(
        source=arr.astype(np.float32),
        destination=dst,
        src_transform=prof["transform"],
        src_crs=prof["crs"],
        dst_transform=dst_tx,
        dst_crs=dst_crs,
        dst_nodata=NODATA,
        resampling=Resampling.nearest,
    )
    return dst, dst_tx

def _extent(tx, w, h, pad_frac=PADDING_FRAC):
    left = tx.c; top = tx.f
    right = left + tx.a * w
    bottom = top + tx.e * h
    W, E, S, N = (left, right, bottom, top)
    # pad
    dx = (E - W) * pad_frac
    dy = (N - S) * pad_frac
    return (W - dx, E + dx, S - dy, N + dy)

def _fetch_basemap(W, S, E, N, source=BASEMAP):
    # try a couple zooms
    for z in (12, 11, 10, 9):
        try:
            img, ext = ctx.bounds2img(W, S, E, N, zoom=z, source=source)
            return img, ext
        except Exception:
            continue
    # last resort
    return ctx.bounds2img(W, S, E, N, zoom=8, source=source)

def _annotate_cities(ax, extent):
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    W, E, S, N = extent
    for name, lon, lat in CITY_POINTS:
        x, y = transformer.transform(lon, lat)
        if (W <= x <= E) and (S <= y <= N):
            ax.plot(x, y, marker='o', markersize=3.8, color='black', zorder=12)
            ax.text(x + 600, y + 600, name, fontsize=9, weight='bold',
                    color='black', zorder=12,
                    bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='round,pad=0.2'))

def _apply_aoi_mask(arr, prof):
    if not AOI_MASK.exists():
        return arr
    m_arr, m_prof = _read1(AOI_MASK)
    if (m_prof["crs"] != prof["crs"] or
        m_prof["transform"] != prof["transform"] or
        m_prof["width"] != prof["width"] or
        m_prof["height"] != prof["height"]):
        m_dst = np.zeros_like(arr, dtype=np.float32)
        rio_warp.reproject(
            source=m_arr.astype(np.float32),
            destination=m_dst,
            src_transform=m_prof["transform"],
            src_crs=m_prof["crs"],
            dst_transform=prof["transform"],
            dst_crs=prof["crs"],
            dst_nodata=0,
            resampling=Resampling.nearest,
        )
        return np.where(m_dst > 0.5, arr, NODATA)
    return np.where(m_arr > 0.5, arr, NODATA)

# ---------- classification strategies ----------
def compute_global_quantile_edges():
    """One set of edges for ALL years → maps won’t look identical; differences are real."""
    samples = []
    for y in YEARS:
        p = A_DIR / f"a_factor_{y}.tif"
        if not p.exists(): 
            continue
        a, prof = _read1(p)
        a = _apply_aoi_mask(a, prof)
        v = a[np.isfinite(a) & (a != NODATA) & (a >= 0)]
        if v.size:
            # subsample to keep memory light
            if v.size > 800_000:
                idx = np.random.choice(v.size, 800_000, replace=False)
                v = v[idx]
            samples.append(v)
    if not samples:
        # fallback
        return np.array([0, 0.1, 0.5, 1.5, 4.0, np.inf])
    allv = np.concatenate(samples)
    q = np.quantile(allv, [0.50, 0.75, 0.90, 0.97])  # tune if needed
    edges = np.array([0.0, *q, float(np.nanmax(allv)) + 1e-6])
    return edges

GLOBAL_EDGES = compute_global_quantile_edges()  # 6 edges → 5 classes

def classify_global(a_m):
    m = np.isfinite(a_m) & (a_m != NODATA) & (a_m >= 0)
    classes = np.full(a_m.shape, -1, dtype=np.int16)
    classes[m] = np.digitize(a_m[m], GLOBAL_EDGES, right=False) - 1
    labels = [
        f"{GLOBAL_EDGES[0]:.2f}–{GLOBAL_EDGES[1]:.2f}",
        f"{GLOBAL_EDGES[1]:.2f}–{GLOBAL_EDGES[2]:.2f}",
        f"{GLOBAL_EDGES[2]:.2f}–{GLOBAL_EDGES[3]:.2f}",
        f"{GLOBAL_EDGES[3]:.2f}–{GLOBAL_EDGES[4]:.2f}",
        f">{GLOBAL_EDGES[4]:.2f}",
    ]
    return classes, labels

def classify_log(a_m):
    # log-spread mid-range so maps don’t collapse to green
    bins = np.array([0.0, 0.05, 0.20, 0.80, 3.20, np.inf])
    m = np.isfinite(a_m) & (a_m != NODATA) & (a_m >= 0)
    classes = np.full(a_m.shape, -1, dtype=np.int16)
    classes[m] = np.digitize(a_m[m], bins, right=False) - 1
    labels = ["<0.05", "0.05–0.20", "0.20–0.80", "0.80–3.20", ">3.20"]
    return classes, labels

def render_year(year, mode="global"):  # mode: "global" or "log"
    a_path = A_DIR / f"a_factor_{year}.tif"
    if not a_path.exists():
        print(f"[WARN] missing {a_path}")
        return

    a, prof = _read1(a_path)
    a = _apply_aoi_mask(a, prof)
    a_m, tx_m = _to_mercator_raster(a, prof)
    W, E, S, N = _extent(tx_m, a_m.shape[1], a_m.shape[0], pad_frac=PADDING_FRAC)

    if mode == "log":
        classes, labels = classify_log(a_m)
        title_suffix = "(Log-spread bins)"
    else:
        classes, labels = classify_global(a_m)
        title_suffix = "(Global bins: same scale for 2016–2025)"

    # RGBA overlay
    rgba = np.zeros((classes.shape[0], classes.shape[1], 4), dtype=np.float32)
    color_list = [mcolors.to_rgba(c, alpha=ALPHA) for c in PALETTE]
    for k in range(5):
        m = (classes == k)
        if m.any():
            rgba[m] = color_list[k]

    # basemap
    img, ext = _fetch_basemap(W, S, E, N, source=BASEMAP)

    # AOI outline
    aoi_gdf = None
    if AOI_SHP.exists():
        try:
            aoi_gdf = gpd.read_file(AOI_SHP)
            if aoi_gdf.crs is None or aoi_gdf.crs.to_string() != "EPSG:3857":
                aoi_gdf = aoi_gdf.to_crs("EPSG:3857")
        except Exception:
            aoi_gdf = None

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    ax.imshow(img, extent=ext)
    ax.imshow(rgba, extent=ext, interpolation="nearest")

    if aoi_gdf is not None and not aoi_gdf.empty:
        aoi_gdf.boundary.plot(ax=ax, color="white", linewidth=1.3, alpha=0.95, zorder=11)
        aoi_gdf.boundary.plot(ax=ax, color="black", linewidth=0.7, alpha=0.9, zorder=12)

    _annotate_cities(ax, ext)

    handles = [Patch(facecolor=PALETTE[i], edgecolor='black', label=lab) for i, lab in enumerate(labels)]
    ax.legend(handles=handles, loc="lower left", frameon=True, fontsize=9)
    ax.set_title(f"Soil Loss (A) — {year}  {title_suffix}", fontsize=13, weight="bold")
    ax.set_xlim([ext[0], ext[1]]); ax.set_ylim([ext[2], ext[3]])
    ax.axis("off")
    fig.tight_layout()

    out = OUT_DIR / f"soil_loss_on_basemap_{year}.png"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print(f"[OK] {out}")

def make_all(mode="global"):
    for y in YEARS:
        render_year(y, mode=mode)

if __name__ == "__main__":
    # Choose one:
    #   mode="global"  → one scale for all years (recommended for comparison)
    #   mode="log"     → more mid-range contrast
    make_all(mode="global")
