# # scripts/make_overlay_maps.py — bigger colored basemap + global bins
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

# # SciHawk Soil Degradation palette (Very Low → Very High)
# PALETTE = ["#006837", "#7CB342", "#FFEB3B", "#FF9800", "#D32F2F"]
# NODATA  = -9999.0

# # Colored, labelled basemap (no white)
# BASEMAP = ctx.providers.Esri.WorldTopoMap

# # more surroundings visible
# PADDING_FRAC = 0.18      # 18% padding around AOI extent
# FIGSIZE       = (12.5, 9)  # bigger figure
# DPI           = 170
# ALPHA         = 0.70

# YEARS = list(range(2016, 2026))

# CITY_POINTS = [
#     ("Pune",               73.8567, 18.5204),
#     ("Pimpri-Chinchwad",   73.7997, 18.6298),
#     ("Lonavala",           73.4070, 18.7557),
#     ("Talegaon",           73.6760, 18.7260),
#     ("Sinhagad Fort",      73.7550, 18.3660),
#     ("Hadapsar",           73.9345, 18.5039),
#     ("Saswad",             74.0316, 18.3438),
# ]

# def _read1(path):
#     with rasterio.open(path) as src:
#         return src.read(1), src.profile

# def _to_mercator_raster(arr, prof):
#     dst_crs = "EPSG:3857"
#     left, bottom, right, top = rasterio.transform.array_bounds(
#         prof["height"], prof["width"], prof["transform"]
#     )
#     dst_tx, w, h = rio_warp.calculate_default_transform(
#         prof["crs"], dst_crs, prof["width"], prof["height"],
#         left=left, bottom=bottom, right=right, top=top
#     )
#     dst = np.full((h, w), NODATA, dtype=np.float32)
#     rio_warp.reproject(
#         source=arr.astype(np.float32),
#         destination=dst,
#         src_transform=prof["transform"],
#         src_crs=prof["crs"],
#         dst_transform=dst_tx,
#         dst_crs=dst_crs,
#         dst_nodata=NODATA,
#         resampling=Resampling.nearest,
#     )
#     return dst, dst_tx

# def _extent(tx, w, h, pad_frac=PADDING_FRAC):
#     left = tx.c; top = tx.f
#     right = left + tx.a * w
#     bottom = top + tx.e * h
#     W, E, S, N = (left, right, bottom, top)
#     # pad
#     dx = (E - W) * pad_frac
#     dy = (N - S) * pad_frac
#     return (W - dx, E + dx, S - dy, N + dy)

# def _fetch_basemap(W, S, E, N, source=BASEMAP):
#     # try a couple zooms
#     for z in (12, 11, 10, 9):
#         try:
#             img, ext = ctx.bounds2img(W, S, E, N, zoom=z, source=source)
#             return img, ext
#         except Exception:
#             continue
#     # last resort
#     return ctx.bounds2img(W, S, E, N, zoom=8, source=source)

# def _annotate_cities(ax, extent):
#     transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
#     W, E, S, N = extent
#     for name, lon, lat in CITY_POINTS:
#         x, y = transformer.transform(lon, lat)
#         if (W <= x <= E) and (S <= y <= N):
#             ax.plot(x, y, marker='o', markersize=3.8, color='black', zorder=12)
#             ax.text(x + 600, y + 600, name, fontsize=9, weight='bold',
#                     color='black', zorder=12,
#                     bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='round,pad=0.2'))

# def _apply_aoi_mask(arr, prof):
#     if not AOI_MASK.exists():
#         return arr
#     m_arr, m_prof = _read1(AOI_MASK)
#     if (m_prof["crs"] != prof["crs"] or
#         m_prof["transform"] != prof["transform"] or
#         m_prof["width"] != prof["width"] or
#         m_prof["height"] != prof["height"]):
#         m_dst = np.zeros_like(arr, dtype=np.float32)
#         rio_warp.reproject(
#             source=m_arr.astype(np.float32),
#             destination=m_dst,
#             src_transform=m_prof["transform"],
#             src_crs=m_prof["crs"],
#             dst_transform=prof["transform"],
#             dst_crs=prof["crs"],
#             dst_nodata=0,
#             resampling=Resampling.nearest,
#         )
#         return np.where(m_dst > 0.5, arr, NODATA)
#     return np.where(m_arr > 0.5, arr, NODATA)

