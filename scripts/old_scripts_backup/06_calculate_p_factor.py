"""
Step 6: Calculate P Factor (Support Practice Factor)
Derives conservation practice factor from slope and land cover

Author: Bhavya Singh
Date: 17 November 2025

P-factor represents the effect of conservation practices on erosion.
Based on slope and land cover type (cropland vs others)
"""

import sys
sys.path.append('/home/ubuntuksh/Desktop/RUSLE/scripts')

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
import geopandas as gpd
import ee
import geemap
import matplotlib.pyplot as plt
import pandas as pd
import logging
from pathlib import Path
from config import *

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(LOGS_DIR / "06_p_factor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def initialize_gee():
    """Initialize Google Earth Engine."""
    logger.info("Initializing Google Earth Engine...")
    try:
        ee.Initialize(project='rusle-477405')
        logger.info("[OK] Google Earth Engine initialized")
        return True
    except Exception as e:
        logger.error(f"[ERROR] GEE initialization failed: {e}")
        return False


def download_landcover(year, catchment_bounds, output_path):
    """
    Download land cover from Dynamic World.
    
    Args:
        year: Year (2014-2024)
        catchment_bounds: Bounding box
        output_path: Output path
        
    Returns:
        bool: Success
    """
    logger.info(f"Downloading land cover for {year}...")
    
    try:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        bbox = ee.Geometry.Rectangle(catchment_bounds.tolist())
        
        if year >= 2015:
            # Dynamic World available from mid-2015
            logger.info(f"   - Using Dynamic World")
            
            dw = ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1") \
                .filterDate(start_date, end_date) \
                .filterBounds(bbox)
            
            count = dw.size().getInfo()
            logger.info(f"   - Images available: {count}")
            
            if count == 0:
                logger.error(f"   [ERROR] No Dynamic World data for {year}")
                return False
            
            # Get mode (most common class) for the year
            landcover = dw.select('label').mode()
            
        else:
            # For 2014, use ESA WorldCover or proxy with 2015
            logger.warning(f"   [WARNING]  Dynamic World not available for {year}")
            logger.info(f"   Using 2015 land cover as proxy")
            return False
        
        landcover = landcover.clip(bbox)
        
        # Download at target resolution (90m) to avoid size limit
        logger.info(f"   - Downloading...")
        
        geemap.ee_export_image(
            landcover,
            filename=str(output_path),
            scale=90,  # Use target resolution
            region=bbox,
            file_per_band=False
        )
        
        if output_path.exists():
            logger.info(f"   [OK] Downloaded: {year}")
            return True
        else:
            logger.error(f"   [ERROR] Download failed")
            return False
            
    except Exception as e:
        logger.error(f"   [ERROR] Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def calculate_p_factor(slope_pct, landcover, nodata_value):
    """
    Calculate P-factor based on slope and land cover.
    
    P-factor logic:
    - Cropland (class 4):
      * slope < 5%: P = 0.10 (well terraced)
      * 5-10%: P = 0.30 (some terracing)
      * 10-20%: P = 0.50 (minimal conservation)
      * >20%: P = 1.00 (no conservation)
    - Other land: P = 1.00 (no artificial conservation)
    
    Args:
        slope_pct: Slope percentage array
        landcover: Land cover classification
        nodata_value: NoData value
        
    Returns:
        numpy.ndarray: P-factor
    """
    logger.info("Calculating P-factor from slope and land cover...")
    
    # Mask NoData
    slope_masked = np.ma.masked_equal(slope_pct, nodata_value)
    lc_masked = np.ma.masked_equal(landcover, nodata_value)
    
    # Initialize P-factor array (default = 1.0)
    p_factor = np.ones_like(slope_pct, dtype=np.float32)
    
    # Dynamic World classes:
    # 0: Water, 1: Trees, 2: Grass, 3: Flooded veg, 4: Crops,
    # 5: Shrub, 6: Built, 7: Bare, 8: Snow/ice
    
    # Apply P-factor for cropland only
    cropland_mask = (landcover == 4)
    
    if cropland_mask.sum() > 0:
        logger.info(f"   - Cropland pixels: {cropland_mask.sum():,}")
        
        # Slope-based P for cropland
        crop_flat = cropland_mask & (slope_pct < 5)
        crop_gentle = cropland_mask & (slope_pct >= 5) & (slope_pct < 10)
        crop_moderate = cropland_mask & (slope_pct >= 10) & (slope_pct < 20)
        crop_steep = cropland_mask & (slope_pct >= 20)
        
        p_factor[crop_flat] = 0.10
        p_factor[crop_gentle] = 0.30
        p_factor[crop_moderate] = 0.50
        p_factor[crop_steep] = 1.00
        
        logger.info(f"      - Flat (<5%): {crop_flat.sum():,} pixels -> P=0.10")
        logger.info(f"      - Gentle (5-10%): {crop_gentle.sum():,} pixels -> P=0.30")
        logger.info(f"      - Moderate (10-20%): {crop_moderate.sum():,} pixels -> P=0.50")
        logger.info(f"      - Steep (>20%): {crop_steep.sum():,} pixels -> P=1.00")
    else:
        logger.warning("   [WARNING]  No cropland detected - all P=1.0")
    
    # Mask NoData areas
    p_factor[slope_masked.mask | lc_masked.mask] = nodata_value
    
    # Statistics
    p_valid = np.ma.masked_equal(p_factor, nodata_value).compressed()
    
    logger.info(f"\n   P-factor Statistics:")
    logger.info(f"   - Range: {p_valid.min():.2f} - {p_valid.max():.2f}")
    logger.info(f"   - Mean: {p_valid.mean():.3f}")
    logger.info(f"   - Median: {np.median(p_valid):.3f}")
    
    # Distribution
    unique, counts = np.unique(p_valid, return_counts=True)
    logger.info(f"\n   P-factor Distribution:")
    for val, count in zip(unique, counts):
        pct = (count / len(p_valid)) * 100
        logger.info(f"      P={val:.2f}: {count:,} pixels ({pct:.1f}%)")
    
    # Validation
    p_min, p_max = FACTOR_RANGES['P']
    if p_valid.min() >= p_min and p_valid.max() <= p_max:
        logger.info(f"   [OK] P-factor within expected range ({p_min}-{p_max})")
    else:
        logger.warning(f"   [WARNING]  P-factor outside range ({p_min}-{p_max})")
    
    return p_factor


def resample_p_to_target(p_factor_path, reference_dem_path, output_path):
    """Resample P-factor to target resolution."""
    logger.info("   Resampling P-factor to 90m...")
    
    try:
        with rasterio.open(reference_dem_path) as ref:
            ref_transform = ref.transform
            ref_width = ref.width
            ref_height = ref.height
            ref_crs = ref.crs
        
        with rasterio.open(p_factor_path) as src:
            p_data = src.read(1)
            src_nodata = src.nodata if src.nodata is not None else NODATA_VALUE
            
            p_resampled = np.empty((ref_height, ref_width), dtype=np.float32)
            
            reproject(
                source=p_data,
                destination=p_resampled,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=ref_transform,
                dst_crs=ref_crs,
                src_nodata=src_nodata,
                dst_nodata=NODATA_VALUE,
                resampling=Resampling.nearest
            )
            
            meta = src.meta.copy()
            meta.update({
                'crs': ref_crs,
                'transform': ref_transform,
                'width': ref_width,
                'height': ref_height,
                'dtype': 'float32',
                'nodata': NODATA_VALUE
            })
            
            with rasterio.open(output_path, 'w', **meta) as dst:
                dst.write(p_resampled, 1)
            
            logger.info(f"   [OK] Resampled to 90m")
            return True
            
    except Exception as e:
        logger.error(f"   [ERROR] Resampling failed: {e}")
        return False


def main(start_year=None, end_year=None):
    """Main execution function."""
    start_year = start_year or START_YEAR
    end_year = end_year or END_YEAR
    years = list(range(start_year, end_year + 1))
    
    logger.info("="*80)
    logger.info("STEP 6: SUPPORT PRACTICE (P) FACTOR CALCULATION")
    logger.info("="*80)
    logger.info(f"Years: {start_year}-{end_year} ({len(years)} years)")
    
    try:
        if not initialize_gee():
            return False
        
        catchment = gpd.read_file(TEMP_DIR / "catchment_validated.geojson")
        bounds = catchment.total_bounds
        dem_path = TEMP_DIR / "dem_processed.tif"
        
        # Load slope (calculated in step 2)
        slope_path = FACTORS_DIR / "slope_percentage.tif"
        if not slope_path.exists():
            logger.error(f"[ERROR] Slope not found: {slope_path}")
            logger.error("   Run 02_calculate_ls_factor.py first!")
            return False
        
        with rasterio.open(slope_path) as src:
            slope_pct = src.read(1)
            slope_meta = src.meta.copy()
        
        p_stats = []
        
        for year in years:
            logger.info("="*80)
            logger.info(f"Processing year: {year}")
            logger.info("="*80)
            
            lc_raw_path = TEMP_DIR / f"landcover_{year}_raw.tif"
            
            # Handle 2014
            if year == 2014:
                if not lc_raw_path.exists():
                    lc_2015_path = TEMP_DIR / "landcover_2015_raw.tif"
                    if lc_2015_path.exists():
                        import shutil
                        logger.info("   Using 2015 land cover for 2014")
                        shutil.copy(lc_2015_path, lc_raw_path)
                    else:
                        if not download_landcover(year, bounds, lc_raw_path):
                            logger.warning("   [WARNING]  Using default P=1.0 for all pixels")
                            p_factor = np.ones_like(slope_pct)
                            p_factor[slope_pct == NODATA_VALUE] = NODATA_VALUE
                            
                            p_final_path = FACTORS_DIR / f"p_factor_{year}.tif"
                            with rasterio.open(p_final_path, 'w', **slope_meta) as dst:
                                dst.write(p_factor, 1)
                            continue
            else:
                if not lc_raw_path.exists():
                    if not download_landcover(year, bounds, lc_raw_path):
                        continue
            
            # Load land cover and calculate P
            with rasterio.open(lc_raw_path) as src:
                landcover = src.read(1)
                lc_meta = src.meta.copy()
            
            # Ensure landcover matches slope dimensions
            if landcover.shape != slope_pct.shape:
                logger.info("   Resampling land cover to match slope...")
                lc_resampled = np.empty_like(slope_pct)
                lc_nodata = lc_meta.get('nodata', NODATA_VALUE)
                
                reproject(
                    source=landcover,
                    destination=lc_resampled,
                    src_transform=lc_meta['transform'],
                    src_crs=lc_meta['crs'],
                    dst_transform=slope_meta['transform'],
                    dst_crs=slope_meta['crs'],
                    src_nodata=lc_nodata,
                    dst_nodata=NODATA_VALUE,
                    resampling=Resampling.nearest
                )
                landcover = lc_resampled
            
            p_factor = calculate_p_factor(slope_pct, landcover, NODATA_VALUE)
            
            # Save P-factor
            p_final_path = FACTORS_DIR / f"p_factor_{year}.tif"
            with rasterio.open(p_final_path, 'w', **slope_meta) as dst:
                dst.write(p_factor, 1)
            
            p_valid = np.ma.masked_equal(p_factor, NODATA_VALUE).compressed()
            p_stats.append({
                'year': year,
                'p_min': p_valid.min(),
                'p_max': p_valid.max(),
                'p_mean': p_valid.mean(),
                'p_median': np.median(p_valid)
            })
            
            logger.info(f"[OK] Year {year} completed")
        
        if len(p_stats) > 0:
            stats_df = pd.DataFrame(p_stats)
            stats_path = STATS_DIR / "p_factor_annual_statistics.csv"
            stats_df.to_csv(stats_path, index=False)
            logger.info(f"[SAVED] Statistics saved: {stats_path}")
        
        logger.info("="*80)
        logger.info("[OK] P-FACTOR CALCULATION COMPLETED!")
        logger.info("="*80)
        
        return len(p_stats) == len(years)
        
    except Exception as e:
        logger.error(f"[ERROR] P-FACTOR CALCULATION FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-year', type=int, default=START_YEAR)
    parser.add_argument('--end-year', type=int, default=END_YEAR)
    args = parser.parse_args()
    
    success = main(args.start_year, args.end_year)
    sys.exit(0 if success else 1)
