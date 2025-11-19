"""
Step 2: Calculate LS Factor (Topographic Factor)
Computes slope length and steepness factor from DEM

Author: Bhavya Singh
Date: 17 November 2025

Formula:
    LS = sqrt(flow_length / 22.13)^m × (sin(slope) / 0.0896)^n
    
Simplified (as per methodology):
    LS = sqrt(500/100) × (0.53×S + 0.076×S² + 0.76)
    where S = slope in percentage
"""

import sys
sys.path.append('/home/ubuntuksh/Desktop/RUSLE/scripts')

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from scipy.ndimage import generic_filter
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
        logging.FileHandler(LOGS_DIR / "02_ls_factor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def calculate_slope_percentage(dem, transform, nodata_value):
    """
    Calculate slope in percentage from DEM.
    
    Args:
        dem: DEM array (elevation in meters)
        transform: Affine transform
        nodata_value: NoData value to mask
        
    Returns:
        numpy.ndarray: Slope in percentage
    """
    logger.info("Calculating slope from DEM...")
    
    # Get cell size in degrees, convert to meters (approximate)
    cell_size_deg_x = abs(transform[0])
    cell_size_deg_y = abs(transform[4])
    
    # Convert degrees to meters (1 degree ≈ 111320 meters at equator)
    cell_size_x = cell_size_deg_x * 111320
    cell_size_y = cell_size_deg_y * 111320
    cell_size = (cell_size_x + cell_size_y) / 2
    
    logger.info(f"   - Cell size: {cell_size:.2f} meters")
    
    # Mask NoData values BEFORE any calculations
    dem_masked = np.ma.masked_equal(dem, nodata_value)
    
    # For gradient calculation, use a filled version but ONLY for convolution
    # Fill with edge values to avoid artifacts at boundaries
    dem_filled = dem_masked.filled(np.nan)
    
    # Calculate gradients using Sobel-like operators
    # dz/dx (east-west gradient)
    kernel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]) / (8 * cell_size)
    # dz/dy (north-south gradient)  
    kernel_y = np.array([[1, 2, 1], [0, 0, 0], [-1, -2, -1]]) / (8 * cell_size)
    
    # Apply convolution for gradients
    from scipy.ndimage import convolve
    
    # Use the original masked array for convolution, filling with mean for calculation
    dem_for_conv = dem_masked.filled(dem_masked.mean())
    
    grad_x = convolve(dem_for_conv, kernel_x, mode='nearest')
    grad_y = convolve(dem_for_conv, kernel_y, mode='nearest')
    
    # Calculate slope in radians
    slope_rad = np.arctan(np.sqrt(grad_x**2 + grad_y**2))
    
    # Convert to percentage (rise/run × 100)
    slope_pct = np.tan(slope_rad) * 100
    
    # Mask NoData areas
    slope_pct = np.ma.masked_where(dem_masked.mask, slope_pct)
    
    # Validation
    valid_slope = slope_pct[~slope_pct.mask]
    logger.info(f"   - Slope range: {valid_slope.min():.2f}% - {valid_slope.max():.2f}%")
    logger.info(f"   - Mean slope: {valid_slope.mean():.2f}%")
    logger.info(f"   - Median slope: {np.median(valid_slope):.2f}%")
    
    # Error check: unrealistic slopes
    if valid_slope.max() > 200:
        logger.warning(f"[WARNING]  Very steep slopes detected (max: {valid_slope.max():.1f}%)")
        logger.warning("    This may indicate DEM artifacts - capping at 200%")
        slope_pct = np.clip(slope_pct, 0, 200)
    
    if valid_slope.min() < 0:
        logger.error("[ERROR] Negative slopes detected - DEM processing error!")
        raise ValueError("Invalid slope calculation")
    
    logger.info("[OK] Slope calculation completed")
    
    return slope_pct.filled(nodata_value)


