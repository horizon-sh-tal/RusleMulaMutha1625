"""
Step 5: Calculate C Factor (Cover Management)
Downloads Sentinel-2 NDVI from Dynamic World and calculates vegetation cover factor

Author: Bhavya Singh
Date: 17 November 2025

Formula: C = exp(-2 × NDVI / (1 - NDVI))
Then normalized to 0-1 range

Data Source: Google Dynamic World v1 (Sentinel-2 based)
Temporal Range: 2015-2024 (Note: 2014 uses Landsat 8 or 2015 proxy)
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
import time
from pathlib import Path
from config import *

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(LOGS_DIR / "05_c_factor.log"),
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


def download_annual_ndvi(year, catchment_bounds, output_path):
    """
    Download annual mean NDVI from Sentinel-2 (Dynamic World) or Landsat 8.
    
    Args:
        year: Year (2014-2024)
        catchment_bounds: Bounding box
        output_path: Output path
        
    Returns:
        bool: Success
    """
    logger.info(f"Downloading NDVI for {year}...")
    
    try:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        bbox = ee.Geometry.Rectangle(catchment_bounds.tolist())
        
        # Use Landsat 8 for 2014-2015 (Sentinel-2 has limited coverage in 2015)
        # Sentinel-2 from 2016 onwards (better temporal coverage)
        if year >= 2016:
            logger.info(f"   - Using Sentinel-2 (Dynamic World)")
            
            # Cloud masking function for Sentinel-2
            def mask_s2_clouds(image):
                qa = image.select('QA60')
                # Bits 10 and 11 are clouds and cirrus
                cloud_bit_mask = 1 << 10
                cirrus_bit_mask = 1 << 11
                mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(
                    qa.bitwiseAnd(cirrus_bit_mask).eq(0))
                return image.updateMask(mask)
            
            # Use Sentinel-2 Level-2A for atmospherically corrected data
            s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
                .filterDate(start_date, end_date) \
                .filterBounds(bbox) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)) \
                .map(mask_s2_clouds)
            
            count = s2.size().getInfo()
            logger.info(f"   - Images available: {count}")
            
            if count == 0:
                logger.error(f"   [ERROR] No Sentinel-2 data for {year}")
                return False
            
            # Calculate NDVI: (NIR - Red) / (NIR + Red)
            def calculate_ndvi(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                # Mask out unrealistic NDVI values
                ndvi = ndvi.updateMask(ndvi.gte(-0.2).And(ndvi.lte(1.0)))
                return ndvi
            
            ndvi_collection = s2.map(calculate_ndvi)
            annual_ndvi = ndvi_collection.median()  # Use median to reduce cloud impact
            
        else:  # 2014-2015 - use Landsat 8 for consistent quality
            logger.info(f"   - Using Landsat 8 (better temporal coverage)")
            
            # Cloud masking function for Landsat 8
            def mask_l8_clouds(image):
                qa = image.select('QA_PIXEL')
                # Bit 3: Cloud, Bit 4: Cloud Shadow
                cloud_mask = qa.bitwiseAnd(1 << 3).eq(0)
                shadow_mask = qa.bitwiseAnd(1 << 4).eq(0)
                mask = cloud_mask.And(shadow_mask)
                return image.updateMask(mask)
            
            l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2") \
                .filterDate(start_date, end_date) \
                .filterBounds(bbox) \
                .filter(ee.Filter.lt('CLOUD_COVER', 30)) \
                .map(mask_l8_clouds)
            
            count = l8.size().getInfo()
            logger.info(f"   - Images available: {count}")
            
            if count == 0:
                logger.warning(f"   [WARNING] No Landsat 8 data for {year}")
                logger.warning(f"   Using 2016 NDVI as proxy")
                return False
            
            # Landsat 8: Band 5 = NIR, Band 4 = Red
            def calculate_ndvi_l8(image):
                ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
                # Apply scaling factor and mask unrealistic values
                ndvi = ndvi.updateMask(ndvi.gte(-0.2).And(ndvi.lte(1.0)))
                return ndvi
            
            ndvi_collection = l8.map(calculate_ndvi_l8)
            annual_ndvi = ndvi_collection.median()
        
        # Clip to catchment
        annual_ndvi = annual_ndvi.clip(bbox)
        
        # Download with retry logic for network issues
        logger.info(f"   - Downloading...")
        
        max_retries = 3
        retry_delay = 10  # seconds
        
        for attempt in range(max_retries):
            try:
                # Download at target resolution (90m) to avoid size limit
                geemap.ee_export_image(
                    annual_ndvi,
                    filename=str(output_path),
                    scale=90,  # Use target resolution to reduce file size
                    region=bbox,
                    file_per_band=False
                )
                break  # Success, exit retry loop
                
            except (KeyboardInterrupt, SystemExit):
                raise  # Don't retry on user interrupt
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"   [WARNING] Download attempt {attempt + 1} failed: {str(e)}")
                    logger.warning(f"   [RETRY] Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"   [ERROR] Download failed after {max_retries} attempts")
                    raise
        
        if output_path.exists():
            with rasterio.open(output_path) as src:
                data = src.read(1)
                # Strict NDVI validation: -0.2 to 1.0 (healthy range)
                valid = data[(data != src.nodata) & (data >= -0.2) & (data <= 1.0)] if src.nodata else data
                
                if len(valid) == 0:
                    logger.error(f"   [ERROR] No valid NDVI data for {year}")
                    return False
                
                # Check data quality
                mean_ndvi = valid.mean()
                if mean_ndvi < -0.1 or mean_ndvi > 0.95:
                    logger.warning(f"   [WARNING] Suspicious NDVI mean: {mean_ndvi:.3f}")
                    logger.warning(f"   [WARNING] Data quality may be poor for {year}")
                
                logger.info(f"   [OK] Downloaded: {year}")
                logger.info(f"      - NDVI range: {valid.min():.3f} - {valid.max():.3f}")
                logger.info(f"      - Mean NDVI: {mean_ndvi:.3f}")
                logger.info(f"      - Valid pixels: {len(valid):,}")
            
            return True
        else:
            logger.error(f"   [ERROR] Download failed for {year}")
            return False
            
    except Exception as e:
        logger.error(f"   [ERROR] Error downloading {year}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def calculate_c_factor(ndvi_array, nodata_value):
    """
    Calculate C-factor from NDVI.
    
    Formula: C = exp(-2 × NDVI / (1 - NDVI))
    Then normalize to 0-1 range
    
    Args:
        ndvi_array: NDVI values (-1 to 1)
        nodata_value: NoData value
        
    Returns:
        numpy.ndarray: C-factor (0-1)
    """
    logger.info("Calculating C-factor from NDVI...")
    
    # Mask NoData and invalid NDVI
    ndvi_masked = np.ma.masked_equal(ndvi_array, nodata_value)
    ndvi_masked = np.ma.masked_outside(ndvi_masked, NDVI_MIN, NDVI_MAX)
    
    # Apply C-factor formula
    # Add small epsilon to avoid division by zero
    epsilon = 1e-6
    c_factor = np.exp(-2 * ndvi_masked / (1 - ndvi_masked + epsilon))
    
    # Normalize to 0-1 range
    c_valid = c_factor.compressed()
    c_min = c_valid.min()
    c_max = c_valid.max()
    
    c_normalized = (c_factor - c_min) / (c_max - c_min + epsilon)
    
    # Validation
    c_norm_valid = c_normalized.compressed()
    
    logger.info(f"   - C-factor range: {c_norm_valid.min():.4f} - {c_norm_valid.max():.4f}")
    logger.info(f"   - Mean C: {c_norm_valid.mean():.4f}")
    logger.info(f"   - Median C: {np.median(c_norm_valid):.4f}")
    
    # Check relationship: High NDVI -> Low C
    high_ndvi = ndvi_masked > 0.6
    if high_ndvi.sum() > 0:
        high_ndvi_c = c_normalized[high_ndvi].compressed()
        logger.info(f"   - C-factor for high NDVI (>0.6): mean = {high_ndvi_c.mean():.4f}")
        if high_ndvi_c.mean() < 0.3:
            logger.info("   [OK] High vegetation -> Low C (expected)")
        else:
            logger.warning(f"   [WARNING] High vegetation has high C ({high_ndvi_c.mean():.4f})")
    
    low_ndvi = ndvi_masked < 0.2
    if low_ndvi.sum() > 0:
        low_ndvi_c = c_normalized[low_ndvi].compressed()
        logger.info(f"   - C-factor for low NDVI (<0.2): mean = {low_ndvi_c.mean():.4f}")
        if low_ndvi_c.mean() > 0.5:
            logger.info("   [OK] Bare soil -> High C (expected)")
        else:
            logger.warning(f"   [WARNING] Bare soil has low C ({low_ndvi_c.mean():.4f})")
    
    return c_normalized.filled(nodata_value)


def resample_c_to_target(c_factor_path, reference_dem_path, output_path):
    """
    Resample C-factor to target 90m resolution.
    
    Args:
        c_factor_path: Source C-factor path
        reference_dem_path: Reference DEM path
        output_path: Output path
        
    Returns:
        bool: Success
    """
    logger.info("   Resampling C-factor to 90m...")
    
    try:
        with rasterio.open(reference_dem_path) as ref:
            ref_transform = ref.transform
            ref_width = ref.width
            ref_height = ref.height
            ref_crs = ref.crs
        
        with rasterio.open(c_factor_path) as src:
            c_data = src.read(1)
            src_transform = src.transform
            src_crs = src.crs
            src_nodata = src.nodata if src.nodata is not None else NODATA_VALUE
            
            c_resampled = np.empty((ref_height, ref_width), dtype=np.float32)
            
            reproject(
                source=c_data,
                destination=c_resampled,
                src_transform=src_transform,
                src_crs=src_crs,
                dst_transform=ref_transform,
                dst_crs=ref_crs,
                src_nodata=src_nodata,
                dst_nodata=NODATA_VALUE,
                resampling=Resampling.bilinear
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
                dst.write(c_resampled, 1)
            
            logger.info(f"   [OK] Resampled to 90m")
            return True
            
    except Exception as e:
        logger.error(f"   [ERROR] Resampling failed: {e}")
        return False


def visualize_c_factors(c_factors_dict, years):
    """
    Create visualizations of C-factors over time.
    
    Args:
        c_factors_dict: Dictionary {year: c_factor_array}
        years: List of years
    """
    logger.info("Creating C-factor visualizations...")
    
    try:
        # Multi-year panel
        n_years = len(years)
        ncols = 4
        nrows = int(np.ceil(n_years / ncols))
        
        fig, axes = plt.subplots(nrows, ncols, figsize=(20, 5*nrows))
        fig.suptitle('Cover Management Factor (C-Factor) - Annual Maps (2014-2024)', 
                     fontsize=16, fontweight='bold', y=0.999)
        
        axes = axes.flatten() if n_years > 1 else [axes]
        
        for idx, year in enumerate(years):
            c_array = c_factors_dict[year]
            c_plot = np.ma.masked_equal(c_array, NODATA_VALUE)
            
            im = axes[idx].imshow(c_plot, cmap='RdYlGn_r', interpolation='bilinear',
                                 vmin=0, vmax=1)
            axes[idx].set_title(f'{year}', fontweight='bold', fontsize=12)
            axes[idx].axis('off')
            
            cbar = plt.colorbar(im, ax=axes[idx], fraction=0.046, pad=0.04)
            cbar.set_label('C', rotation=0, labelpad=10, fontsize=9)
        
        for idx in range(len(years), len(axes)):
            axes[idx].axis('off')
        
        plt.tight_layout()
        
        output_path = FIGURES_DIR / "05_c_factor_temporal.png"
        plt.savefig(output_path, dpi=200, bbox_inches='tight')
        logger.info(f"[SAVED] Temporal visualization saved: {output_path}")
        
        plt.close()
        
        # Trend plot
        fig, ax = plt.subplots(figsize=(12, 6))
        
        years_list = sorted(years)
        means = [np.ma.masked_equal(c_factors_dict[y], NODATA_VALUE).mean() for y in years_list]
        
        ax.plot(years_list, means, marker='o', linewidth=2, markersize=8, color='green')
        ax.fill_between(years_list, 0, means, alpha=0.3, color='green')
        
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Mean C-Factor', fontsize=12, fontweight='bold')
        ax.set_title('Vegetation Cover Temporal Trend (2014-2024)', 
                    fontsize=14, fontweight='bold')
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        trend_path = FIGURES_DIR / "05_c_factor_trend.png"
        plt.savefig(trend_path, dpi=FIG_DPI, bbox_inches='tight')
        logger.info(f"[SAVED] Trend plot saved: {trend_path}")
        
        plt.close()
        
    except Exception as e:
        logger.warning(f"[WARNING] Visualization failed: {e}")


def main(start_year=None, end_year=None):
    """Main execution function."""
    start_year = start_year or START_YEAR
    end_year = end_year or END_YEAR
    years = list(range(start_year, end_year + 1))
    
    logger.info("="*80)
    logger.info("STEP 5: COVER MANAGEMENT (C) FACTOR CALCULATION")
    logger.info("="*80)
    logger.info(f"Years: {start_year}-{end_year} ({len(years)} years)")
    
    try:
        if not initialize_gee():
            return False
        
        catchment = gpd.read_file(TEMP_DIR / "catchment_validated.geojson")
        bounds = catchment.total_bounds
        dem_path = TEMP_DIR / "dem_processed.tif"
        
        c_factors = {}
        c_stats = []
        
        for year in years:
            logger.info("="*80)
            logger.info(f"Processing year: {year}")
            logger.info("="*80)
            
            ndvi_raw_path = TEMP_DIR / f"ndvi_{year}_raw.tif"
            
            # Handle 2014 separately (use 2015 as proxy if needed)
            if year == 2014:
                if not ndvi_raw_path.exists():
                    if not download_annual_ndvi(year, bounds, ndvi_raw_path):
                        logger.warning(f"Using 2015 NDVI for 2014")
                        ndvi_2015_path = TEMP_DIR / "ndvi_2015_raw.tif"
                        if ndvi_2015_path.exists():
                            import shutil
                            shutil.copy(ndvi_2015_path, ndvi_raw_path)
                        else:
                            logger.error("2015 NDVI not available - process 2015 first")
                            continue
            else:
                if not ndvi_raw_path.exists():
                    if not download_annual_ndvi(year, bounds, ndvi_raw_path):
                        continue
            
            # Calculate C-factor
            with rasterio.open(ndvi_raw_path) as src:
                ndvi = src.read(1)
                nodata = src.nodata if src.nodata is not None else NODATA_VALUE
                
                c_factor = calculate_c_factor(ndvi, nodata)
                
                c_raw_path = TEMP_DIR / f"c_factor_{year}_raw.tif"
                meta = src.meta.copy()
                meta.update({'dtype': 'float32', 'nodata': NODATA_VALUE})
                
                with rasterio.open(c_raw_path, 'w', **meta) as dst:
                    dst.write(c_factor, 1)
            
            # Resample
            c_final_path = FACTORS_DIR / f"c_factor_{year}.tif"
            if not resample_c_to_target(c_raw_path, dem_path, c_final_path):
                continue
            
            with rasterio.open(c_final_path) as src:
                c_factors[year] = src.read(1)
            
            c_valid = np.ma.masked_equal(c_factors[year], NODATA_VALUE).compressed()
            c_stats.append({
                'year': year,
                'c_min': c_valid.min(),
                'c_max': c_valid.max(),
                'c_mean': c_valid.mean(),
                'c_median': np.median(c_valid),
                'c_std': c_valid.std()
            })
            
            logger.info(f"[COMPLETE] Year {year} completed")
        
        if len(c_factors) > 0:
            stats_df = pd.DataFrame(c_stats)
            stats_path = STATS_DIR / "c_factor_annual_statistics.csv"
            stats_df.to_csv(stats_path, index=False)
            logger.info(f"[SAVED] Statistics saved: {stats_path}")
            
            visualize_c_factors(c_factors, years)
        
        logger.info("="*80)
        logger.info("[SUCCESS] C-FACTOR CALCULATION COMPLETED!")
        logger.info("="*80)
        
        return len(c_factors) == len(years)
        
    except Exception as e:
        logger.error(f"[FAILED] C-FACTOR CALCULATION FAILED: {e}")
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