# # ---------- classification strategies ----------
# def compute_global_quantile_edges():
#     """One set of edges for ALL years → maps won’t look identical; differences are real."""
#     samples = []
#     for y in YEARS:
#         p = A_DIR / f"a_factor_{y}.tif"
#         if not p.exists(): 
#             continue
#         a, prof = _read1(p)
#         a = _apply_aoi_mask(a, prof)
#         v = a[np.isfinite(a) & (a != NODATA) & (a >= 0)]
#         if v.size:
#             # subsample to keep memory light
#             if v.size > 800_000:
#                 idx = np.random.choice(v.size, 800_000, replace=False)
#                 v = v[idx]
#             samples.append(v)
#     if not samples:
#         # fallback
#         return np.array([0, 0.1, 0.5, 1.5, 4.0, np.inf])
#     allv = np.concatenate(samples)
#     q = np.quantile(allv, [0.50, 0.75, 0.90, 0.97])  # tune if needed
#     edges = np.array([0.0, *q, float(np.nanmax(allv)) + 1e-6])
#     return edges

# GLOBAL_EDGES = compute_global_quantile_edges()  # 6 edges → 5 classes

# def classify_global(a_m):
#     m = np.isfinite(a_m) & (a_m != NODATA) & (a_m >= 0)
#     classes = np.full(a_m.shape, -1, dtype=np.int16)
#     classes[m] = np.digitize(a_m[m], GLOBAL_EDGES, right=False) - 1
#     labels = [
#         f"{GLOBAL_EDGES[0]:.2f}–{GLOBAL_EDGES[1]:.2f}",
#         f"{GLOBAL_EDGES[1]:.2f}–{GLOBAL_EDGES[2]:.2f}",
#         f"{GLOBAL_EDGES[2]:.2f}–{GLOBAL_EDGES[3]:.2f}",
#         f"{GLOBAL_EDGES[3]:.2f}–{GLOBAL_EDGES[4]:.2f}",
#         f">{GLOBAL_EDGES[4]:.2f}",
#     ]
#     return classes, labels

# def classify_log(a_m):
#     # log-spread mid-range so maps don’t collapse to green
#     bins = np.array([0.0, 0.05, 0.20, 0.80, 3.20, np.inf])
#     m = np.isfinite(a_m) & (a_m != NODATA) & (a_m >= 0)
#     classes = np.full(a_m.shape, -1, dtype=np.int16)
#     classes[m] = np.digitize(a_m[m], bins, right=False) - 1
#     labels = ["<0.05", "0.05–0.20", "0.20–0.80", "0.80–3.20", ">3.20"]
#     return classes, labels

# def render_year(year, mode="global"):  # mode: "global" or "log"
#     a_path = A_DIR / f"a_factor_{year}.tif"
#     if not a_path.exists():
#         print(f"[WARN] missing {a_path}")
#         return

#     a, prof = _read1(a_path)
#     a = _apply_aoi_mask(a, prof)
#     a_m, tx_m = _to_mercator_raster(a, prof)
#     W, E, S, N = _extent(tx_m, a_m.shape[1], a_m.shape[0], pad_frac=PADDING_FRAC)

#     if mode == "log":
#         classes, labels = classify_log(a_m)
#         title_suffix = "(Log-spread bins)"
#     else:
#         classes, labels = classify_global(a_m)
#         title_suffix = "(Global bins: same scale for 2016–2025)"

#     # RGBA overlay
#     rgba = np.zeros((classes.shape[0], classes.shape[1], 4), dtype=np.float32)
#     color_list = [mcolors.to_rgba(c, alpha=ALPHA) for c in PALETTE]
#     for k in range(5):
#         m = (classes == k)
#         if m.any():
#             rgba[m] = color_list[k]

#     # basemap
#     img, ext = _fetch_basemap(W, S, E, N, source=BASEMAP)

#     # AOI outline
#     aoi_gdf = None
#     if AOI_SHP.exists():
#         try:
#             aoi_gdf = gpd.read_file(AOI_SHP)
#             if aoi_gdf.crs is None or aoi_gdf.crs.to_string() != "EPSG:3857":
#                 aoi_gdf = aoi_gdf.to_crs("EPSG:3857")
#         except Exception:
#             aoi_gdf = None

#     fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
#     ax.imshow(img, extent=ext)
#     ax.imshow(rgba, extent=ext, interpolation="nearest")

#     if aoi_gdf is not None and not aoi_gdf.empty:
#         aoi_gdf.boundary.plot(ax=ax, color="white", linewidth=1.3, alpha=0.95, zorder=11)
#         aoi_gdf.boundary.plot(ax=ax, color="black", linewidth=0.7, alpha=0.9, zorder=12)

#     _annotate_cities(ax, ext)

#     handles = [Patch(facecolor=PALETTE[i], edgecolor='black', label=lab) for i, lab in enumerate(labels)]
#     ax.legend(handles=handles, loc="lower left", frameon=True, fontsize=9)
#     ax.set_title(f"Soil Loss (A) — {year}  {title_suffix}", fontsize=13, weight="bold")
#     ax.set_xlim([ext[0], ext[1]]); ax.set_ylim([ext[2], ext[3]])
#     ax.axis("off")
#     fig.tight_layout()

