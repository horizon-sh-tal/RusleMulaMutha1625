#!/usr/bin/env python3
"""
RUSLE K-Factor Calculation Script (2016-2025)
==============================================
Calculate K-Factor (Soil Erodibility) from OpenLandMap soil texture data.

K-Factor is a STATIC factor - calculated once and used for all 10 years (2016-2025).

Data Source:
    - OpenLandMap Soil Texture Classification (USDA)
    - Dataset: OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02
    - Band: b0 (0-30cm depth)
    - Date: 2016-01-01 (static dataset)
    - Resolution: 250m (resampled to 90m for RUSLE)

Output:
    - temp/factors/k_factor.tif (90m resolution)
    - Range: 0.005 - 0.07 (soil erodibility factor)
    - Usage: Same file for ALL years 2016-2025

Author: RUSLE Mula-Mutha Project
Date: November 2025

IMPORTANT: This script is 100% portable
- Works with ANY Google Earth Engine account
- Uses ee.Initialize() without account parameters
- Whoever is authenticated will be used
"""

import sys
from pathlib import Path

# Get project root directory (works anywhere!)
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / 'scripts'))

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
import geopandas as gpd
import ee
import geemap
import matplotlib.pyplot as plt
import logging
from datetime import datetime

# Import configurations
from config import (
    CATCHMENT_SHP, FACTORS_DIR, LOGS_DIR, FIGURES_DIR,
    GEE_SOIL, SOIL_BAND, SOIL_K_VALUES, FACTOR_RANGES,
    TARGET_RESOLUTION, TARGET_CRS, LOG_FORMAT, LOG_DATE_FORMAT
)
from color_config import EROSION_PALETTE, EROSION_CATEGORIES