def calculate_ls_factor(slope_pct, slope_length=500, nodata_value=-9999):
    """
    Calculate LS factor using simplified RUSLE equation.
    
    Args:
        slope_pct: Slope in percentage
        slope_length: Assumed slope length in meters (default: 500m)
        nodata_value: NoData value
        
    Returns:
        numpy.ndarray: LS factor
    """
    logger.info("Calculating LS factor...")
    logger.info(f"   - Assumed slope length: {slope_length} meters")
    
    # Mask NoData
    slope_masked = np.ma.masked_equal(slope_pct, nodata_value)
    
    # RUSLE LS equation (simplified)
    # LS = sqrt(L/22.13) × (65.41×sin²θ + 4.56×sinθ + 0.065)
    # 
    # Simplified for constant slope length L:
    # LS4 = sqrt(L / 22.13) -> slope length factor
    # LS3 = 0.53 × S -> linear slope component
    # LS2 = 0.076 × S² -> quadratic slope component  
    # LS1 = LS3 + LS2 + 0.76 -> combined slope steepness
    # LS = LS4 × LS1 -> final LS factor
    
    LS4 = np.sqrt(slope_length / 22.13)
    LS3 = 0.53 * slope_masked
    LS2 = 0.076 * (slope_masked ** 2)
    LS1 = LS3 + LS2 + 0.76
    
    LS = LS4 * LS1
    
    # Validation
    valid_ls = LS[~LS.mask]
    logger.info(f"   - LS factor range: {valid_ls.min():.4f} - {valid_ls.max():.4f}")
    logger.info(f"   - Mean LS: {valid_ls.mean():.4f}")
    logger.info(f"   - Median LS: {np.median(valid_ls):.4f}")
    
    # Error checks
    if valid_ls.min() < 0:
        logger.error("[ERROR] Negative LS values detected!")
        raise ValueError("Invalid LS calculation")
    
    if valid_ls.max() > 100:
        logger.warning(f"[WARNING]  Very high LS values detected (max: {valid_ls.max():.2f})")
        logger.warning("    Expected range: 0-50 for most catchments")
        logger.warning("    Steep slopes with long flow paths can exceed 50")
    
    # Statistical distribution check
    percentiles = np.percentile(valid_ls, [10, 25, 50, 75, 90])
    logger.info(f"   - LS percentiles (10/25/50/75/90): " + 
                "/".join([f"{p:.2f}" for p in percentiles]))
    
    logger.info("[OK] LS factor calculation completed")
    
    return LS.filled(nodata_value)