#     out = OUT_DIR / f"soil_loss_on_basemap_{year}.png"
#     fig.savefig(out, bbox_inches="tight", pad_inches=0.15)
#     plt.close(fig)
#     print(f"[OK] {out}")

# def make_all(mode="global"):
#     for y in YEARS:
#         render_year(y, mode=mode)

# if __name__ == "__main__":
#     # Choose one:
#     #   mode="global"  → one scale for all years (recommended for comparison)
#     #   mode="log"     → more mid-range contrast
#     make_all(mode="global")


# scripts/09_make_overlay_maps.py
# Generates A-factor overlay maps for each year (2016–2025)
# + NEW: ALL-YEARS combined overlay map using GLOBAL_EDGES
# Uses Web-Mercator basemap + AOI mask + consistent classification.

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

# -----------------------------------------------------------
# Paths & Config
# -----------------------------------------------------------
BASE = Path(__file__).resolve().parents[1]
A_DIR     = BASE / "temp" / "erosion"
AOI_MASK  = BASE / "temp" / "aoi" / "aoi_mask.tif"
AOI_SHP   = BASE / "catchment" / "Mula_Mutha_Catchment.shp"
OUT_DIR   = BASE / "outputs" / "maps"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PALETTE = ["#006837", "#7CB342", "#FFEB3B", "#FF9800", "#D32F2F"]   # Very Low → Very High
NODATA  = -9999.0
BASEMAP = ctx.providers.Esri.WorldTopoMap

PADDING_FRAC = 0.18
FIGSIZE = (12.5, 9)
DPI     = 170
ALPHA   = 0.70

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

# -----------------------------------------------------------
# Utilities
# -----------------------------------------------------------
def _read1(path):
    with rasterio.open(path) as src:
        return src.read(1), src.profile

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

def _to_mercator_raster(arr, prof):
    dst_crs = "EPSG:3857"
    left, bottom, right, top = rasterio.transform.array_bounds(
        prof["height"], prof["width"], prof["transform"]
    )
    dst_tx, width, height = rio_warp.calculate_default_transform(
        prof["crs"], dst_crs, prof["width"], prof["height"],
        left=left, bottom=bottom, right=right, top=top
    )
    dst = np.full((height, width), NODATA, dtype=np.float32)
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
    W = tx.c
    N = tx.f
    E = W + tx.a * w
    S = N + tx.e * h
    dx = (E - W) * pad_frac
    dy = (N - S) * pad_frac
    return (W - dx, E + dx, S - dy, N + dy)

def _fetch_basemap(W, S, E, N):
    for z in (12, 11, 10, 9):
        try:
            img, ext = ctx.bounds2img(W, S, E, N, zoom=z, source=BASEMAP)
            return img, ext
        except:
            pass
    return ctx.bounds2img(W, S, E, N, zoom=8, source=BASEMAP)

