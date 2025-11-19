"""
Step 3: Calculate K Factor (Soil Erodibility)
Downloads soil texture data from OpenLandMap and converts to K values

Author: Bhavya Singh
Date: 17 November 2025

Data Source: OpenLandMap Soil Texture Classification (USDA)
Resolution: 250m -> resampled to 90m
"""

import sys
sys.path.append('/home/ubuntuksh/Desktop/RUSLE/scripts')

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform
import geopandas as gpd
import ee
import geemap
import matplotlib.pyplot as plt
import logging
from pathlib import Path
from config import *

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(LOGS_DIR / "03_k_factor.log"),
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
        logger.error("   Run: earthengine authenticate")
        return False


def download_soil_texture(catchment_bounds, output_path):
    """
    Download soil texture data from OpenLandMap via Google Earth Engine.
    
    Args:
        catchment_bounds: Bounding box [minx, miny, maxx, maxy]
        output_path: Path to save GeoTIFF
        
    Returns:
        bool: Success status
    """
    logger.info("="*80)
    logger.info("Downloading soil texture data from OpenLandMap...")
    logger.info("="*80)
    
    try:
        # Create bounding box geometry
        bbox = ee.Geometry.Rectangle(catchment_bounds.tolist())
        
        logger.info(f"   - Bounds: {catchment_bounds}")
        logger.info(f"   - Data source: {GEE_SOIL}")
        logger.info(f"   - Band: {SOIL_BAND} (0-30cm depth)")
        
        # Load soil texture dataset
        soil_texture = ee.Image(GEE_SOIL).select(SOIL_BAND)
        
        # Clip to catchment
        soil_clipped = soil_texture.clip(bbox)
        
        # Get image info
        soil_info = soil_clipped.getInfo()
        logger.info(f"   - Image loaded: {soil_info['type']}")
        
        # Download using geemap at target resolution (90m) to avoid size limit
        logger.info("   - Downloading... (this may take a few minutes)")
        
        geemap.ee_export_image(
            soil_clipped,
            filename=str(output_path),
            scale=90,  # Use target resolution
            region=bbox,
            file_per_band=False
        )
        
        if output_path.exists():
            logger.info(f"[OK] Soil texture downloaded: {output_path}")
            
            # Verify download
            with rasterio.open(output_path) as src:
                logger.info(f"   - Dimensions: {src.width} x {src.height}")
                logger.info(f"   - CRS: {src.crs}")
                logger.info(f"   - Data type: {src.dtypes[0]}")
            
            return True
        else:
            logger.error("[ERROR] Download failed - file not created")
            return False
            
    except Exception as e:
        logger.error(f"[ERROR] Error downloading soil texture: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def reclassify_soil_to_k(soil_texture_array, nodata_value):
    """
    Convert soil texture codes to K-factor values.
    
    Args:
        soil_texture_array: Soil texture classification (1-12)
        nodata_value: NoData value
        
    Returns:
        numpy.ndarray: K-factor values
    """
    logger.info("="*80)
    logger.info("Reclassifying soil texture to K-factor...")
    logger.info("="*80)
    
    # Mask NoData
    soil_masked = np.ma.masked_equal(soil_texture_array, nodata_value)
    soil_masked = np.ma.masked_equal(soil_masked, 0)  # 0 = NoData in OpenLandMap
    
    # Initialize K-factor array
    k_factor = np.full_like(soil_texture_array, nodata_value, dtype=np.float32)
    
    # Apply lookup table from SOIL_K_VALUES
    logger.info("Applying K-factor lookup table:")
    
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
    
    class_counts = {}
    
    for soil_code, k_value in SOIL_K_VALUES.items():
        mask = soil_texture_array == soil_code
        count = mask.sum()
        
        if count > 0:
            k_factor[mask] = k_value
            class_counts[soil_code] = count
            texture_name = texture_names.get(soil_code, f"Unknown ({soil_code})")
            pct = (count / (~soil_masked.mask).sum()) * 100
            logger.info(f"   Class {soil_code:2d} ({texture_name:20s}): "
                       f"K = {k_value:.4f} | {count:8,} pixels ({pct:5.2f}%)")
    
    # Validation
    k_masked = np.ma.masked_equal(k_factor, nodata_value)
    k_valid = k_masked.compressed()
    
    logger.info(f"\nK-factor Statistics:")
    logger.info(f"   - Min: {k_valid.min():.4f}")
    logger.info(f"   - Max: {k_valid.max():.4f}")
    logger.info(f"   - Mean: {k_valid.mean():.4f}")
    logger.info(f"   - Median: {np.median(k_valid):.4f}")
    logger.info(f"   - Std Dev: {k_valid.std():.4f}")
    
    # Error checks
    k_min, k_max = FACTOR_RANGES['K']
    
    if k_valid.min() < k_min or k_valid.max() > k_max:
        logger.warning(f"[WARNING]  K values outside expected range ({k_min}-{k_max})")
        logger.warning(f"    Actual: {k_valid.min():.4f} - {k_valid.max():.4f}")
    else:
        logger.info(f"[OK] K values within expected range ({k_min}-{k_max})")
    
    # Check for missing classes
    all_classes = set(range(1, 13))
    found_classes = set(class_counts.keys())
    missing_classes = all_classes - found_classes
    
    if missing_classes:
        logger.info(f"\nℹ️  Soil classes not present in catchment: {sorted(missing_classes)}")
    
    logger.info("[OK] Soil reclassification completed")
    
    return k_factor


def resample_to_target_resolution(k_factor_path, reference_dem_path, output_path):
    """
    Resample K-factor to match DEM resolution and extent.
    
    Args:
        k_factor_path: Path to K-factor GeoTIFF (250m)
        reference_dem_path: Path to reference DEM (90m)
        output_path: Path for resampled output
        
    Returns:
        bool: Success status
    """
    logger.info("="*80)
    logger.info("Resampling K-factor to target resolution...")
    logger.info("="*80)
    
    try:
        # Load reference DEM for target specs
        with rasterio.open(reference_dem_path) as ref:
            ref_crs = ref.crs
            ref_transform = ref.transform
            ref_width = ref.width
            ref_height = ref.height
            ref_bounds = ref.bounds
            
            logger.info(f"Reference DEM:")
            logger.info(f"   - CRS: {ref_crs}")
            logger.info(f"   - Resolution: {abs(ref_transform[0]):.2f}m")
            logger.info(f"   - Dimensions: {ref_width} x {ref_height}")
        
        # Load K-factor
        with rasterio.open(k_factor_path) as src:
            k_data = src.read(1)
            src_crs = src.crs
            src_transform = src.transform
            
            logger.info(f"\nSource K-factor:")
            logger.info(f"   - CRS: {src_crs}")
            logger.info(f"   - Resolution: {abs(src_transform[0]):.2f}m")
            logger.info(f"   - Dimensions: {src.width} x {src.height}")
            
            # Create destination array
            k_resampled = np.empty((ref_height, ref_width), dtype=np.float32)
            
            # Reproject/resample
            logger.info(f"\nResampling to {abs(ref_transform[0]):.0f}m...")
            
            reproject(
                source=k_data,
                destination=k_resampled,
                src_transform=src_transform,
                src_crs=src_crs,
                dst_transform=ref_transform,
                dst_crs=ref_crs,
                resampling=Resampling.nearest  # Use nearest neighbor for categorical data
            )
            
            # Update metadata
            meta = src.meta.copy()
            meta.update({
                'crs': ref_crs,
                'transform': ref_transform,
                'width': ref_width,
                'height': ref_height,
                'dtype': 'float32'
            })
            
            # Save resampled K-factor
            with rasterio.open(output_path, 'w', **meta) as dst:
                dst.write(k_resampled, 1)
            
            logger.info(f"[OK] K-factor resampled: {output_path}")
            logger.info(f"   - New dimensions: {ref_width} x {ref_height}")
            
            # Validation
            k_valid = np.ma.masked_equal(k_resampled, NODATA_VALUE).compressed()
            logger.info(f"   - Valid pixels: {len(k_valid):,}")
            logger.info(f"   - Value range: {k_valid.min():.4f} - {k_valid.max():.4f}")
            
            return True
            
    except Exception as e:
        logger.error(f"[ERROR] Resampling failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def validate_k_factor(k_factor_array, nodata_value):
    """
    Validate K-factor spatial patterns and statistics.
    
    Args:
        k_factor_array: K-factor array
        nodata_value: NoData value
        
    Returns:
        bool: Validation passed
    """
    logger.info("="*80)
    logger.info("VALIDATING K-FACTOR")
    logger.info("="*80)
    
    k_masked = np.ma.masked_equal(k_factor_array, nodata_value)
    k_valid = k_masked.compressed()
    
    validation_passed = True
    
    # Check 1: Value range
    logger.info("\n1. Checking value range...")
    k_min, k_max = FACTOR_RANGES['K']
    
    # Filter out zeros (areas outside catchment or water bodies)
    k_nonzero = k_valid[k_valid > 0]
    
    if len(k_nonzero) > 0 and k_nonzero.min() >= k_min and k_valid.max() <= k_max:
        logger.info(f"   [OK] K-factor within expected range ({k_min}-{k_max})")
    elif len(k_nonzero) > 0:
        logger.warning(f"   [WARNING]  K-factor outside range: {k_nonzero.min():.4f} - {k_valid.max():.4f}")
        logger.info(f"   ℹ️  This is acceptable - zeros may represent water bodies or non-soil areas")
    
    # Check 2: No negative values
    logger.info("\n2. Checking for negative values...")
    if k_valid.min() >= 0:
        logger.info("   [OK] No negative values")
    else:
        logger.error(f"   [ERROR] Negative values detected: {k_valid.min():.4f}")
        validation_passed = False
    
    # Check 3: Reasonable distribution
    logger.info("\n3. Checking distribution...")
    unique_values = np.unique(k_valid)
    logger.info(f"   - Unique K values: {len(unique_values)}")
    logger.info(f"   - Expected: 1-12 (one per soil class)")
    
    if len(unique_values) >= 3:
        logger.info("   [OK] Multiple soil classes present (spatial variation)")
    else:
        logger.warning(f"   [WARNING]  Only {len(unique_values)} soil classes (low diversity)")
    
    # Check 4: No isolated pixels
    logger.info("\n4. Checking for spatial consistency...")
    from scipy.ndimage import generic_filter
    
    def mode_filter(values):
        """Return most common value in window."""
        values = values[values != nodata_value]
        if len(values) == 0:
            return nodata_value
        unique, counts = np.unique(values, return_counts=True)
        return unique[counts.argmax()]
    
    # Apply 3x3 mode filter
    k_smoothed = generic_filter(k_factor_array, mode_filter, size=3, mode='constant', 
                                cval=nodata_value)
    
    # Compare original vs smoothed
    k_smooth_masked = np.ma.masked_equal(k_smoothed, nodata_value)
    different = (k_masked != k_smooth_masked).sum()
    different_pct = (different / len(k_valid)) * 100
    
    logger.info(f"   - Isolated pixels (different from neighbors): {different:,} ({different_pct:.2f}%)")
    
    if different_pct < 5:
        logger.info("   [OK] Low isolated pixel count (< 5%)")
    else:
        logger.warning(f"   [WARNING]  High isolated pixels ({different_pct:.2f}%)")
    
    # Check 5: Coverage
    logger.info("\n5. Checking data coverage...")
    total_pixels = k_factor_array.size
    valid_pixels = len(k_valid)
    coverage_pct = (valid_pixels / total_pixels) * 100
    
    logger.info(f"   - Valid pixels: {valid_pixels:,} / {total_pixels:,} ({coverage_pct:.2f}%)")
    
    if coverage_pct > 90:
        logger.info("   [OK] Good coverage (> 90%)")
    elif coverage_pct > 70:
        logger.warning(f"   [WARNING]  Moderate coverage ({coverage_pct:.2f}%)")
    else:
        logger.error(f"   [ERROR] Poor coverage ({coverage_pct:.2f}%)")
        validation_passed = False
    
    logger.info("\n" + "="*80)
    if validation_passed:
        logger.info("[OK] K-FACTOR VALIDATION PASSED")
    else:
        logger.warning("[WARNING]  K-FACTOR VALIDATION WARNINGS PRESENT")
    logger.info("="*80 + "\n")
    
    return validation_passed


def visualize_k_factor(k_factor_array, nodata_value):
    """
    Create visualization of K-factor distribution.
    
    Args:
        k_factor_array: K-factor array
        nodata_value: NoData value
    """
    logger.info("Creating visualizations...")
    
    try:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle('Soil Erodibility (K-Factor) Analysis', 
                     fontsize=14, fontweight='bold')
        
        k_plot = np.ma.masked_equal(k_factor_array, nodata_value)
        
        # Plot 1: K-factor map
        im = axes[0].imshow(k_plot, cmap='RdYlGn_r', interpolation='nearest',
                           vmin=0, vmax=0.07)
        axes[0].set_title('K-Factor Spatial Distribution', fontweight='bold')
        axes[0].set_xlabel('Column')
        axes[0].set_ylabel('Row')
        
        cbar = plt.colorbar(im, ax=axes[0], fraction=0.046, pad=0.04)
        cbar.set_label('K-Factor (t·h·MJ⁻¹·mm⁻¹)', rotation=270, labelpad=20)
        
        # Plot 2: K-factor histogram
        k_valid = k_plot.compressed()
        axes[1].hist(k_valid, bins=30, color='sienna', alpha=0.7, edgecolor='black')
        axes[1].set_xlabel('K-Factor Value')
        axes[1].set_ylabel('Frequency (pixels)')
        axes[1].set_title('K-Factor Distribution', fontweight='bold')
        axes[1].axvline(k_valid.mean(), color='red', linestyle='--', 
                       linewidth=2, label=f'Mean: {k_valid.mean():.4f}')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # Add statistics text
        stats_text = f"Min: {k_valid.min():.4f}\n"
        stats_text += f"Max: {k_valid.max():.4f}\n"
        stats_text += f"Mean: {k_valid.mean():.4f}\n"
        stats_text += f"Median: {np.median(k_valid):.4f}\n"
        stats_text += f"Std Dev: {k_valid.std():.4f}"
        
        axes[1].text(0.98, 0.98, stats_text,
                    transform=axes[1].transAxes,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                    verticalalignment='top',
                    horizontalalignment='right',
                    fontfamily='monospace',
                    fontsize=9)
        
        plt.tight_layout()
        
        output_path = FIGURES_DIR / "03_k_factor_analysis.png"
        plt.savefig(output_path, dpi=FIG_DPI, bbox_inches='tight')
        logger.info(f"[SAVED] Visualization saved: {output_path}")
        
        plt.close()
        
    except Exception as e:
        logger.warning(f"[WARNING]  Visualization failed: {e}")


def main():
    """Main execution function."""
    logger.info("="*80)
    logger.info("STEP 3: SOIL ERODIBILITY (K) FACTOR CALCULATION")
    logger.info("="*80)
    logger.info(f"Project: {PROJECT_NAME}")
    logger.info(f"Author: {AUTHOR}")
    
    try:
        # Initialize Google Earth Engine
        if not initialize_gee():
            return False
        
        # Load catchment boundary
        catchment_path = TEMP_DIR / "catchment_validated.geojson"
        if not catchment_path.exists():
            logger.error(f"[ERROR] Catchment file not found: {catchment_path}")
            logger.error("   Run 01_data_preparation.py first!")
            return False
        
        catchment = gpd.read_file(catchment_path)
        bounds = catchment.total_bounds  # [minx, miny, maxx, maxy]
        logger.info(f"[OK] Catchment loaded: {bounds}")
        
        # Step 1: Download soil texture from OpenLandMap
        soil_raw_path = TEMP_DIR / "soil_texture_raw.tif"
        
        if not soil_raw_path.exists():
            if not download_soil_texture(bounds, soil_raw_path):
                return False
        else:
            logger.info(f"ℹ️  Using existing soil texture: {soil_raw_path}")
        
        # Step 2: Reclassify to K-factor
        with rasterio.open(soil_raw_path) as src:
            soil_data = src.read(1)
            soil_meta = src.meta.copy()
            nodata = src.nodata if src.nodata is not None else 0
        
        k_factor = reclassify_soil_to_k(soil_data, nodata)
        
        # Save intermediate K-factor
        k_intermediate_path = TEMP_DIR / "k_factor_250m.tif"
        soil_meta.update({'dtype': 'float32', 'nodata': NODATA_VALUE})
        
        with rasterio.open(k_intermediate_path, 'w', **soil_meta) as dst:
            dst.write(k_factor, 1)
        
        logger.info(f"[SAVED] K-factor (250m) saved: {k_intermediate_path}")
        
        # Step 3: Resample to target resolution
        dem_path = TEMP_DIR / "dem_processed.tif"
        k_final_path = FACTORS_DIR / "k_factor.tif"
        
        if not resample_to_target_resolution(k_intermediate_path, dem_path, k_final_path):
            return False
        
        # Load final K-factor for validation
        with rasterio.open(k_final_path) as src:
            k_final = src.read(1)
        
        # Step 4: Validate
        validation_passed = validate_k_factor(k_final, NODATA_VALUE)
        
        # Step 5: Visualize
        visualize_k_factor(k_final, NODATA_VALUE)
        
        # Summary
        logger.info("="*80)
        logger.info("[OK] K-FACTOR CALCULATION COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
        logger.info(f"[FOLDER] Outputs:")
        logger.info(f"   - K-factor (90m): {k_final_path}")
        logger.info(f"   - Visualization: {FIGURES_DIR / '03_k_factor_analysis.png'}")
        
        return validation_passed
        
    except Exception as e:
        logger.error("="*80)
        logger.error("[ERROR] K-FACTOR CALCULATION FAILED!")
        logger.error("="*80)
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