def validate_ls_factor(ls_array, slope_pct, nodata_value):
    """
    Validate LS factor against slope to ensure realistic relationship.
    
    Args:
        ls_array: LS factor array
        slope_pct: Slope percentage array
        nodata_value: NoData value
        
    Returns:
        bool: True if validation passes
    """
    logger.info("="*80)
    logger.info("VALIDATING LS FACTOR")
    logger.info("="*80)
    
    # Mask NoData
    ls_masked = np.ma.masked_equal(ls_array, nodata_value)
    slope_masked = np.ma.masked_equal(slope_pct, nodata_value)
    
    # Combined mask
    combined_mask = ls_masked.mask | slope_masked.mask
    ls_valid = ls_masked[~combined_mask]
    slope_valid = slope_masked[~combined_mask]
    
    validation_passed = True
    
    # Check 1: LS increases with slope
    logger.info("\n1. Checking LS-Slope correlation...")
    correlation = np.corrcoef(slope_valid, ls_valid)[0, 1]
    logger.info(f"   Correlation coefficient: {correlation:.4f}")
    
    if correlation > 0.9:
        logger.info("   [OK] Strong positive correlation (expected)")
    elif correlation > 0.7:
        logger.warning("   [WARNING]  Moderate correlation (acceptable)")
    else:
        logger.error("   [ERROR] Weak correlation - LS should increase with slope!")
        validation_passed = False
    
    # Check 2: Flat areas have low LS
    logger.info("\n2. Checking flat areas (slope < 2%)...")
    flat_mask = slope_valid < 2
    if flat_mask.sum() > 0:
        flat_ls = ls_valid[flat_mask]
        logger.info(f"   - Flat area LS range: {flat_ls.min():.2f} - {flat_ls.max():.2f}")
        logger.info(f"   - Flat area mean LS: {flat_ls.mean():.2f}")
        
        if flat_ls.mean() < 2:
            logger.info("   [OK] Flat areas have low LS (< 2)")
        else:
            logger.warning(f"   [WARNING]  Flat areas have elevated LS (mean: {flat_ls.mean():.2f})")
    
    # Check 3: Steep areas have high LS
    logger.info("\n3. Checking steep areas (slope > 20%)...")
    steep_mask = slope_valid > 20
    if steep_mask.sum() > 0:
        steep_ls = ls_valid[steep_mask]
        logger.info(f"   - Steep area LS range: {steep_ls.min():.2f} - {steep_ls.max():.2f}")
        logger.info(f"   - Steep area mean LS: {steep_ls.mean():.2f}")
        
        if steep_ls.mean() > 5:
            logger.info("   [OK] Steep areas have high LS (> 5)")
        else:
            logger.warning(f"   [WARNING]  Steep areas have low LS (mean: {steep_ls.mean():.2f})")
    
    # Check 4: Value range validation
    logger.info("\n4. Checking LS value range...")
    ls_min, ls_max = FACTOR_RANGES['LS']
    if ls_valid.min() >= ls_min and ls_valid.max() <= ls_max:
        logger.info(f"   [OK] LS within expected range ({ls_min}-{ls_max})")
    else:
        logger.warning(f"   [WARNING]  LS outside typical range ({ls_min}-{ls_max})")
        logger.warning(f"      Actual: {ls_valid.min():.2f} - {ls_valid.max():.2f}")
        logger.warning("      This may be acceptable for mountainous terrain")
    
    # Check 5: No extreme outliers
    logger.info("\n5. Checking for outliers...")
    mean_ls = ls_valid.mean()
    std_ls = ls_valid.std()
    outliers = np.abs(ls_valid - mean_ls) > 3 * std_ls
    outlier_count = outliers.sum()
    outlier_pct = (outlier_count / len(ls_valid)) * 100
    
    logger.info(f"   - Outliers (>3sigma): {outlier_count:,} ({outlier_pct:.2f}%)")
    
    if outlier_pct < 1:
        logger.info("   [OK] Low outlier percentage (< 1%)")
    elif outlier_pct < 5:
        logger.warning(f"   [WARNING]  Moderate outliers ({outlier_pct:.2f}%)")
    else:
        logger.error(f"   [ERROR] High outlier percentage ({outlier_pct:.2f}%)")
        validation_passed = False
    
    logger.info("\n" + "="*80)
    if validation_passed:
        logger.info("[OK] LS FACTOR VALIDATION PASSED")
    else:
        logger.warning("[WARNING]  LS FACTOR VALIDATION WARNINGS PRESENT")
    logger.info("="*80 + "\n")
    
    return validation_passed