def _annotate_cities(ax, extent):
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    W, E, S, N = extent
    for name, lon, lat in CITY_POINTS:
        x, y = transformer.transform(lon, lat)
        if W <= x <= E and S <= y <= N:
            ax.plot(x, y, "o", markersize=4, color="black", zorder=12)
            ax.text(x+600, y+600, name, fontsize=9, weight="bold",
                    bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"))

# -----------------------------------------------------------
# GLOBAL EDGES (BEST OPTION)
# -----------------------------------------------------------
def compute_global_edges():
    samples = []
    for y in YEARS:
        p = A_DIR / f"a_factor_{y}.tif"
        if not p.exists(): continue
        a, prof = _read1(p)
        a = _apply_aoi_mask(a, prof)
        v = a[(a != NODATA) & np.isfinite(a) & (a >= 0)]
        if v.size > 800_000:  # subsample
            v = v[np.random.choice(v.size, 800_000, replace=False)]
        if v.size:
            samples.append(v)

    if not samples:
        return np.array([0, 0.1, 0.5, 1.5, 4.0, np.inf])

    allv = np.concatenate(samples)
    q = np.quantile(allv, [0.50, 0.75, 0.90, 0.97])
    hi = float(np.nanmax(allv)) + 1e-6
    return np.array([0.0, q[0], q[1], q[2], q[3], hi])

GLOBAL_EDGES = compute_global_edges()  # 6 edges = 5 classes

def classify_global(a_m):
    m = np.isfinite(a_m) & (a_m != NODATA) & (a_m >= 0)
    classes = np.full(a_m.shape, -1, dtype=np.int16)
    classes[m] = np.digitize(a_m[m], GLOBAL_EDGES) - 1
    labels = [
        f"{GLOBAL_EDGES[0]:.2f}–{GLOBAL_EDGES[1]:.2f}",
        f"{GLOBAL_EDGES[1]:.2f}–{GLOBAL_EDGES[2]:.2f}",
        f"{GLOBAL_EDGES[2]:.2f}–{GLOBAL_EDGES[3]:.2f}",
        f"{GLOBAL_EDGES[3]:.2f}–{GLOBAL_EDGES[4]:.2f}",
        f">{GLOBAL_EDGES[4]:.2f}",
    ]
    return classes, labels

# -----------------------------------------------------------
# RENDER ONE YEAR
# -----------------------------------------------------------
def render_year(year):
    path = A_DIR / f"a_factor_{year}.tif"
    if not path.exists():
        print(f"[WARN] Missing {path}")
        return

    a, prof = _read1(path)
    a = _apply_aoi_mask(a, prof)

    a_m, tx = _to_mercator_raster(a, prof)
    W, E, S, N = _extent(tx, a_m.shape[1], a_m.shape[0])

    classes, labels = classify_global(a_m)
    img, ext = _fetch_basemap(W, S, E, N)

    rgba = np.zeros((*classes.shape, 4), dtype=np.float32)
    colors = [mcolors.to_rgba(c, ALPHA) for c in PALETTE]
    for k in range(5):
        mask = (classes == k)
        rgba[mask] = colors[k]

    aoi = None
    if AOI_SHP.exists():
        try:
            aoi = gpd.read_file(AOI_SHP)
            if aoi.crs is None or aoi.crs.to_string() != "EPSG:3857":
                aoi = aoi.to_crs("EPSG:3857")
        except:
            aoi = None

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    ax.imshow(img, extent=ext)
    ax.imshow(rgba, extent=ext, interpolation="nearest")

    if aoi is not None:
        aoi.boundary.plot(ax=ax, color="white", linewidth=1.3, zorder=11)
        aoi.boundary.plot(ax=ax, color="black", linewidth=0.7, zorder=12)

    _annotate_cities(ax, ext)

    legend = [Patch(facecolor=PALETTE[i], edgecolor='black', label=labels[i]) for i in range(5)]
    ax.legend(handles=legend, loc="lower left", fontsize=9)
    ax.set_title(f"Soil Loss (A) — {year}", fontsize=14, weight="bold")
    ax.axis("off")

    out = OUT_DIR / f"soil_loss_on_basemap_{year}.png"
    fig.savefig(out, bbox_inches='tight', pad_inches=0.15)
    plt.close(fig)
    print(f"[OK] {out}")

# -----------------------------------------------------------
# NEW: ALL-YEARS COMBINED MAP
# -----------------------------------------------------------
def render_all_years():
    stack = []
    ref_prof = None

    for y in YEARS:
        p = A_DIR / f"a_factor_{y}.tif"
        if not p.exists(): continue
        a, prof = _read1(p)
        a = _apply_aoi_mask(a, prof)
        stack.append(a.astype(np.float32))
        ref_prof = prof

    if not stack:
        print("[ERR] No rasters found for ALL-YEARS map.")
        return

    arr = np.nanmean(np.stack(stack, axis=0), axis=0)

    a_m, tx = _to_mercator_raster(arr, ref_prof)
    W, E, S, N = _extent(tx, a_m.shape[1], a_m.shape[0])

    classes, labels = classify_global(a_m)
    img, ext = _fetch_basemap(W, S, E, N)

    rgba = np.zeros((*classes.shape, 4), dtype=np.float32)
    colors = [mcolors.to_rgba(c, ALPHA) for c in PALETTE]
    for k in range(5):
        rgba[classes == k] = colors[k]

    aoi = None
    if AOI_SHP.exists():
        try:
            aoi = gpd.read_file(AOI_SHP)
            if aoi.crs is None or aoi.crs.to_string() != "EPSG:3857":
                aoi = aoi.to_crs("EPSG:3857")
        except:
            aoi = None

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    ax.imshow(img, extent=ext)
    ax.imshow(rgba, extent=ext, interpolation="nearest")

    if aoi is not None:
        aoi.boundary.plot(ax=ax, color="white", linewidth=1.3)
        aoi.boundary.plot(ax=ax, color="black", linewidth=0.7)

    _annotate_cities(ax, ext)

    legend = [Patch(facecolor=PALETTE[i], edgecolor='black', label=labels[i]) for i in range(5)]
    ax.legend(handles=legend, loc="lower left", fontsize=9)
    ax.set_title("Soil Loss (A) — ALL YEARS (2016–2025)", fontsize=14, weight="bold")
    ax.axis("off")

    out = OUT_DIR / "soil_loss_on_basemap_ALL_YEARS.png"
    fig.savefig(out, bbox_inches='tight', pad_inches=0.15)
    plt.close(fig)
    print(f"[OK] {out}")

# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
def make_all():
    for y in YEARS:
        render_year(y)
    render_all_years()          # NEW ADDITION

if __name__ == "__main__":
    make_all()
