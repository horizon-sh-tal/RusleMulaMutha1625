"""
Step 1: Data Preparation and Validation
Loads catchment boundary and DEM, performs validation checks

Author: Bhavya Singh
Date: 17 November 2025
"""

import sys
sys.path.append('/home/ubuntuksh/Desktop/RUSLE/scripts')

import geopandas as gpd
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging
from config import *

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(LOGS_DIR / "01_data_prep.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_catchment_boundary():
    """
    Load and validate catchment shapefile.
    
    Returns:
        geopandas.GeoDataFrame: Catchment boundary
    """
    logger.info("="*80)
    logger.info("STEP 1.1: Loading Catchment Boundary")
    logger.info("="*80)
    
    try:
        # Load shapefile
        catchment = gpd.read_file(CATCHMENT_SHP)
        logger.info(f"[OK] Catchment shapefile loaded: {CATCHMENT_SHP}")
        
        # Validation checks
        logger.info(f"[CHART] Catchment Info:")
        logger.info(f"   - CRS: {catchment.crs}")
        logger.info(f"   - Number of features: {len(catchment)}")
        logger.info(f"   - Geometry type: {catchment.geometry.type.unique()}")
        
        # Calculate area
        catchment_wgs84 = catchment.to_crs("EPSG:4326")
        catchment_utm = catchment.to_crs("EPSG:32643")  # UTM Zone 43N for Pune
        area_km2 = catchment_utm.geometry.area.sum() / 1e6
        logger.info(f"   - Total area: {area_km2:.2f} km²")
        
        # Bounds
        bounds = catchment_wgs84.total_bounds
        logger.info(f"   - Bounds (WGS84):")
        logger.info(f"     * West: {bounds[0]:.4f}°")
        logger.info(f"     * South: {bounds[1]:.4f}°")
        logger.info(f"     * East: {bounds[2]:.4f}°")
        logger.info(f"     * North: {bounds[3]:.4f}°")
        
        # Validation
        assert len(catchment) > 0, "Catchment has no features!"
        assert catchment.geometry.is_valid.all(), "Invalid geometries detected!"
        assert area_km2 > 5000 and area_km2 < 7000, f"Unexpected area: {area_km2} km²"
        
        logger.info("[OK] Catchment validation passed!")
        
        # Reproject to target CRS if needed
        if catchment.crs != TARGET_CRS:
            logger.info(f"[PROCESS] Reprojecting to {TARGET_CRS}...")
            catchment = catchment.to_crs(TARGET_CRS)
        
        # Save validated catchment
        output_path = TEMP_DIR / "catchment_validated.geojson"
        catchment.to_file(output_path, driver="GeoJSON")
        logger.info(f"[SAVED] Validated catchment saved: {output_path}")
        
        return catchment
        
    except Exception as e:
        logger.error(f"[ERROR] Error loading catchment: {e}")
        raise


def load_and_validate_dem(catchment):
    """
    Load DEM, validate, clip to catchment, and resample.
    
    Args:
        catchment: GeoDataFrame with catchment boundary
        
    Returns:
        tuple: (dem_array, dem_transform, dem_crs, dem_meta)
    """
    logger.info("="*80)
    logger.info("STEP 1.2: Loading and Validating DEM")
    logger.info("="*80)
    
    try:
        # Try primary DEM first
        dem_path = DEM_FILE
        if not dem_path.exists():
            logger.warning(f"Primary DEM not found: {dem_path}")
            dem_path = DEM_BACKUP
            logger.info(f"Using backup DEM: {dem_path}")
        
        # Load DEM
        with rasterio.open(dem_path) as src:
            logger.info(f"[OK] DEM loaded: {dem_path}")
            logger.info(f"[CHART] DEM Info:")
            logger.info(f"   - CRS: {src.crs}")
            logger.info(f"   - Resolution: {src.res[0]:.2f} x {src.res[1]:.2f} meters")
            logger.info(f"   - Dimensions: {src.width} x {src.height} pixels")
            logger.info(f"   - Bands: {src.count}")
            logger.info(f"   - Data type: {src.dtypes[0]}")
            logger.info(f"   - NoData value: {src.nodata}")
            
            # Read full DEM
            dem = src.read(1)
            dem_meta = src.meta.copy()
            
            # Basic statistics
            valid_mask = dem != src.nodata if src.nodata else np.ones_like(dem, dtype=bool)
            valid_dem = dem[valid_mask]
            
            logger.info(f"   - Elevation range: {valid_dem.min():.1f} - {valid_dem.max():.1f} meters")
            logger.info(f"   - Mean elevation: {valid_dem.mean():.1f} meters")
            logger.info(f"   - Valid pixels: {valid_mask.sum():,} / {dem.size:,}")
            
            # Validation checks
            if valid_dem.min() < 0:
                logger.warning(f"   [WARNING]  Negative elevations detected (min: {valid_dem.min():.1f}m) - may be water bodies")
                # Set negative values to 0 (water level)
                dem[dem < 0] = 0
                logger.info("   [OK] Negative values set to 0m (sea level)")
            
            assert valid_dem.max() < 3000, f"Unrealistic elevation: {valid_dem.max()}m"
            assert valid_mask.sum() > 0.5 * dem.size, "Too many NoData pixels!"
            
            logger.info("[OK] DEM validation passed!")
            
            # Clip to catchment
            logger.info("[PROCESS] Clipping DEM to catchment boundary...")
            catchment_reproj = catchment.to_crs(src.crs)
            
            clipped_dem, clipped_transform = mask(
                src, 
                catchment_reproj.geometry, 
                crop=True,
                nodata=NODATA_VALUE
            )
            clipped_dem = clipped_dem[0]
            
            logger.info(f"[OK] DEM clipped to catchment")
            logger.info(f"   - New dimensions: {clipped_dem.shape}")
            
            # Update metadata
            dem_meta.update({
                "driver": "GTiff",
                "height": clipped_dem.shape[0],
                "width": clipped_dem.shape[1],
                "transform": clipped_transform,
                "nodata": NODATA_VALUE
            })
        
        # Resample to target resolution if needed
        current_res = abs(clipped_transform[0])  # Resolution in degrees (WGS84)
        logger.info(f"Current resolution: {current_res:.6f}°, Target: {TARGET_RESOLUTION}m")
        
        # For WGS84, convert 90m to degrees (approximate: 1° ≈ 111.32km at equator)
        target_res_deg = TARGET_RESOLUTION / 111320  # Convert meters to degrees
        
        if abs(current_res - target_res_deg) / target_res_deg > 0.1:  # More than 10% difference
            logger.info(f"[PROCESS] Resampling DEM to target resolution (~{target_res_deg:.6f}°)...")
            
            # Calculate new dimensions
            scale_factor = current_res / target_res_deg
            new_height = int(clipped_dem.shape[0] * scale_factor)
            new_width = int(clipped_dem.shape[1] * scale_factor)
            
            logger.info(f"   Scale factor: {scale_factor:.2f}")
            logger.info(f"   Target dimensions: {new_height} x {new_width}")
            
            if new_height <= 0 or new_width <= 0:
                logger.error(f"   [ERROR] Invalid dimensions calculated")
                raise ValueError("Resampling produced invalid dimensions")
            
            # Create new transform
            new_transform = rasterio.Affine(
                target_res_deg, clipped_transform[1], clipped_transform[2],
                clipped_transform[3], -target_res_deg, clipped_transform[5]
            )
            
            # Resample with proper NoData handling
            resampled_dem = np.empty((new_height, new_width), dtype=clipped_dem.dtype)
            
            reproject(
                source=clipped_dem,
                destination=resampled_dem,
                src_transform=clipped_transform,
                src_crs=dem_meta['crs'],
                dst_transform=new_transform,
                dst_crs=dem_meta['crs'],
                src_nodata=NODATA_VALUE,
                dst_nodata=NODATA_VALUE,
                resampling=Resampling.bilinear
            )
            
            clipped_dem = resampled_dem
            clipped_transform = new_transform
            
            dem_meta.update({
                "height": new_height,
                "width": new_width,
                "transform": new_transform
            })
            
            logger.info(f"[OK] DEM resampled to ~{TARGET_RESOLUTION}m")
        else:
            logger.info("[OK] DEM already at target resolution")
        
        # Save processed DEM
        output_path = TEMP_DIR / "dem_processed.tif"
        
        # Ensure NoData is properly set in metadata
        dem_meta.update({
            'nodata': NODATA_VALUE,
            'dtype': 'float32'
        })
        
        with rasterio.open(output_path, 'w', **dem_meta) as dst:
            dst.write(clipped_dem, 1)
        
        logger.info(f"[SAVED] Processed DEM saved: {output_path}")
        
        return clipped_dem, clipped_transform, dem_meta['crs'], dem_meta
        
    except Exception as e:
        logger.error(f"[ERROR] Error processing DEM: {e}")
        raise


def visualize_data(catchment, dem, dem_transform):
    """
    Create visualization of catchment and DEM.
    
    Args:
        catchment: GeoDataFrame with catchment boundary
        dem: DEM array
        dem_transform: Affine transform
    """
    logger.info("="*80)
    logger.info("STEP 1.3: Creating Visualizations")
    logger.info("="*80)
    
    try:
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        
        # Plot 1: Catchment boundary
        catchment.plot(ax=axes[0], facecolor='lightblue', edgecolor='darkblue', linewidth=2)
        axes[0].set_title('Mula-Mutha Catchment Boundary', fontsize=14, fontweight='bold')
        axes[0].set_xlabel('Longitude (°E)')
        axes[0].set_ylabel('Latitude (°N)')
        axes[0].grid(True, alpha=0.3)
        
        # Plot 2: DEM
        from rasterio.plot import show
        dem_plot = np.ma.masked_equal(dem, NODATA_VALUE)
        im = axes[1].imshow(dem_plot, cmap='terrain', interpolation='bilinear')
        axes[1].set_title('Digital Elevation Model (DEM)', fontsize=14, fontweight='bold')
        axes[1].set_xlabel('Column')
        axes[1].set_ylabel('Row')
        
        cbar = plt.colorbar(im, ax=axes[1], orientation='vertical', fraction=0.046, pad=0.04)
        cbar.set_label('Elevation (m)', rotation=270, labelpad=20)
        
        plt.tight_layout()
        
        output_path = FIGURES_DIR / "01_catchment_and_dem.png"
        plt.savefig(output_path, dpi=FIG_DPI, bbox_inches='tight')
        logger.info(f"[SAVED] Visualization saved: {output_path}")
        
        plt.close()
        
    except Exception as e:
        logger.warning(f"[WARNING] Visualization failed: {e}")


def main():
    """Main execution function."""
    logger.info("🚀 Starting Data Preparation and Validation")
    logger.info(f"Project: {PROJECT_NAME}")
    logger.info(f"Author: {AUTHOR}")
    logger.info(f"Date: {LAST_UPDATED}")
    
    try:
        # Step 1: Load catchment
        catchment = load_catchment_boundary()
        
        # Step 2: Load and process DEM
        dem, dem_transform, dem_crs, dem_meta = load_and_validate_dem(catchment)
        
        # Step 3: Visualize
        visualize_data(catchment, dem, dem_transform)
        
        logger.info("="*80)
        logger.info("[OK] DATA PREPARATION COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
        logger.info("[FOLDER] Outputs saved in:")
        logger.info(f"   - Temp data: {TEMP_DIR}")
        logger.info(f"   - Figures: {FIGURES_DIR}")
        logger.info(f"   - Logs: {LOGS_DIR}")
        
        return True
        
    except Exception as e:
        logger.error("="*80)
        logger.error("[ERROR] DATA PREPARATION FAILED!")
        logger.error("="*80)
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
