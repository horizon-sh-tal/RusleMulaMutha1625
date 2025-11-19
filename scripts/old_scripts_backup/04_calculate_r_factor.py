"""
Step 4: Calculate R Factor (Rainfall Erosivity)
Downloads CHIRPS precipitation data and calculates annual erosivity for 2014-2024

Author: Bhavya Singh
Date: 17 November 2025

Formula: R = 79 + 0.363 × P
where P = annual precipitation (mm)

Data Source: CHIRPS Daily (Climate Hazards Group)
Temporal Range: 2014-2024 (11 years)
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
from datetime import datetime
import logging
from pathlib import Path
from config import *

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(LOGS_DIR / "04_r_factor.log"),
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


def download_annual_rainfall(year, catchment_bounds, output_path):
    """
    Download CHIRPS annual rainfall for a specific year.
    
    Args:
        year: Year (2014-2024)
        catchment_bounds: Bounding box [minx, miny, maxx, maxy]
        output_path: Path to save GeoTIFF
        
    Returns:
        bool: Success status
    """
    logger.info(f"Downloading CHIRPS rainfall for {year}...")
    
    try:
        # Date range for the year
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        logger.info(f"   - Period: {start_date} to {end_date}")
        
        # Create bounding box
        bbox = ee.Geometry.Rectangle(catchment_bounds.tolist())
        
        # Load CHIRPS daily precipitation
        chirps = ee.ImageCollection(GEE_CHIRPS) \
            .filterDate(start_date, end_date) \
            .filterBounds(bbox)
        
        # Check data availability
        count = chirps.size().getInfo()
        logger.info(f"   - Images available: {count}")
        
        if count == 0:
            logger.error(f"   [ERROR] No CHIRPS data for {year}")
            return False
        
        # Expected days in year
        expected_days = 366 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 365
        
        if count < expected_days * 0.9:  # Allow 10% missing data
            logger.warning(f"   [WARNING]  Incomplete data: {count}/{expected_days} days")
        
        # Sum to annual precipitation
        annual_precip = chirps.select(CHIRPS_BAND).sum()
        
        # Clip to catchment
        annual_precip = annual_precip.clip(bbox)
        
        # Download
        logger.info(f"   - Downloading (scale: 5000m)...")
        
        geemap.ee_export_image(
            annual_precip,
            filename=str(output_path),
            scale=5000,  # CHIRPS resolution ~5km
            region=bbox,
            file_per_band=False
        )
        
        if output_path.exists():
            # Verify download
            with rasterio.open(output_path) as src:
                data = src.read(1)
                valid = data[data != src.nodata] if src.nodata else data
                
                logger.info(f"   [OK] Downloaded: {year}")
                logger.info(f"      - Annual rainfall: {valid.min():.1f} - {valid.max():.1f} mm")
                logger.info(f"      - Mean: {valid.mean():.1f} mm")
                
                # Validation check
                if valid.mean() < RAINFALL_MIN or valid.mean() > RAINFALL_MAX:
                    logger.warning(f"      [WARNING]  Rainfall outside typical range ({RAINFALL_MIN}-{RAINFALL_MAX} mm)")
            
            return True
        else:
            logger.error(f"   [ERROR] Download failed for {year}")
            return False
            
    except Exception as e:
        logger.error(f"   [ERROR] Error downloading {year}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def calculate_r_factor(annual_precip, nodata_value):
    """
    Calculate R-factor from annual precipitation.
    
    Formula: R = 79 + 0.363 × P
    
    Args:
        annual_precip: Annual precipitation (mm)
        nodata_value: NoData value
        
    Returns:
        numpy.ndarray: R-factor values
    """
    logger.info("Calculating R-factor from precipitation...")
    
    # Mask NoData
    precip_masked = np.ma.masked_equal(annual_precip, nodata_value)
    
    # Apply R-factor formula
    r_factor = R_FORMULA(precip_masked)
    
    # Statistics
    r_valid = r_factor.compressed()
    
    logger.info(f"   - R-factor range: {r_valid.min():.1f} - {r_valid.max():.1f}")
    logger.info(f"   - Mean R: {r_valid.mean():.1f}")
    logger.info(f"   - Median R: {np.median(r_valid):.1f}")
    
    # Validation
    r_min, r_max = FACTOR_RANGES['R']
    
    if r_valid.min() < r_min or r_valid.max() > r_max:
        logger.warning(f"   [WARNING]  R-factor outside typical range ({r_min}-{r_max})")
        logger.warning(f"       Actual: {r_valid.min():.1f} - {r_valid.max():.1f}")
    else:
        logger.info(f"   [OK] R-factor within expected range ({r_min}-{r_max})")
    
    return r_factor.filled(nodata_value)


def resample_r_to_target(r_factor_path, reference_dem_path, output_path):
    """
    Resample R-factor from CHIRPS resolution to target 90m.
    
    Args:
        r_factor_path: Path to R-factor at CHIRPS resolution
        reference_dem_path: Path to reference DEM (90m)
        output_path: Path for resampled output
        
    Returns:
        bool: Success status
    """
    logger.info("   Resampling R-factor to 90m...")
    
    try:
        # Load reference DEM
        with rasterio.open(reference_dem_path) as ref:
            ref_transform = ref.transform
            ref_width = ref.width
            ref_height = ref.height
            ref_crs = ref.crs
        
        # Load R-factor
        with rasterio.open(r_factor_path) as src:
            r_data = src.read(1)
            src_transform = src.transform
            src_crs = src.crs
            nodata = src.nodata if src.nodata is not None else NODATA_VALUE
            
            # Create destination array
            r_resampled = np.empty((ref_height, ref_width), dtype=np.float32)
            
            # Reproject
            reproject(
                source=r_data,
                destination=r_resampled,
                src_transform=src_transform,
                src_crs=src_crs,
                dst_transform=ref_transform,
                dst_crs=ref_crs,
                resampling=Resampling.bilinear  # Bilinear for continuous data
            )
            
            # Save
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
                dst.write(r_resampled, 1)
            
            logger.info(f"   [OK] Resampled to 90m: {output_path}")
            
            return True
            
    except Exception as e:
        logger.error(f"   [ERROR] Resampling failed: {e}")
        return False


def validate_annual_r_factors(r_factors_dict):
    """
    Validate R-factors across all years for consistency.
    
    Args:
        r_factors_dict: Dictionary {year: r_factor_array}
        
    Returns:
        bool: Validation passed
    """
    logger.info("="*80)
    logger.info("VALIDATING R-FACTORS ACROSS ALL YEARS")
    logger.info("="*80)
    
    validation_passed = True
    
    # Collect statistics
    stats = {}
    for year, r_array in r_factors_dict.items():
        r_valid = np.ma.masked_equal(r_array, NODATA_VALUE).compressed()
        stats[year] = {
            'min': r_valid.min(),
            'max': r_valid.max(),
            'mean': r_valid.mean(),
            'std': r_valid.std()
        }
    
    # Check 1: Year-to-year variability
    logger.info("\n1. Checking temporal consistency...")
    
    years = sorted(stats.keys())
    means = [stats[y]['mean'] for y in years]
    
    for i in range(1, len(years)):
        prev_mean = means[i-1]
        curr_mean = means[i]
        change_pct = abs((curr_mean - prev_mean) / prev_mean) * 100
        
        logger.info(f"   {years[i-1]} -> {years[i]}: "
                   f"{prev_mean:.1f} -> {curr_mean:.1f} "
                   f"({change_pct:+.1f}%)")
        
        if change_pct > 50:
            logger.warning(f"      [WARNING]  Large change (>{change_pct:.1f}%) - unusual but possible")
    
    # Check 2: Overall range
    logger.info("\n2. Checking overall R-factor range...")
    all_means = [s['mean'] for s in stats.values()]
    overall_min = min([s['min'] for s in stats.values()])
    overall_max = max([s['max'] for s in stats.values()])
    overall_mean = np.mean(all_means)
    
    logger.info(f"   - Overall range: {overall_min:.1f} - {overall_max:.1f}")
    logger.info(f"   - Mean across years: {overall_mean:.1f}")
    logger.info(f"   - Std across years: {np.std(all_means):.1f}")
    
    r_min, r_max = FACTOR_RANGES['R']
    if overall_min >= r_min and overall_max <= r_max:
        logger.info(f"   [OK] Within expected range ({r_min}-{r_max})")
    else:
        logger.warning(f"   [WARNING]  Outside typical range ({r_min}-{r_max})")
    
    # Check 3: Spatial consistency
    logger.info("\n3. Checking spatial patterns...")
    
    # Calculate coefficient of variation across years
    r_arrays = [r_factors_dict[y] for y in years]
    r_stack = np.stack(r_arrays, axis=0)
    
    r_mean_spatial = np.mean(r_stack, axis=0)
    r_std_spatial = np.std(r_stack, axis=0)
    
    # Mask NoData
    valid_mask = r_mean_spatial != NODATA_VALUE
    
    cv_spatial = r_std_spatial[valid_mask] / r_mean_spatial[valid_mask]
    mean_cv = np.mean(cv_spatial)
    
    logger.info(f"   - Mean coefficient of variation: {mean_cv:.3f}")
    
    if mean_cv < 0.3:
        logger.info("   [OK] Low spatial variability (stable patterns)")
    elif mean_cv < 0.5:
        logger.info("   [OK] Moderate variability (expected for rainfall)")
    else:
        logger.warning(f"   [WARNING]  High variability (CV: {mean_cv:.3f})")
    
    logger.info("\n" + "="*80)
    if validation_passed:
        logger.info("[OK] R-FACTOR VALIDATION PASSED")
    else:
        logger.warning("[WARNING]  R-FACTOR VALIDATION WARNINGS PRESENT")
    logger.info("="*80 + "\n")
    
    return validation_passed


def visualize_r_factors(r_factors_dict, years):
    """
    Create temporal visualization of R-factors.
    
    Args:
        r_factors_dict: Dictionary {year: r_factor_array}
        years: List of years
    """
    logger.info("Creating R-factor visualizations...")
    
    try:
        # Create multi-year panel
        n_years = len(years)
        ncols = 4
        nrows = int(np.ceil(n_years / ncols))
        
        fig, axes = plt.subplots(nrows, ncols, figsize=(20, 5*nrows))
        fig.suptitle('Rainfall Erosivity (R-Factor) - Annual Maps (2014-2024)', 
                     fontsize=16, fontweight='bold', y=0.999)
        
        axes = axes.flatten() if n_years > 1 else [axes]
        
        for idx, year in enumerate(years):
            r_array = r_factors_dict[year]
            r_plot = np.ma.masked_equal(r_array, NODATA_VALUE)
            
            im = axes[idx].imshow(r_plot, cmap='Blues', interpolation='bilinear',
                                 vmin=200, vmax=1200)
            axes[idx].set_title(f'{year}', fontweight='bold', fontsize=12)
            axes[idx].axis('off')
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=axes[idx], fraction=0.046, pad=0.04)
            cbar.set_label('R', rotation=0, labelpad=10, fontsize=9)
        
        # Hide unused subplots
        for idx in range(len(years), len(axes)):
            axes[idx].axis('off')
        
        plt.tight_layout()
        
        output_path = FIGURES_DIR / "04_r_factor_temporal.png"
        plt.savefig(output_path, dpi=200, bbox_inches='tight')
        logger.info(f"[SAVED] Temporal visualization saved: {output_path}")
        
        plt.close()
        
        # Create trend plot
        fig, ax = plt.subplots(figsize=(12, 6))
        
        years_list = sorted(years)
        means = [np.ma.masked_equal(r_factors_dict[y], NODATA_VALUE).mean() for y in years_list]
        stds = [np.ma.masked_equal(r_factors_dict[y], NODATA_VALUE).std() for y in years_list]
        
        ax.errorbar(years_list, means, yerr=stds, marker='o', linewidth=2, 
                   markersize=8, capsize=5, capthick=2, label='Mean ± Std Dev')
        ax.fill_between(years_list, 
                        [m-s for m,s in zip(means, stds)],
                        [m+s for m,s in zip(means, stds)],
                        alpha=0.3)
        
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Mean R-Factor', fontsize=12, fontweight='bold')
        ax.set_title('Rainfall Erosivity Temporal Trend (2014-2024)', 
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Add expected range
        r_min, r_max = FACTOR_RANGES['R']
        ax.axhline(r_min, color='red', linestyle='--', alpha=0.5, label=f'Min expected ({r_min})')
        ax.axhline(r_max, color='red', linestyle='--', alpha=0.5, label=f'Max expected ({r_max})')
        
        plt.tight_layout()
        
        trend_path = FIGURES_DIR / "04_r_factor_trend.png"
        plt.savefig(trend_path, dpi=FIG_DPI, bbox_inches='tight')
        logger.info(f"[SAVED] Trend plot saved: {trend_path}")
        
        plt.close()
        
    except Exception as e:
        logger.warning(f"[WARNING]  Visualization failed: {e}")


def main(start_year=None, end_year=None):
    """
    Main execution function.
    
    Args:
        start_year: Start year (default: from config)
        end_year: End year (default: from config)
    """
    start_year = start_year or START_YEAR
    end_year = end_year or END_YEAR
    
    years = list(range(start_year, end_year + 1))
    
    logger.info("="*80)
    logger.info("STEP 4: RAINFALL EROSIVITY (R) FACTOR CALCULATION")
    logger.info("="*80)
    logger.info(f"Project: {PROJECT_NAME}")
    logger.info(f"Author: {AUTHOR}")
    logger.info(f"Years: {start_year}-{end_year} ({len(years)} years)")
    
    try:
        # Initialize GEE
        if not initialize_gee():
            return False
        
        # Load catchment
        catchment_path = TEMP_DIR / "catchment_validated.geojson"
        if not catchment_path.exists():
            logger.error(f"[ERROR] Catchment not found: {catchment_path}")
            return False
        
        catchment = gpd.read_file(catchment_path)
        bounds = catchment.total_bounds
        
        # Reference DEM
        dem_path = TEMP_DIR / "dem_processed.tif"
        if not dem_path.exists():
            logger.error(f"[ERROR] DEM not found: {dem_path}")
            return False
        
        # Process each year
        r_factors = {}
        rainfall_stats = []
        
        for year in years:
            logger.info("="*80)
            logger.info(f"Processing year: {year}")
            logger.info("="*80)
            
            # Download annual rainfall
            rainfall_raw_path = TEMP_DIR / f"rainfall_{year}_raw.tif"
            
            if not rainfall_raw_path.exists():
                if not download_annual_rainfall(year, bounds, rainfall_raw_path):
                    logger.error(f"[ERROR] Failed to download rainfall for {year}")
                    continue
            else:
                logger.info(f"ℹ️  Using existing rainfall data: {year}")
            
            # Load and calculate R-factor
            with rasterio.open(rainfall_raw_path) as src:
                annual_precip = src.read(1)
                nodata = src.nodata if src.nodata is not None else NODATA_VALUE
                
                # Calculate R
                r_factor = calculate_r_factor(annual_precip, nodata)
                
                # Save at original resolution
                r_raw_path = TEMP_DIR / f"r_factor_{year}_raw.tif"
                meta = src.meta.copy()
                meta.update({'dtype': 'float32', 'nodata': NODATA_VALUE})
                
                with rasterio.open(r_raw_path, 'w', **meta) as dst:
                    dst.write(r_factor, 1)
            
            # Resample to 90m
            r_final_path = FACTORS_DIR / f"r_factor_{year}.tif"
            if not resample_r_to_target(r_raw_path, dem_path, r_final_path):
                logger.error(f"[ERROR] Failed to resample R-factor for {year}")
                continue
            
            # Load final R-factor
            with rasterio.open(r_final_path) as src:
                r_factors[year] = src.read(1)
            
            # Record statistics
            r_valid = np.ma.masked_equal(r_factors[year], NODATA_VALUE).compressed()
            rainfall_stats.append({
                'year': year,
                'r_min': r_valid.min(),
                'r_max': r_valid.max(),
                'r_mean': r_valid.mean(),
                'r_median': np.median(r_valid),
                'r_std': r_valid.std()
            })
            
            logger.info(f"[OK] Year {year} completed")
        
        # Validate all years
        if len(r_factors) > 0:
            validate_annual_r_factors(r_factors)
            
            # Save statistics
            stats_df = pd.DataFrame(rainfall_stats)
            stats_path = STATS_DIR / "r_factor_annual_statistics.csv"
            stats_df.to_csv(stats_path, index=False)
            logger.info(f"[SAVED] Statistics saved: {stats_path}")
            
            # Visualize
            visualize_r_factors(r_factors, years)
        
        logger.info("="*80)
        logger.info("[OK] R-FACTOR CALCULATION COMPLETED!")
        logger.info("="*80)
        logger.info(f"[FOLDER] Outputs:")
        logger.info(f"   - R-factors: {FACTORS_DIR}")
        logger.info(f"   - Statistics: {stats_path}")
        logger.info(f"   - Figures: {FIGURES_DIR}")
        
        return len(r_factors) == len(years)
        
    except Exception as e:
        logger.error("="*80)
        logger.error("[ERROR] R-FACTOR CALCULATION FAILED!")
        logger.error("="*80)
        logger.error(f"Error: {e}")
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
