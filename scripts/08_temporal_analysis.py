"""
Step 8: Temporal Analysis & Validation
Analyzes trends, change detection, and validates against literature

Author: Bhavya Singh
Date: 17 November 2025

Performs:
- Temporal trend analysis
- Change detection (2024 vs 2014)
- Basin-wide statistics
- Validation against literature
"""

import sys
sys.path.append('/home/ubuntuksh/Desktop/RUSLE/scripts')

import numpy as np
import rasterio
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from pathlib import Path
from scipy import stats
from config import *

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(LOGS_DIR / "08_temporal_analysis.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_annual_soil_loss(start_year, end_year):
    """Load all annual soil loss maps."""
    logger.info("Loading annual soil loss maps...")
    
    years = list(range(start_year, end_year + 1))
    soil_loss_data = {}
    
    for year in years:
        path = MAPS_DIR / f"soil_loss_{year}.tif"
        
        if not path.exists():
            logger.warning(f"   [WARNING]  Missing: {year}")
            continue
        
        with rasterio.open(path) as src:
            data = src.read(1)
            meta = src.meta
        
        soil_loss_data[year] = data
        logger.info(f"   [OK] Loaded: {year}")
    
    logger.info(f"Loaded {len(soil_loss_data)} years")
    return soil_loss_data, meta


def calculate_temporal_statistics(soil_loss_data, nodata_value):
    """Calculate basin-wide statistics for each year."""
    logger.info("Calculating temporal statistics...")
    
    stats_list = []
    
    for year, data in sorted(soil_loss_data.items()):
        valid = np.ma.masked_equal(data, nodata_value).compressed()
        
        stats_list.append({
            'year': year,
            'min': valid.min(),
            'max': valid.max(),
            'mean': valid.mean(),
            'median': np.median(valid),
            'std': valid.std(),
            'p25': np.percentile(valid, 25),
            'p75': np.percentile(valid, 75),
            'p90': np.percentile(valid, 90),
            'p95': np.percentile(valid, 95),
            'pixels': len(valid)
        })
    
    df = pd.DataFrame(stats_list)
    logger.info(f"   [OK] Statistics calculated for {len(df)} years")
    
    return df


def detect_temporal_trends(stats_df):
    """
    Detect temporal trends using linear regression.
    
    Returns:
        dict: Trend analysis results
    """
    logger.info("Detecting temporal trends...")
    
    years = stats_df['year'].values
    means = stats_df['mean'].values
    
    # Linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(years, means)
    
    logger.info(f"\n   Trend Analysis (Mean Soil Loss):")
    logger.info(f"   - Slope: {slope:.4f} t/ha/yr per year")
    logger.info(f"   - R²: {r_value**2:.4f}")
    logger.info(f"   - P-value: {p_value:.4f}")
    
    if p_value < 0.05:
        if slope > 0:
            logger.info(f"   [OK] Significant INCREASING trend (p<0.05)")
            trend = "increasing"
        else:
            logger.info(f"   [OK] Significant DECREASING trend (p<0.05)")
            trend = "decreasing"
    else:
        logger.info(f"   ℹ️  No significant trend (p≥0.05)")
        trend = "stable"
    
    # Calculate change percentage
    change_pct = ((means[-1] - means[0]) / means[0]) * 100
    logger.info(f"   - Total change: {change_pct:+.2f}% ({stats_df['year'].min()}-{stats_df['year'].max()})")
    
    return {
        'slope': slope,
        'intercept': intercept,
        'r_squared': r_value**2,
        'p_value': p_value,
        'trend': trend,
        'change_pct': change_pct
    }


def create_change_map(soil_loss_data, start_year, end_year, meta, nodata_value):
    """Create change detection map (end_year - start_year)."""
    logger.info(f"Creating change map ({end_year} - {start_year})...")
    
    if start_year not in soil_loss_data or end_year not in soil_loss_data:
        logger.error(f"   [ERROR] Missing data for {start_year} or {end_year}")
        return None
    
    start_data = soil_loss_data[start_year]
    end_data = soil_loss_data[end_year]
    
    # Calculate change
    start_masked = np.ma.masked_equal(start_data, nodata_value)
    end_masked = np.ma.masked_equal(end_data, nodata_value)
    
    change = end_masked - start_masked
    change_arr = change.filled(nodata_value)
    
    # Statistics
    change_valid = change.compressed()
    
    logger.info(f"\n   Change Statistics:")
    logger.info(f"   - Min: {change_valid.min():.2f} t/ha/yr")
    logger.info(f"   - Max: {change_valid.max():.2f} t/ha/yr")
    logger.info(f"   - Mean: {change_valid.mean():.2f} t/ha/yr")
    logger.info(f"   - Median: {np.median(change_valid):.2f} t/ha/yr")
    
    increased = (change_valid > 5).sum()
    decreased = (change_valid < -5).sum()
    stable = ((change_valid >= -5) & (change_valid <= 5)).sum()
    
    total = len(change_valid)
    logger.info(f"\n   Change Categories:")
    logger.info(f"   - Increased (>5): {increased:,} ({increased/total*100:.1f}%)")
    logger.info(f"   - Stable (±5): {stable:,} ({stable/total*100:.1f}%)")
    logger.info(f"   - Decreased (<-5): {decreased:,} ({decreased/total*100:.1f}%)")
    
    # Save change map
    change_path = MAPS_DIR / f"soil_loss_change_{start_year}_{end_year}.tif"
    with rasterio.open(change_path, 'w', **meta) as dst:
        dst.write(change_arr, 1)
    logger.info(f"\n   [SAVED] Change map saved: {change_path}")
    
    return change_arr


def validate_against_literature(stats_df):
    """
    Validate results against published literature.
    
    Expected range for similar catchments in Western Ghats: 8-25 t/ha/yr
    """
    logger.info("="*80)
    logger.info("VALIDATING AGAINST LITERATURE")
    logger.info("="*80)
    
    mean_overall = stats_df['mean'].mean()
    median_overall = stats_df['median'].mean()
    
    logger.info(f"\n   Overall Statistics (2014-2024):")
    logger.info(f"   - Mean soil loss: {mean_overall:.2f} t/ha/yr")
    logger.info(f"   - Median soil loss: {median_overall:.2f} t/ha/yr")
    
    # Literature values for similar catchments
    lit_min = 8.0
    lit_max = 25.0
    
    logger.info(f"\n   Literature Comparison:")
    logger.info(f"   - Expected range: {lit_min}-{lit_max} t/ha/yr")
    logger.info(f"      (based on Western Ghats catchments)")
    
    if mean_overall >= lit_min and mean_overall <= lit_max:
        logger.info(f"   [OK] Mean within literature range")
        validation_status = "PASSED"
    elif mean_overall < lit_min:
        logger.warning(f"   [WARNING]  Mean below literature range")
        logger.warning(f"       Possible causes: conservative factors, data quality")
        validation_status = "LOW"
    else:
        logger.warning(f"   [WARNING]  Mean above literature range")
        logger.warning(f"       Possible causes: severe erosion, factor overestimation")
        validation_status = "HIGH"
    
    # Year-to-year consistency
    logger.info(f"\n   Temporal Consistency:")
    mean_diff = stats_df['mean'].diff().abs()
    mean_change = mean_diff.mean()
    max_change = mean_diff.max()
    
    logger.info(f"   - Average year-to-year change: {mean_change:.2f} t/ha/yr")
    logger.info(f"   - Maximum year-to-year change: {max_change:.2f} t/ha/yr")
    
    if max_change < stats_df['mean'].mean() * 0.5:
        logger.info(f"   [OK] Temporal changes are consistent (<50% jumps)")
    else:
        logger.warning(f"   [WARNING]  Large temporal jumps detected")
    
    logger.info("\n" + "="*80)
    logger.info(f"VALIDATION STATUS: {validation_status}")
    logger.info("="*80 + "\n")
    
    return validation_status


def visualize_temporal_analysis(stats_df, trend_results):
    """Create comprehensive temporal analysis visualizations."""
    logger.info("Creating temporal visualizations...")
    
    try:
        # Figure 1: Multi-panel temporal analysis
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Temporal Analysis of Soil Erosion (2014-2024)', 
                     fontsize=16, fontweight='bold')
        
        years = stats_df['year'].values
        
        # Plot 1: Mean with trend line
        ax1 = axes[0, 0]
        ax1.plot(years, stats_df['mean'], 'o-', color='#d62728', 
                linewidth=2, markersize=8, label='Observed Mean')
        
        # Trend line
        trend_line = trend_results['slope'] * years + trend_results['intercept']
        ax1.plot(years, trend_line, '--', color='#1f77b4', 
                linewidth=2, label=f'Trend (R²={trend_results["r_squared"]:.3f})')
        
        ax1.set_xlabel('Year', fontweight='bold')
        ax1.set_ylabel('Soil Loss (t/ha/yr)', fontweight='bold')
        ax1.set_title('Mean Annual Soil Loss', fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Box plot distribution
        ax2 = axes[0, 1]
        box_data = [stats_df[stats_df['year'] == year]['mean'].values[0] 
                   for year in years]
        ax2.boxplot([box_data], vert=True, patch_artist=True,
                   boxprops=dict(facecolor='#ff7f0e', alpha=0.7))
        ax2.set_ylabel('Soil Loss (t/ha/yr)', fontweight='bold')
        ax2.set_title('Distribution Statistics', fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Plot 3: Year-to-year change
        ax3 = axes[1, 0]
        changes = stats_df['mean'].diff()
        ax3.bar(years[1:], changes[1:], color=['#2ca02c' if c < 0 else '#d62728' 
                                                for c in changes[1:]], alpha=0.7)
        ax3.axhline(0, color='black', linewidth=0.8)
        ax3.set_xlabel('Year', fontweight='bold')
        ax3.set_ylabel('Change from Previous Year (t/ha/yr)', fontweight='bold')
        ax3.set_title('Year-to-Year Changes', fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y')
        
        # Plot 4: Percentiles over time
        ax4 = axes[1, 1]
        ax4.fill_between(years, stats_df['p25'], stats_df['p75'], 
                         alpha=0.3, color='#1f77b4', label='IQR (25-75%)')
        ax4.plot(years, stats_df['median'], 'o-', color='#ff7f0e', 
                linewidth=2, markersize=6, label='Median')
        ax4.plot(years, stats_df['p90'], 's-', color='#d62728', 
                linewidth=1.5, markersize=5, label='90th percentile')
        ax4.set_xlabel('Year', fontweight='bold')
        ax4.set_ylabel('Soil Loss (t/ha/yr)', fontweight='bold')
        ax4.set_title('Percentile Trends', fontweight='bold')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        output_path = FIGURES_DIR / "temporal_analysis.png"
        plt.savefig(output_path, dpi=FIG_DPI, bbox_inches='tight')
        logger.info(f"   [SAVED] Temporal analysis saved: {output_path}")
        
        plt.close()
        
        # Figure 2: Change map visualization
        if (MAPS_DIR / f"soil_loss_change_{START_YEAR}_{END_YEAR}.tif").exists():
            with rasterio.open(MAPS_DIR / f"soil_loss_change_{START_YEAR}_{END_YEAR}.tif") as src:
                change_data = src.read(1)
            
            fig, ax = plt.subplots(figsize=(12, 10))
            
            change_masked = np.ma.masked_equal(change_data, NODATA_VALUE)
            
            im = ax.imshow(change_masked, cmap='RdYlGn_r', interpolation='bilinear',
                          vmin=-20, vmax=20)
            ax.set_title(f'Soil Loss Change ({END_YEAR} - {START_YEAR})', 
                        fontsize=14, fontweight='bold')
            ax.axis('off')
            
            cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label('Change (t/ha/yr)', rotation=270, labelpad=20)
            
            output_path2 = FIGURES_DIR / f"change_map_{START_YEAR}_{END_YEAR}.png"
            plt.savefig(output_path2, dpi=FIG_DPI, bbox_inches='tight')
            logger.info(f"   [SAVED] Change map saved: {output_path2}")
            
            plt.close()
        
        logger.info("   [OK] Visualizations created")
        
    except Exception as e:
        logger.warning(f"   [WARNING]  Visualization error: {e}")


def main(start_year=None, end_year=None):
    """Main execution function."""
    start_year = start_year or START_YEAR
    end_year = end_year or END_YEAR
    
    logger.info("="*80)
    logger.info("STEP 8: TEMPORAL ANALYSIS & VALIDATION")
    logger.info("="*80)
    logger.info(f"Period: {start_year}-{end_year}")
    
    try:
        # Load data
        soil_loss_data, meta = load_annual_soil_loss(start_year, end_year)
        
        if len(soil_loss_data) < 2:
            logger.error("[ERROR] Insufficient data for temporal analysis")
            return False
        
        # Calculate statistics
        stats_df = calculate_temporal_statistics(soil_loss_data, NODATA_VALUE)
        
        # Save temporal statistics
        stats_path = STATS_DIR / "temporal_statistics.csv"
        stats_df.to_csv(stats_path, index=False)
        logger.info(f"[SAVED] Temporal statistics saved: {stats_path}")
        
        # Trend analysis
        trend_results = detect_temporal_trends(stats_df)
        
        # Change detection
        change_map = create_change_map(soil_loss_data, start_year, end_year, 
                                      meta, NODATA_VALUE)
        
        # Validation
        validation_status = validate_against_literature(stats_df)
        
        # Visualizations
        visualize_temporal_analysis(stats_df, trend_results)
        
        # Summary report
        logger.info("="*80)
        logger.info("TEMPORAL ANALYSIS SUMMARY")
        logger.info("="*80)
        logger.info(f"Period: {start_year}-{end_year} ({len(soil_loss_data)} years)")
        logger.info(f"Mean soil loss: {stats_df['mean'].mean():.2f} t/ha/yr")
        logger.info(f"Trend: {trend_results['trend'].upper()}")
        logger.info(f"Change: {trend_results['change_pct']:+.2f}%")
        logger.info(f"Validation: {validation_status}")
        logger.info("="*80)
        
        logger.info("\n[OK] TEMPORAL ANALYSIS COMPLETED!")
        
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] TEMPORAL ANALYSIS FAILED: {e}")
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