# Setup logging
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(LOGS_DIR / f"02_k_factor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def initialize_gee():
    """
    Initialize Google Earth Engine.
    
    IMPORTANT: Uses ee.Initialize() WITHOUT account parameters.
    This makes the script work with ANY authenticated GEE account.
    Whoever runs 'earthengine authenticate' will be used.
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("=" * 80)
    logger.info("Initializing Google Earth Engine...")
    logger.info("=" * 80)
    
    try:
        # Initialize WITHOUT account parameters - works with ANY authenticated user!
        ee.Initialize()
        
        logger.info("✅ Google Earth Engine initialized successfully")
        logger.info("   Using authenticated account (whoever ran 'earthengine authenticate')")
        
        # Test connection
        test_image = ee.Image('CGIAR/SRTM90_V4')
        test_info = test_image.getInfo()
        logger.info(f"✅ GEE connection verified: {test_info['type']}")
        
        return True
        
    except Exception as e:
        logger.error("❌ Google Earth Engine initialization failed")
        logger.error(f"   Error: {e}")
        logger.error("")
        logger.error("   SOLUTION:")
        logger.error("   1. Run: earthengine authenticate")
        logger.error("   2. Login with YOUR Google account")
        logger.error("   3. Run this script again")
        logger.error("")
        return False


def load_catchment():
    """
    Load catchment shapefile and get bounds.
    
    Returns:
        tuple: (GeoDataFrame, bounds array) or (None, None) on failure
    """
    logger.info("=" * 80)
    logger.info("Loading catchment shapefile...")
    logger.info("=" * 80)
    
    try:
        # Use Path for portability
        catchment_path = BASE_DIR / CATCHMENT_SHP
        
        if not catchment_path.exists():
            logger.error(f"❌ Catchment file not found: {catchment_path}")
            return None, None
        
        gdf = gpd.read_file(catchment_path)
        
        # Ensure WGS84 (EPSG:4326) for GEE compatibility
        if gdf.crs.to_epsg() != 4326:
            logger.info(f"   Reprojecting from {gdf.crs} to EPSG:4326...")
            gdf = gdf.to_crs(epsg=4326)
        
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        
        logger.info(f"✅ Catchment loaded successfully")
        logger.info(f"   File: {catchment_path}")
        logger.info(f"   CRS: {gdf.crs}")
        logger.info(f"   Features: {len(gdf)}")
        logger.info(f"   Bounds:")
        logger.info(f"      West:  {bounds[0]:.5f}°")
        logger.info(f"      South: {bounds[1]:.5f}°")
        logger.info(f"      East:  {bounds[2]:.5f}°")
        logger.info(f"      North: {bounds[3]:.5f}°")
        
        return gdf, bounds
        
    except Exception as e:
        logger.error(f"❌ Error loading catchment: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None


def download_soil_texture(bounds, output_path):
    """
    Download soil texture data from OpenLandMap via Google Earth Engine.
    
    Args:
        bounds: Bounding box [minx, miny, maxx, maxy]
        output_path: Path to save GeoTIFF
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("=" * 80)
    logger.info("Downloading soil texture data from OpenLandMap...")
    logger.info("=" * 80)
    
    try:
        # Create bounding box geometry
        bbox = ee.Geometry.Rectangle(bounds.tolist())
        
        logger.info(f"   Data source: {GEE_SOIL}")
        logger.info(f"   Band: {SOIL_BAND} (0-30cm depth)")
        logger.info(f"   Target resolution: {TARGET_RESOLUTION}m")
        logger.info(f"   Bounds: {bounds}")
        
        # Load soil texture dataset
        soil_texture = ee.Image(GEE_SOIL).select(SOIL_BAND)
        
        # Clip to catchment bounds
        soil_clipped = soil_texture.clip(bbox)
        
        # Get image info
        soil_info = soil_clipped.getInfo()
        logger.info(f"✅ Image loaded: {soil_info['type']}")
        
        # Download using geemap at target resolution
        logger.info("   Downloading... (this may take a few minutes)")
        
        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        geemap.ee_export_image(
            soil_clipped,
            filename=str(output_path),
            scale=TARGET_RESOLUTION,  # 90m resolution
            region=bbox,
            file_per_band=False
        )
        
        if output_path.exists():
            # Verify download
            with rasterio.open(output_path) as src:
                logger.info(f"✅ Soil texture downloaded successfully")
                logger.info(f"   Output: {output_path}")
                logger.info(f"   Dimensions: {src.width} × {src.height} pixels")
                logger.info(f"   CRS: {src.crs}")
                logger.info(f"   Resolution: {abs(src.res[0]) * 111320:.1f}m × {abs(src.res[1]) * 111320:.1f}m")
                logger.info(f"   Data type: {src.dtypes[0]}")
                logger.info(f"   File size: {output_path.stat().st_size / (1024*1024):.2f} MB")
            
            return True
        else:
            logger.error("❌ Download failed - file not created")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error downloading soil texture: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def reclassify_soil_to_k(soil_texture_array, nodata_value):
    """
    Convert soil texture codes to K-factor values.
    
    Uses USDA soil texture classification system:
    1=Clay, 2=Silty Clay, 3=Silty Clay Loam, 4=Sandy Clay,
    5=Sandy Clay Loam, 6=Clay Loam, 7=Silt Loam, 8=Loam,
    9=Silt, 10=Sandy Loam, 11=Loamy Sand, 12=Sand
    
    Args:
        soil_texture_array: Soil texture classification (1-12)
        nodata_value: NoData value
        
    Returns:
        numpy.ndarray: K-factor values (float32)
    """
    logger.info("=" * 80)
    logger.info("Reclassifying soil texture to K-factor...")
    logger.info("=" * 80)
    
    # Soil texture class names
    texture_names = {
        1: "Clay",
        2: "Silty Clay",
        3: "Silty Clay Loam",
        4: "Sandy Clay",
        5: "Sandy Clay Loam",
        6: "Clay Loam",
        7: "Silt Loam",
        8: "Loam",
        9: "Silt",
        10: "Sandy Loam",
        11: "Loamy Sand",
        12: "Sand"
    }
    
    # Mask NoData
    soil_masked = np.ma.masked_equal(soil_texture_array, nodata_value)
    soil_masked = np.ma.masked_equal(soil_masked, 0)  # 0 = NoData in OpenLandMap
    
    # Initialize K-factor array
    k_factor = np.full_like(soil_texture_array, nodata_value, dtype=np.float32)
    
    # Apply lookup table from config
    logger.info("Applying K-factor lookup table:")
    logger.info("")
    logger.info(f"{'Class':<7} {'Texture Type':<22} {'K-Value':<10} {'Pixels':<15} {'%':<8}")
    logger.info("-" * 70)
    
    class_counts = {}
    total_valid = (~soil_masked.mask).sum()
    
    for soil_code, k_value in sorted(SOIL_K_VALUES.items()):
        mask = soil_texture_array == soil_code
        count = mask.sum()
        
        if count > 0:
            k_factor[mask] = k_value
            class_counts[soil_code] = count
            texture_name = texture_names.get(soil_code, f"Unknown ({soil_code})")
            pct = (count / total_valid) * 100
            logger.info(f"{soil_code:<7} {texture_name:<22} {k_value:<10.4f} {count:<15,} {pct:<8.2f}")
    
    logger.info("-" * 70)
    
    # Calculate statistics
    k_masked = np.ma.masked_equal(k_factor, nodata_value)
    k_valid = k_masked.compressed()
    
    logger.info("")
    logger.info("K-Factor Statistics:")
    logger.info(f"   Min:         {k_valid.min():.4f}")
    logger.info(f"   Max:         {k_valid.max():.4f}")
    logger.info(f"   Mean:        {k_valid.mean():.4f}")
    logger.info(f"   Median:      {np.median(k_valid):.4f}")
    logger.info(f"   Std Dev:     {k_valid.std():.4f}")
    logger.info(f"   Valid pixels: {len(k_valid):,}")
    
    # Validation
    k_min, k_max = FACTOR_RANGES['K']
    
    if k_valid.min() < k_min or k_valid.max() > k_max:
        logger.warning(f"⚠️  K values outside expected range ({k_min}-{k_max})")
        logger.warning(f"    Actual: {k_valid.min():.4f} - {k_valid.max():.4f}")
    else:
        logger.info(f"✅ K values within expected range ({k_min}-{k_max})")
    
    # Check for missing classes
    all_classes = set(range(1, 13))
    found_classes = set(class_counts.keys())
    missing_classes = all_classes - found_classes
    
    if missing_classes:
        logger.info(f"\nℹ️  Soil classes not present in catchment:")
        for soil_code in sorted(missing_classes):
            texture_name = texture_names.get(soil_code, f"Unknown")
            logger.info(f"    Class {soil_code}: {texture_name}")
    
    logger.info("✅ Soil reclassification completed")
    
    return k_factor


def save_k_factor(k_factor_array, profile, output_path):
    """
    Save K-factor raster to GeoTIFF.
    
    Args:
        k_factor_array: K-factor values
        profile: Rasterio profile (metadata)
        output_path: Output file path
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("=" * 80)
    logger.info("Saving K-factor raster...")
    logger.info("=" * 80)
    
    try:
        # Update profile for K-factor
        profile.update({
            'dtype': 'float32',
            'nodata': -9999,
            'compress': 'lzw'
        })
        
        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save raster
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(k_factor_array.astype('float32'), 1)
        
        logger.info(f"✅ K-factor saved successfully")
        logger.info(f"   Output: {output_path}")
        logger.info(f"   File size: {output_path.stat().st_size / (1024*1024):.2f} MB")
        
        # Verify
        with rasterio.open(output_path) as src:
            logger.info(f"   Dimensions: {src.width} × {src.height} pixels")
            logger.info(f"   CRS: {src.crs}")
            logger.info(f"   NoData: {src.nodata}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving K-factor: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def create_visualization(k_factor_path, output_path):
    """
    Create K-factor visualization.
    
    Args:
        k_factor_path: Path to K-factor GeoTIFF
        output_path: Path to save visualization
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("=" * 80)
    logger.info("Creating K-factor visualization...")
    logger.info("=" * 80)
    
    try:
        # Load K-factor
        with rasterio.open(k_factor_path) as src:
            k_data = src.read(1)
            k_data_masked = np.ma.masked_equal(k_data, src.nodata)
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
        
        # K-factor map
        im1 = ax1.imshow(k_data_masked, cmap='YlOrRd', vmin=0.005, vmax=0.07)
        ax1.set_title('K-Factor (Soil Erodibility)\nMula-Mutha Catchment',
                     fontsize=14, fontweight='bold')
        ax1.set_xlabel('Longitude (pixels)', fontsize=11)
        ax1.set_ylabel('Latitude (pixels)', fontsize=11)
        cbar1 = plt.colorbar(im1, ax=ax1, orientation='vertical', pad=0.02)
        cbar1.set_label('K-Factor (t·ha·h/ha·MJ·mm)', fontsize=11)
        ax1.grid(True, alpha=0.3, linestyle='--')
        
        # Histogram
        k_valid = k_data_masked.compressed()
        ax2.hist(k_valid.flatten(), bins=30, color='coral', edgecolor='black', alpha=0.7)
        ax2.set_title('K-Factor Distribution', fontsize=14, fontweight='bold')
        ax2.set_xlabel('K-Factor', fontsize=11)
        ax2.set_ylabel('Frequency (pixels)', fontsize=11)
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.axvline(k_valid.mean(), color='red', linestyle='--', linewidth=2,
                   label=f'Mean: {k_valid.mean():.4f}')
        ax2.axvline(np.median(k_valid), color='green', linestyle='--', linewidth=2,
                   label=f'Median: {np.median(k_valid):.4f}')
        ax2.legend(fontsize=10)
        
        # Add statistics
        stats_text = f"""K-Factor Statistics:
Min:    {k_valid.min():.4f}
Max:    {k_valid.max():.4f}
Mean:   {k_valid.mean():.4f}
Median: {np.median(k_valid):.4f}
Std:    {k_valid.std():.4f}

Source: OpenLandMap
Date: 2016-01-01
Usage: Static (all years)"""
        
        ax2.text(0.98, 0.97, stats_text, transform=ax2.transAxes,
                fontsize=9, verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"✅ Visualization saved: {output_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating visualization: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Main execution function."""
    start_time = datetime.now()
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("RUSLE K-FACTOR CALCULATION (2016-2025)")
    logger.info("=" * 80)
    logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Project directory: {BASE_DIR}")
    logger.info("")
    
    # Step 1: Initialize GEE
    if not initialize_gee():
        logger.error("❌ Cannot proceed without GEE initialization")
        return False
    
    # Step 2: Load catchment
    gdf, bounds = load_catchment()
    if gdf is None:
        logger.error("❌ Cannot proceed without catchment data")
        return False
    
    # Step 3: Download soil texture
    soil_texture_path = FACTORS_DIR / "soil_texture_raw.tif"
    
    if not download_soil_texture(bounds, soil_texture_path):
        logger.error("❌ Failed to download soil texture")
        return False
    
    # Step 4: Load soil texture
    logger.info("=" * 80)
    logger.info("Loading soil texture raster...")
    logger.info("=" * 80)
    
    with rasterio.open(soil_texture_path) as src:
        soil_data = src.read(1)
        profile = src.profile.copy()
        nodata = src.nodata if src.nodata is not None else -9999
        
        logger.info(f"✅ Soil texture loaded")
        logger.info(f"   Dimensions: {src.width} × {src.height} pixels")
        logger.info(f"   NoData: {nodata}")
    
    # Step 5: Reclassify to K-factor
    k_factor = reclassify_soil_to_k(soil_data, nodata)
    
    # Step 6: Save K-factor
    k_factor_path = FACTORS_DIR / "k_factor.tif"
    
    if not save_k_factor(k_factor, profile, k_factor_path):
        logger.error("❌ Failed to save K-factor")
        return False
    
    # Step 7: Create visualization
    viz_path = FIGURES_DIR / "k_factor_map.png"
    
    if not create_visualization(k_factor_path, viz_path):
        logger.warning("⚠️  Visualization failed (K-factor still saved)")
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("K-FACTOR CALCULATION COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)
    logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    logger.info("")
    logger.info("Output files:")
    logger.info(f"   K-Factor:      {k_factor_path}")
    logger.info(f"   Visualization: {viz_path}")
    logger.info("")
    logger.info("Next step: Run 03_calculate_ls_factor.py")
    logger.info("=" * 80)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
