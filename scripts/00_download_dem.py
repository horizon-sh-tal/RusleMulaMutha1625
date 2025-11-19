#!/usr/bin/env python3
"""
Download SRTM 90m DEM from Google Earth Engine
For RUSLE Analysis - Mula-Mutha Catchment (2016-2025)

Author: Bhavya Singh
Date: 19 November 2025
"""

import sys
import logging
from pathlib import Path
import geopandas as gpd
import ee
import geemap

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent))
from config import *

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "00_download_dem.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def download_srtm_dem():
    """
    Download SRTM 90m DEM from Google Earth Engine
    
    Returns:
        bool: True if successful
    """
    try:
        logger.info("="*80)
        logger.info("STEP 0: DOWNLOAD SRTM 90m DEM FROM GOOGLE EARTH ENGINE")
        logger.info("="*80)
        
        # Initialize Google Earth Engine
        logger.info("\n[PROCESS] Initializing Google Earth Engine...")
        try:
            # Try with project ID first
            try:
                ee.Initialize(project='rusle-477405')
                logger.info("   [OK] Google Earth Engine initialized with project")
            except:
                # Fallback to default initialization
                ee.Initialize()
                logger.info("   [OK] Google Earth Engine initialized")
        except Exception as e:
            logger.error(f"   [ERROR] Failed to initialize GEE: {e}")
            logger.error("   Please run: earthengine authenticate")
            return False
        
        # Load catchment boundary
        logger.info("\n[PROCESS] Loading catchment boundary...")
        if not CATCHMENT_SHP.exists():
            logger.error(f"   [ERROR] Catchment shapefile not found: {CATCHMENT_SHP}")
            return False
        
        catchment_gdf = gpd.read_file(CATCHMENT_SHP)
        logger.info(f"   [OK] Loaded catchment: {catchment_gdf.shape[0]} feature(s)")
        logger.info(f"   [OK] CRS: {catchment_gdf.crs}")
        
        # Ensure WGS84 projection
        if catchment_gdf.crs != "EPSG:4326":
            logger.info("   [PROCESS] Reprojecting to EPSG:4326...")
            catchment_gdf = catchment_gdf.to_crs("EPSG:4326")
        
        # Get bounding box
        bounds = catchment_gdf.total_bounds  # [minx, miny, maxx, maxy]
        bbox = ee.Geometry.Rectangle([bounds[0], bounds[1], bounds[2], bounds[3]])
        logger.info(f"   [OK] Bounding Box: {bounds}")
        
        # Load SRTM DEM from Google Earth Engine
        logger.info(f"\n[PROCESS] Loading SRTM DEM from GEE: {DEM_GEE_ASSET}")
        srtm = ee.Image(DEM_GEE_ASSET)
        
        # Clip to catchment area
        logger.info("   [PROCESS] Clipping DEM to catchment area...")
        dem_clipped = srtm.clip(bbox)
        
        # Download DEM
        logger.info(f"\n[PROCESS] Downloading DEM to: {DEM_FILE}")
        logger.info("   [WARNING] This may take 2-5 minutes depending on network speed...")
        
        try:
            geemap.ee_export_image(
                dem_clipped,
                filename=str(DEM_FILE),
                scale=90,  # 90m resolution
                region=bbox,
                file_per_band=False
            )
            logger.info("   [OK] DEM downloaded successfully!")
        except Exception as e:
            logger.error(f"   [ERROR] Download failed: {e}")
            return False
        
        # Validate downloaded DEM
        logger.info("\n[PROCESS] Validating downloaded DEM...")
        if not DEM_FILE.exists():
            logger.error("   [ERROR] DEM file not created!")
            return False
        
        file_size_mb = DEM_FILE.stat().st_size / (1024 * 1024)
        logger.info(f"   [OK] DEM file size: {file_size_mb:.2f} MB")
        
        # Read and check DEM values
        import rasterio
        with rasterio.open(DEM_FILE) as src:
            dem_array = src.read(1)
            logger.info(f"   [OK] DEM shape: {dem_array.shape}")
            logger.info(f"   [OK] DEM resolution: {src.res}")
            logger.info(f"   [OK] DEM CRS: {src.crs}")
            logger.info(f"   [OK] Elevation range: {dem_array.min():.1f} to {dem_array.max():.1f} meters")
            logger.info(f"   [OK] Mean elevation: {dem_array.mean():.1f} meters")
        
        # Check if elevation values are reasonable
        if dem_array.min() < -500 or dem_array.max() > 10000:
            logger.warning("   [WARNING] Elevation values may be unrealistic!")
        else:
            logger.info("   [OK] Elevation values look reasonable")
        
        logger.info("\n" + "="*80)
        logger.info("[OK] SRTM DEM DOWNLOAD COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
        logger.info(f"DEM saved to: {DEM_FILE}")
        logger.info(f"Ready for LS-Factor calculation")
        logger.info("="*80 + "\n")
        
        return True
        
    except Exception as e:
        logger.error(f"\n[ERROR] DEM download failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Main execution function"""
    logger.info("\n" + "="*80)
    logger.info("RUSLE ANALYSIS - SRTM DEM DOWNLOAD")
    logger.info("Mula-Mutha Catchment, Pune (2016-2025)")
    logger.info("="*80 + "\n")
    
    success = download_srtm_dem()
    
    if success:
        logger.info("\n[OK] Script completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n[ERROR] Script failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