def visualize_ls_factor(dem, slope_pct, ls_factor, nodata_value):
    """
    Create comprehensive visualizations of DEM, slope, and LS factor.
    
    Args:
        dem: DEM array
        slope_pct: Slope percentage array
        ls_factor: LS factor array
        nodata_value: NoData value
    """
    logger.info("Creating visualizations...")
    
    try:
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Topographic Analysis - LS Factor Computation', 
                     fontsize=16, fontweight='bold', y=0.995)
        
        # Mask NoData for all arrays
        dem_plot = np.ma.masked_equal(dem, nodata_value)
        slope_plot = np.ma.masked_equal(slope_pct, nodata_value)
        ls_plot = np.ma.masked_equal(ls_factor, nodata_value)
        
        # Plot 1: DEM
        im1 = axes[0, 0].imshow(dem_plot, cmap='terrain', interpolation='bilinear')
        axes[0, 0].set_title('Digital Elevation Model (DEM)', fontweight='bold')
        axes[0, 0].set_xlabel('Column')
        axes[0, 0].set_ylabel('Row')
        cbar1 = plt.colorbar(im1, ax=axes[0, 0], fraction=0.046, pad=0.04)
        cbar1.set_label('Elevation (m)', rotation=270, labelpad=20)
        
        # Plot 2: Slope (%)
        im2 = axes[0, 1].imshow(slope_plot, cmap='YlOrRd', interpolation='bilinear', 
                                vmin=0, vmax=np.percentile(slope_plot.compressed(), 95))
        axes[0, 1].set_title('Slope Percentage', fontweight='bold')
        axes[0, 1].set_xlabel('Column')
        axes[0, 1].set_ylabel('Row')
        cbar2 = plt.colorbar(im2, ax=axes[0, 1], fraction=0.046, pad=0.04)
        cbar2.set_label('Slope (%)', rotation=270, labelpad=20)
        
        # Plot 3: LS Factor
        im3 = axes[0, 2].imshow(ls_plot, cmap='RdYlGn_r', interpolation='bilinear',
                                vmin=0, vmax=np.percentile(ls_plot.compressed(), 95))
        axes[0, 2].set_title('LS Factor (Topographic Factor)', fontweight='bold')
        axes[0, 2].set_xlabel('Column')
        axes[0, 2].set_ylabel('Row')
        cbar3 = plt.colorbar(im3, ax=axes[0, 2], fraction=0.046, pad=0.04)
        cbar3.set_label('LS Factor', rotation=270, labelpad=20)
        
        # Plot 4: Slope histogram
        slope_valid = slope_plot.compressed()
        axes[1, 0].hist(slope_valid, bins=50, color='darkorange', alpha=0.7, edgecolor='black')
        axes[1, 0].set_xlabel('Slope (%)')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].set_title('Slope Distribution', fontweight='bold')
        axes[1, 0].axvline(slope_valid.mean(), color='red', linestyle='--', 
                          linewidth=2, label=f'Mean: {slope_valid.mean():.2f}%')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # Plot 5: LS histogram
        ls_valid = ls_plot.compressed()
        axes[1, 1].hist(ls_valid, bins=50, color='forestgreen', alpha=0.7, edgecolor='black')
        axes[1, 1].set_xlabel('LS Factor')
        axes[1, 1].set_ylabel('Frequency')
        axes[1, 1].set_title('LS Factor Distribution', fontweight='bold')
        axes[1, 1].axvline(ls_valid.mean(), color='red', linestyle='--', 
                          linewidth=2, label=f'Mean: {ls_valid.mean():.2f}')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        # Plot 6: Slope vs LS scatter
        # Sample data for performance (use every 10th pixel)
        sample_idx = np.random.choice(len(slope_valid), 
                                     min(10000, len(slope_valid)), 
                                     replace=False)
        axes[1, 2].scatter(slope_valid[sample_idx], ls_valid[sample_idx], 
                          alpha=0.3, s=1, c='blue')
        axes[1, 2].set_xlabel('Slope (%)')
        axes[1, 2].set_ylabel('LS Factor')
        axes[1, 2].set_title('Slope vs LS Factor Relationship', fontweight='bold')
        axes[1, 2].grid(True, alpha=0.3)
        
        # Add correlation coefficient
        corr = np.corrcoef(slope_valid, ls_valid)[0, 1]
        axes[1, 2].text(0.05, 0.95, f'R² = {corr**2:.4f}', 
                       transform=axes[1, 2].transAxes, 
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                       verticalalignment='top', fontweight='bold')
        
        plt.tight_layout()
        
        output_path = FIGURES_DIR / "02_ls_factor_analysis.png"
        plt.savefig(output_path, dpi=FIG_DPI, bbox_inches='tight')
        logger.info(f"[SAVED] Visualization saved: {output_path}")
        
        plt.close()
        
    except Exception as e:
        logger.warning(f"[WARNING]  Visualization failed: {e}")


