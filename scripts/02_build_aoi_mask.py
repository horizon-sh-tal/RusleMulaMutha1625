#!/usr/bin/env python
"""
Build AOI mask aligned to the DEM grid
- Input vector: catchment/Mula_Mutha_Catchment.shp
- Reference raster: temp/dem_srtm_90m.tif (EPSG:4326)
- Output mask: temp/aoi/aoi_mask.tif (uint8: 1=AOI, 0=outside, nodata=0)
"""

from pathlib import Path
import sys
import logging
from datetime import datetime

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import rasterize

BASE_DIR = Path(__file__).resolve().parents[1]
SHAPE_PATH = BASE_DIR / "catchment" / "Mula_Mutha_Catchment.shp"
DEM_PATH   = BASE_DIR / "temp" / "dem_srtm_90m.tif"
AOI_DIR    = BASE_DIR / "temp" / "aoi"
AOI_PATH   = AOI_DIR / "aoi_mask.tif"

LOG = logging.getLogger("build_aoi_mask")
LOG.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
fh = logging.FileHandler(BASE_DIR / "outputs" / "logs" / f"build_aoi_mask_{datetime.now():%Y%m%d_%H%M%S}.log", encoding="utf-8")
for h in (ch, fh):
    h.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    LOG.addHandler(h)

def main():
    LOG.info("=== AOI MASK BUILDER ===")
    if not SHAPE_PATH.exists():
        LOG.error(f"Shapefile not found: {SHAPE_PATH}")
        return 1
    if not DEM_PATH.exists():
        LOG.error(f"DEM not found: {DEM_PATH}")
        return 1

    AOI_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "outputs" / "logs").mkdir(parents=True, exist_ok=True)

    # Load DEM as reference grid
    with rasterio.open(DEM_PATH) as dem:
        dem_crs = dem.crs
        dem_transform = dem.transform
        dem_height, dem_width = dem.height, dem.width
        dem_profile = dem.profile

    LOG.info(f"DEM grid -> CRS={dem_crs}, shape=({dem_height},{dem_width})")

    # Load and reproject shapefile to DEM CRS
    gdf = gpd.read_file(SHAPE_PATH)
    LOG.info(f"Loaded shapefile with {len(gdf)} feature(s); source CRS={gdf.crs}")
    if gdf.crs is None:
        LOG.warning("Shapefile has no CRS; assuming EPSG:4326.")
        gdf = gdf.set_crs("EPSG:4326")
    if gdf.crs != dem_crs:
        gdf = gdf.to_crs(dem_crs)
        LOG.info(f"Reprojected AOI to DEM CRS: {dem_crs}")

    # Build shapes for rasterize (handle multi-geometries)
    shapes = [(geom, 1) for geom in gdf.geometry if geom and not geom.is_empty]
    if not shapes:
        LOG.error("No valid geometries found in shapefile.")
        return 1

    # Rasterize onto DEM grid
    mask = rasterize(
        shapes=shapes,
        out_shape=(dem_height, dem_width),
        transform=dem_transform,
        fill=0,
        default_value=1,
        dtype="uint8",
        all_touched=False,  # set True if you want a “fatter” mask
    )

    inside = int(mask.sum())
    total = int(mask.size)
    coverage = 100.0 * inside / total
    LOG.info(f"AOI coverage: {inside}/{total} pixels ({coverage:.2f}%)")

    # Save mask (uint8, nodata=0)
    out_profile = dem_profile.copy()
    out_profile.update({
        "driver": "GTiff",
        "count": 1,
        "dtype": "uint8",
        "nodata": 0,
        "compress": "lzw",
        "tiled": True,
    })
    with rasterio.open(AOI_PATH, "w", **out_profile) as dst:
        dst.write(mask, 1)

    LOG.info(f"Saved AOI mask: {AOI_PATH}")
    LOG.info("Done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
