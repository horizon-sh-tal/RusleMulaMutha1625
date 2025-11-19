"""
Step 7: Calculate RUSLE (Soil Loss)
Multiplies all factors and classifies erosion severity

Author: Bhavya Singh
Date: 17 November 2025

RUSLE Equation: A = R × K × LS × C × P
where A = annual soil loss (t/ha/yr)
"""

import sys
sys.path.append('/home/ubuntuksh/Desktop/RUSLE/scripts')

import numpy as np
import rasterio
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
        logging.FileHandler(LOGS_DIR / "07_rusle_calculation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_factor(factor_name, year=None):
    """
    Load a RUSLE factor.
    
    Args:
        factor_name: Factor name (r, k, ls, c, p)
        year: Year (for R, C, P) or None (for K, LS)
        
    Returns:
        tuple: (factor_array, metadata)
    """
    if factor_name == 'ls':
        path = FACTORS_DIR / "ls_factor.tif"
    elif factor_name == 'k':
        path = FACTORS_DIR / "k_factor.tif"
    elif factor_name in ['r', 'c', 'p']:
        if year is None:
            raise ValueError(f"{factor_name.upper()}-factor requires year")
        path = FACTORS_DIR / f"{factor_name}_factor_{year}.tif"
    else:
        raise ValueError(f"Unknown factor: {factor_name}")
    
    if not path.exists():
        logger.error(f"[ERROR] Factor not found: {path}")
        return None, None
    
    with rasterio.open(path) as src:
        data = src.read(1)
        meta = src.meta.copy()
    
    return data, meta


def calculate_rusle(r_factor, k_factor, ls_factor, c_factor, p_factor, nodata_value):
    """
    Calculate soil loss using RUSLE equation.
    
    A = R × K × LS × C × P
    
    Args:
        r_factor, k_factor, ls_factor, c_factor, p_factor: Factor arrays
        nodata_value: NoData value
        
    Returns:
        numpy.ndarray: Annual soil loss (t/ha/yr)
    """
    logger.info("Calculating RUSLE (A = R × K × LS × C × P)...")
    
    # Mask NoData in all factors
    r_masked = np.ma.masked_equal(r_factor, nodata_value)
    k_masked = np.ma.masked_equal(k_factor, nodata_value)
    ls_masked = np.ma.masked_equal(ls_factor, nodata_value)
    c_masked = np.ma.masked_equal(c_factor, nodata_value)
    p_masked = np.ma.masked_equal(p_factor, nodata_value)
    
    # Check dimensions match
    shapes = [r_masked.shape, k_masked.shape, ls_masked.shape, c_masked.shape, p_masked.shape]
    if len(set(shapes)) > 1:
        logger.error(f"[ERROR] Factor dimensions mismatch: {shapes}")
        raise ValueError("All factors must have same dimensions")
    
    # Multiply factors
    soil_loss = r_masked * k_masked * ls_masked * c_masked * p_masked
    
    # Statistics
    sl_valid = soil_loss.compressed()
    
    logger.info(f"   Soil Loss Statistics:")
    logger.info(f"   - Min: {sl_valid.min():.2f} t/ha/yr")
    logger.info(f"   - Max: {sl_valid.max():.2f} t/ha/yr")
    logger.info(f"   - Mean: {sl_valid.mean():.2f} t/ha/yr")
    logger.info(f"   - Median: {np.median(sl_valid):.2f} t/ha/yr")
    logger.info(f"   - Std Dev: {sl_valid.std():.2f} t/ha/yr")
    logger.info(f"   - 90th percentile: {np.percentile(sl_valid, 90):.2f} t/ha/yr")
    logger.info(f"   - 95th percentile: {np.percentile(sl_valid, 95):.2f} t/ha/yr")
    
    # Validation
    if sl_valid.mean() < SOIL_LOSS_MIN_EXPECTED or sl_valid.mean() > SOIL_LOSS_MAX_EXPECTED:
        logger.warning(f"   [WARNING]  Mean soil loss outside expected range ({SOIL_LOSS_MIN_EXPECTED}-{SOIL_LOSS_MAX_EXPECTED} t/ha/yr)")
    else:
        logger.info(f"   [OK] Mean soil loss within expected range ({SOIL_LOSS_MIN_EXPECTED}-{SOIL_LOSS_MAX_EXPECTED} t/ha/yr)")
    
    if sl_valid.max() > SOIL_LOSS_ABSOLUTE_MAX:
        logger.warning(f"   [WARNING]  Max soil loss exceeds absolute threshold ({SOIL_LOSS_ABSOLUTE_MAX} t/ha/yr)")
        logger.warning(f"       This may indicate erosion hotspots or calculation errors")
    
    return soil_loss.filled(nodata_value)


def classify_erosion_severity(soil_loss, nodata_value):
    """
    Classify soil loss into severity categories.
    
    Classes:
    1: <5 t/ha/yr (Slight)
    2: 5-10 (Moderate)
    3: 10-20 (High)
    4: 20-40 (Very High)
    5: >40 (Severe)
    
    Args:
        soil_loss: Soil loss array (t/ha/yr)
        nodata_value: NoData value
        
    Returns:
        numpy.ndarray: Erosion class (1-5)
    """
    logger.info("Classifying erosion severity...")
    
    # Initialize classification array
    erosion_class = np.full_like(soil_loss, nodata_value, dtype=np.int16)
    
    # Mask NoData
    valid_mask = soil_loss != nodata_value
    
    # Apply classification
    for class_id, class_info in EROSION_CLASSES.items():
        lower, upper = class_info['range']
        mask = valid_mask & (soil_loss >= lower) & (soil_loss < upper)
        erosion_class[mask] = class_id
        
        count = mask.sum()
        pct = (count / valid_mask.sum()) * 100 if valid_mask.sum() > 0 else 0
        
        logger.info(f"   Class {class_id} ({class_info['label']:12s}): "
                   f"{count:8,} pixels ({pct:5.2f}%)")
    
    return erosion_class


def validate_rusle_output(soil_loss, erosion_class, year, nodata_value):
    """
    Comprehensive validation of RUSLE outputs.
    
    Args:
        soil_loss: Soil loss array
        erosion_class: Erosion classification array
        year: Year
        nodata_value: NoData value
        
    Returns:
        bool: Validation passed
    """
    logger.info("="*80)
    logger.info(f"VALIDATING RUSLE OUTPUT FOR {year}")
    logger.info("="*80)
    
    validation_passed = True
    
    sl_valid = np.ma.masked_equal(soil_loss, nodata_value).compressed()
    
    # Check 1: No negative values
    logger.info("\n1. Checking for negative values...")
    if sl_valid.min() < 0:
        logger.error(f"   [ERROR] Negative soil loss detected: {sl_valid.min():.2f}")
        validation_passed = False
    else:
        logger.info("   [OK] No negative values")
    
    # Check 2: Reasonable range
    logger.info("\n2. Checking value range...")
    if sl_valid.mean() >= SOIL_LOSS_MIN_EXPECTED and sl_valid.mean() <= SOIL_LOSS_MAX_EXPECTED:
        logger.info(f"   [OK] Mean within expected range ({SOIL_LOSS_MIN_EXPECTED}-{SOIL_LOSS_MAX_EXPECTED})")
    else:
        logger.warning(f"   [WARNING]  Mean outside expected range: {sl_valid.mean():.2f}")
    
    # Check 3: Classification coverage
    logger.info("\n3. Checking classification coverage...")
    ec_valid = np.ma.masked_equal(erosion_class, nodata_value).compressed()
    class_counts = {i: (ec_valid == i).sum() for i in range(1, 6)}
    total_classified = sum(class_counts.values())
    
    if total_classified == len(ec_valid):
        logger.info("   [OK] All pixels classified")
    else:
        logger.warning(f"   [WARNING]  {len(ec_valid) - total_classified} pixels unclassified")
    
    # Check 4: Severe erosion percentage
    logger.info("\n4. Checking severe erosion extent...")
    severe_pct = (class_counts[5] / len(ec_valid)) * 100 if len(ec_valid) > 0 else 0
    
    if severe_pct < 5:
        logger.info(f"   [OK] Severe erosion limited ({severe_pct:.1f}%)")
    elif severe_pct < 15:
        logger.warning(f"   [WARNING]  Moderate severe erosion ({severe_pct:.1f}%)")
    else:
        logger.error(f"   [ERROR] High severe erosion ({severe_pct:.1f}%) - review inputs")
        validation_passed = False
    
    # Check 5: Outliers
    logger.info("\n5. Checking for outliers...")
    mean_sl = sl_valid.mean()
    std_sl = sl_valid.std()
    outliers = np.abs(sl_valid - mean_sl) > 3 * std_sl
    outlier_pct = (outliers.sum() / len(sl_valid)) * 100
    
    logger.info(f"   - Outliers (>3sigma): {outliers.sum():,} ({outlier_pct:.2f}%)")
    
    if outlier_pct < 1:
        logger.info("   [OK] Low outlier percentage")
    else:
        logger.warning(f"   [WARNING]  Elevated outliers ({outlier_pct:.2f}%)")
    
    logger.info("\n" + "="*80)
    if validation_passed:
        logger.info("[OK] RUSLE VALIDATION PASSED")
    else:
        logger.warning("[WARNING]  RUSLE VALIDATION WARNINGS PRESENT")
    logger.info("="*80 + "\n")
    
    return validation_passed


def visualize_rusle_output(soil_loss, erosion_class, year, nodata_value):
    """Create visualization of soil loss and classification."""
    logger.info(f"Creating visualizations for {year}...")
    
    try:
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        fig.suptitle(f'RUSLE Soil Erosion Analysis - {year}', 
                     fontsize=16, fontweight='bold')
        
        sl_plot = np.ma.masked_equal(soil_loss, nodata_value)
        ec_plot = np.ma.masked_equal(erosion_class, nodata_value)
        
        # Plot 1: Soil loss (continuous)
        im1 = axes[0].imshow(sl_plot, cmap='YlOrRd', interpolation='bilinear',
                            vmin=0, vmax=np.percentile(sl_plot.compressed(), 95))
        axes[0].set_title('Annual Soil Loss (t/ha/yr)', fontweight='bold')
        axes[0].axis('off')
        cbar1 = plt.colorbar(im1, ax=axes[0], fraction=0.046, pad=0.04)
        cbar1.set_label('Soil Loss (t/ha/yr)', rotation=270, labelpad=20)
        
        # Plot 2: Erosion classification
        colors = [EROSION_CLASSES[i]['color'] for i in range(1, 6)]
        from matplotlib.colors import ListedColormap
        cmap_class = ListedColormap(colors)
        
        im2 = axes[1].imshow(ec_plot, cmap=cmap_class, interpolation='nearest',
                            vmin=1, vmax=5)
        axes[1].set_title('Erosion Severity Classification', fontweight='bold')
        axes[1].axis('off')
        
        cbar2 = plt.colorbar(im2, ax=axes[1], fraction=0.046, pad=0.04, ticks=[1,2,3,4,5])
        cbar2.set_label('Severity', rotation=270, labelpad=20)
        cbar2.ax.set_yticklabels([EROSION_CLASSES[i]['label'] for i in range(1, 6)])
        
        # Plot 3: Pie chart
        ec_valid = ec_plot.compressed()
        class_counts = [((ec_valid == i).sum()) for i in range(1, 6)]
        class_labels = [EROSION_CLASSES[i]['label'] for i in range(1, 6)]
        
        axes[2].pie(class_counts, labels=class_labels, colors=colors,
                   autopct='%1.1f%%', startangle=90)
        axes[2].set_title('Erosion Class Distribution', fontweight='bold')
        
        plt.tight_layout()
        
        output_path = MAPS_DIR / f"soil_loss_map_{year}.png"
        plt.savefig(output_path, dpi=FIG_DPI, bbox_inches='tight')
        logger.info(f"[SAVED] Visualization saved: {output_path}")
        
        plt.close()
        
    except Exception as e:
        logger.warning(f"[WARNING]  Visualization failed: {e}")


def main(start_year=None, end_year=None):
    """Main execution function."""
    start_year = start_year or START_YEAR
    end_year = end_year or END_YEAR
    years = list(range(start_year, end_year + 1))
    
    logger.info("="*80)
    logger.info("STEP 7: RUSLE CALCULATION & CLASSIFICATION")
    logger.info("="*80)
    logger.info(f"Years: {start_year}-{end_year} ({len(years)} years)")
    
    try:
        # Load static factors (K, LS)
        logger.info("\nLoading static factors...")
        k_factor, k_meta = load_factor('k')
        ls_factor, _ = load_factor('ls')
        
        if k_factor is None or ls_factor is None:
            logger.error("[ERROR] Static factors not found")
            return False
        
        logger.info(f"[OK] K-factor loaded: {k_factor.shape}")
        logger.info(f"[OK] LS-factor loaded: {ls_factor.shape}")
        
        rusle_stats = []
        
        for year in years:
            logger.info("="*80)
            logger.info(f"Processing year: {year}")
            logger.info("="*80)
            
            # Load annual factors
            r_factor, _ = load_factor('r', year)
            c_factor, _ = load_factor('c', year)
            p_factor, _ = load_factor('p', year)
            
            if r_factor is None or c_factor is None or p_factor is None:
                logger.error(f"[ERROR] Annual factors missing for {year}")
                continue
            
            logger.info(f"[OK] All factors loaded for {year}")
            
            # Calculate RUSLE
            soil_loss = calculate_rusle(r_factor, k_factor, ls_factor, 
                                       c_factor, p_factor, NODATA_VALUE)
            
            # Classify
            erosion_class = classify_erosion_severity(soil_loss, NODATA_VALUE)
            
            # Validate
            validate_rusle_output(soil_loss, erosion_class, year, NODATA_VALUE)
            
            # Save soil loss
            sl_path = MAPS_DIR / f"soil_loss_{year}.tif"
            with rasterio.open(sl_path, 'w', **k_meta) as dst:
                dst.write(soil_loss, 1)
            logger.info(f"[SAVED] Soil loss saved: {sl_path}")
            
            # Save classification
            ec_path = MAPS_DIR / f"erosion_class_{year}.tif"
            ec_meta = k_meta.copy()
            ec_meta.update({'dtype': 'int16'})
            
            with rasterio.open(ec_path, 'w', **ec_meta) as dst:
                dst.write(erosion_class, 1)
            logger.info(f"[SAVED] Classification saved: {ec_path}")
            
            # Visualize
            visualize_rusle_output(soil_loss, erosion_class, year, NODATA_VALUE)
            
            # Statistics
            sl_valid = np.ma.masked_equal(soil_loss, NODATA_VALUE).compressed()
            ec_valid = np.ma.masked_equal(erosion_class, NODATA_VALUE).compressed()
            
            class_areas = {}
            for i in range(1, 6):
                count = (ec_valid == i).sum()
                # Convert pixels to area (km²)
                pixel_area_m2 = TARGET_RESOLUTION ** 2
                area_km2 = (count * pixel_area_m2) / 1e6
                class_areas[EROSION_CLASSES[i]['label']] = area_km2
            
            rusle_stats.append({
                'year': year,
                'min': sl_valid.min(),
                'max': sl_valid.max(),
                'mean': sl_valid.mean(),
                'median': np.median(sl_valid),
                'std': sl_valid.std(),
                'p90': np.percentile(sl_valid, 90),
                'p95': np.percentile(sl_valid, 95),
                **class_areas
            })
            
            logger.info(f"[OK] Year {year} completed")
        
        # Save statistics
        if len(rusle_stats) > 0:
            stats_df = pd.DataFrame(rusle_stats)
            stats_path = STATS_DIR / "rusle_annual_statistics.csv"
            stats_df.to_csv(stats_path, index=False)
            logger.info(f"\n[SAVED] Annual statistics saved: {stats_path}")
        
        logger.info("="*80)
        logger.info("[OK] RUSLE CALCULATION COMPLETED!")
        logger.info("="*80)
        
        return len(rusle_stats) == len(years)
        
    except Exception as e:
        logger.error(f"[ERROR] RUSLE CALCULATION FAILED: {e}")
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