def main():
    """Main execution function."""
    logger.info("="*80)
    logger.info("STEP 2: TOPOGRAPHIC FACTOR (LS) CALCULATION")
    logger.info("="*80)
    logger.info(f"Project: {PROJECT_NAME}")
    logger.info(f"Author: {AUTHOR}")
    
    try:
        # Load processed DEM
        dem_path = TEMP_DIR / "dem_processed.tif"
        
        if not dem_path.exists():
            logger.error(f"[ERROR] Processed DEM not found: {dem_path}")
            logger.error("   Run 01_data_preparation.py first!")
            return False
        
        logger.info(f"[FOLDER] Loading DEM: {dem_path}")
        
        with rasterio.open(dem_path) as src:
            dem = src.read(1)
            dem_meta = src.meta.copy()
            transform = src.transform
            nodata = src.nodata if src.nodata is not None else NODATA_VALUE
        
        logger.info(f"[OK] DEM loaded: {dem.shape}")
        logger.info(f"   - CRS: {dem_meta['crs']}")
        logger.info(f"   - Resolution: {abs(transform[0]):.2f}m x {abs(transform[4]):.2f}m")
        
        # Step 1: Calculate slope
        slope_pct = calculate_slope_percentage(dem, transform, nodata)
        
        # Save slope
        slope_path = FACTORS_DIR / "slope_percentage.tif"
        with rasterio.open(slope_path, 'w', **dem_meta) as dst:
            dst.write(slope_pct, 1)
        logger.info(f"[SAVED] Slope saved: {slope_path}")
        
        # Step 2: Calculate LS factor
        ls_factor = calculate_ls_factor(slope_pct, slope_length=SLOPE_LENGTH, 
                                        nodata_value=nodata)
        
        # Save LS factor
        ls_path = FACTORS_DIR / "ls_factor.tif"
        with rasterio.open(ls_path, 'w', **dem_meta) as dst:
            dst.write(ls_factor, 1)
        logger.info(f"[SAVED] LS factor saved: {ls_path}")
        
        # Step 3: Validate LS factor
        validation_passed = validate_ls_factor(ls_factor, slope_pct, nodata)
        
        # Step 4: Visualize
        visualize_ls_factor(dem, slope_pct, ls_factor, nodata)
        
        # Summary statistics
        logger.info("="*80)
        logger.info("SUMMARY STATISTICS")
        logger.info("="*80)
        
        ls_valid = np.ma.masked_equal(ls_factor, nodata).compressed()
        slope_valid = np.ma.masked_equal(slope_pct, nodata).compressed()
        
        logger.info(f"Slope Statistics:")
        logger.info(f"  - Min: {slope_valid.min():.2f}%")
        logger.info(f"  - Max: {slope_valid.max():.2f}%")
        logger.info(f"  - Mean: {slope_valid.mean():.2f}%")
        logger.info(f"  - Median: {np.median(slope_valid):.2f}%")
        logger.info(f"  - Std Dev: {slope_valid.std():.2f}%")
        
        logger.info(f"\nLS Factor Statistics:")
        logger.info(f"  - Min: {ls_valid.min():.4f}")
        logger.info(f"  - Max: {ls_valid.max():.4f}")
        logger.info(f"  - Mean: {ls_valid.mean():.4f}")
        logger.info(f"  - Median: {np.median(ls_valid):.4f}")
        logger.info(f"  - Std Dev: {ls_valid.std():.4f}")
        
        logger.info("="*80)
        logger.info("[OK] LS FACTOR CALCULATION COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
        logger.info(f"[FOLDER] Outputs saved in:")
        logger.info(f"   - LS Factor: {ls_path}")
        logger.info(f"   - Slope: {slope_path}")
        logger.info(f"   - Figures: {FIGURES_DIR}")
        
        return validation_passed
        
    except Exception as e:
        logger.error("="*80)
        logger.error("[ERROR] LS FACTOR CALCULATION FAILED!")
        logger.error("="*80)
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
