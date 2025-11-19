"""
Step 9: Generate Final Report
Creates comprehensive report with all results

Author: Bhavya Singh
Date: 17 November 2025

Generates:
- Summary statistics tables
- All visualizations
- Comprehensive markdown report
"""

import sys
sys.path.append('/home/ubuntuksh/Desktop/RUSLE/scripts')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import logging
from pathlib import Path
from datetime import datetime
from config import *

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(LOGS_DIR / "09_report_generation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_all_statistics():
    """Load all statistics files."""
    logger.info("Loading statistics files...")
    
    stats = {}
    
    # RUSLE annual statistics
    rusle_path = STATS_DIR / "rusle_annual_statistics.csv"
    if rusle_path.exists():
        stats['rusle'] = pd.read_csv(rusle_path)
        logger.info(f"   [OK] RUSLE statistics: {len(stats['rusle'])} years")
    else:
        logger.warning(f"   [WARNING]  RUSLE statistics not found")
    
    # Temporal statistics
    temp_path = STATS_DIR / "temporal_statistics.csv"
    if temp_path.exists():
        stats['temporal'] = pd.read_csv(temp_path)
        logger.info(f"   [OK] Temporal statistics: {len(stats['temporal'])} years")
    else:
        logger.warning(f"   [WARNING]  Temporal statistics not found")
    
    # Factor statistics
    for factor in ['r', 'k', 'c', 'p']:
        factor_path = STATS_DIR / f"{factor}_factor_annual_statistics.csv"
        if factor_path.exists():
            stats[f'{factor}_factor'] = pd.read_csv(factor_path)
            logger.info(f"   [OK] {factor.upper()}-factor statistics")
    
    return stats


def create_summary_table(stats_data):
    """Create summary table for all years."""
    logger.info("Creating summary table...")
    
    if 'rusle' not in stats_data:
        logger.error("   [ERROR] RUSLE statistics not available")
        return None
    
    df = stats_data['rusle'].copy()
    
    # Round values
    df = df.round({
        'mean': 2, 'median': 2, 'std': 2,
        'min': 2, 'max': 2, 'p90': 2, 'p95': 2
    })
    
    # Add erosion severity percentages
    if 'Slight' in df.columns:
        total_area = df[['Slight', 'Moderate', 'High', 'Very High', 'Severe']].sum(axis=1)
        for col in ['Slight', 'Moderate', 'High', 'Very High', 'Severe']:
            df[f'{col}_pct'] = (df[col] / total_area * 100).round(1)
    
    logger.info("   [OK] Summary table created")
    return df


def create_area_distribution_chart(stats_data):
    """Create stacked area chart of erosion classes over time."""
    logger.info("Creating area distribution chart...")
    
    try:
        if 'rusle' not in stats_data:
            return False
        
        df = stats_data['rusle']
        
        if 'Slight' not in df.columns:
            logger.warning("   [WARNING]  Erosion class areas not available")
            return False
        
        years = df['year'].values
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Prepare data for stacking
        classes = ['Slight', 'Moderate', 'High', 'Very High', 'Severe']
        colors = [EROSION_CLASSES[i+1]['color'] for i in range(5)]
        
        areas = [df[cls].values for cls in classes]
        
        ax.stackplot(years, *areas, labels=classes, colors=colors, alpha=0.8)
        
        ax.set_xlabel('Year', fontweight='bold', fontsize=12)
        ax.set_ylabel('Area (km²)', fontweight='bold', fontsize=12)
        ax.set_title('Erosion Severity Distribution Over Time', 
                    fontweight='bold', fontsize=14)
        ax.legend(loc='upper left', frameon=True, framealpha=0.9)
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        output_path = FIGURES_DIR / "erosion_area_distribution.png"
        plt.savefig(output_path, dpi=FIG_DPI, bbox_inches='tight')
        logger.info(f"   [SAVED] Area distribution chart saved: {output_path}")
        
        plt.close()
        return True
        
    except Exception as e:
        logger.warning(f"   [WARNING]  Chart creation failed: {e}")
        return False


def create_factor_correlation_plot(stats_data):
    """Create correlation matrix of RUSLE factors."""
    logger.info("Creating factor correlation plot...")
    
    try:
        # Collect mean values for each factor
        factor_means = {}
        
        for factor in ['r', 'c', 'p']:
            if f'{factor}_factor' in stats_data:
                df = stats_data[f'{factor}_factor']
                if f'{factor}_mean' in df.columns:
                    factor_means[f'{factor.upper()}-factor'] = df[f'{factor}_mean'].values
        
        if len(factor_means) < 2:
            logger.warning("   [WARNING]  Insufficient factor data for correlation")
            return False
        
        # Create correlation matrix
        corr_df = pd.DataFrame(factor_means)
        corr = corr_df.corr()
        
        fig, ax = plt.subplots(figsize=(8, 6))
        
        import seaborn as sns
        sns.heatmap(corr, annot=True, fmt='.3f', cmap='coolwarm', 
                   center=0, vmin=-1, vmax=1, ax=ax,
                   square=True, linewidths=1)
        
        ax.set_title('RUSLE Factor Correlation Matrix', 
                    fontweight='bold', fontsize=14)
        
        plt.tight_layout()
        
        output_path = FIGURES_DIR / "factor_correlation.png"
        plt.savefig(output_path, dpi=FIG_DPI, bbox_inches='tight')
        logger.info(f"   [SAVED] Correlation plot saved: {output_path}")
        
        plt.close()
        return True
        
    except Exception as e:
        logger.warning(f"   [WARNING]  Correlation plot failed: {e}")
        return False


def generate_markdown_report(stats_data, summary_table):
    """Generate comprehensive markdown report."""
    logger.info("Generating markdown report...")
    
    report_path = BASE_DIR / "RUSLE_ANALYSIS_REPORT.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        # Header
        f.write("# RUSLE Soil Erosion Assessment Report\n\n")
        f.write(f"**Mula-Mutha Catchment, Pune**\n\n")
        f.write(f"**Analysis Period:** {START_YEAR}-{END_YEAR}\n\n")
        f.write(f"**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        # Executive Summary
        f.write("## Executive Summary\n\n")
        
        if 'rusle' in stats_data:
            df = stats_data['rusle']
            overall_mean = df['mean'].mean()
            overall_max = df['max'].max()
            
            f.write(f"- **Study Area:** Mula-Mutha catchment (~600 km²)\n")
            f.write(f"- **Analysis Years:** {len(df)} years ({START_YEAR}-{END_YEAR})\n")
            f.write(f"- **Mean Annual Soil Loss:** {overall_mean:.2f} t/ha/yr\n")
            f.write(f"- **Maximum Soil Loss:** {overall_max:.2f} t/ha/yr\n")
            f.write(f"- **Spatial Resolution:** {TARGET_RESOLUTION}m\n")
            f.write(f"- **Coordinate System:** {TARGET_CRS}\n\n")
        
        # Methodology
        f.write("## Methodology\n\n")
        f.write("### RUSLE Equation\n\n")
        f.write("```\nA = R × K × LS × C × P\n```\n\n")
        f.write("Where:\n")
        f.write("- **A** = Annual soil loss (t/ha/yr)\n")
        f.write("- **R** = Rainfall erosivity factor (MJ mm/ha/h/yr)\n")
        f.write("- **K** = Soil erodibility factor (t h/MJ/mm)\n")
        f.write("- **LS** = Topographic factor (dimensionless)\n")
        f.write("- **C** = Cover management factor (dimensionless)\n")
        f.write("- **P** = Support practice factor (dimensionless)\n\n")
        
        # Data Sources
        f.write("### Data Sources\n\n")
        f.write("| Factor | Data Source | Resolution | Period |\n")
        f.write("|--------|-------------|------------|--------|\n")
        f.write("| R | CHIRPS Daily Precipitation | 5km | 2014-2024 |\n")
        f.write("| K | OpenLandMap Soil Texture | 250m | 2018 |\n")
        f.write("| LS | SRTM DEM | 90m | 2000 |\n")
        f.write("| C | Sentinel-2/Landsat 8 NDVI | 10-30m | 2014-2024 |\n")
        f.write("| P | Dynamic World Land Cover | 10m | 2015-2024 |\n\n")
        
        # Results
        f.write("## Results\n\n")
        
        f.write("### Annual Statistics\n\n")
        if summary_table is not None:
            # Create formatted table
            f.write("| Year | Mean | Median | Std Dev | Min | Max | P90 | P95 |\n")
            f.write("|------|------|--------|---------|-----|-----|-----|-----|\n")
            
            for _, row in summary_table.iterrows():
                f.write(f"| {int(row['year'])} | ")
                f.write(f"{row['mean']:.2f} | {row['median']:.2f} | {row['std']:.2f} | ")
                f.write(f"{row['min']:.2f} | {row['max']:.2f} | ")
                f.write(f"{row['p90']:.2f} | {row['p95']:.2f} |\n")
            
            f.write("\n*All values in t/ha/yr*\n\n")
        
        # Erosion Classification
        f.write("### Erosion Severity Classification\n\n")
        f.write("| Class | Range (t/ha/yr) | Severity |\n")
        f.write("|-------|-----------------|----------|\n")
        for i in range(1, 6):
            info = EROSION_CLASSES[i]
            lower, upper = info['range']
            f.write(f"| {i} | {lower}-{upper if upper < 1000 else 'inf'} | {info['label']} |\n")
        f.write("\n")
        
        # Area distribution
        if summary_table is not None and 'Slight_pct' in summary_table.columns:
            f.write("### Area Distribution by Severity Class\n\n")
            f.write("| Year | Slight | Moderate | High | Very High | Severe |\n")
            f.write("|------|--------|----------|------|-----------|--------|\n")
            
            for _, row in summary_table.iterrows():
                f.write(f"| {int(row['year'])} | ")
                f.write(f"{row['Slight_pct']:.1f}% | {row['Moderate_pct']:.1f}% | ")
                f.write(f"{row['High_pct']:.1f}% | {row['Very High_pct']:.1f}% | ")
                f.write(f"{row['Severe_pct']:.1f}% |\n")
            f.write("\n")
        
        # Visualizations
        f.write("## Visualizations\n\n")
        
        # Check for figures
        figures = [
            ("temporal_analysis.png", "Temporal Analysis"),
            ("erosion_area_distribution.png", "Area Distribution"),
            (f"change_map_{START_YEAR}_{END_YEAR}.png", "Change Detection"),
            ("factor_correlation.png", "Factor Correlations")
        ]
        
        for filename, caption in figures:
            fig_path = FIGURES_DIR / filename
            if fig_path.exists():
                f.write(f"### {caption}\n\n")
                f.write(f"![{caption}](outputs/figures/{filename})\n\n")
        
        # Validation
        f.write("## Validation\n\n")
        f.write("### Literature Comparison\n\n")
        f.write("Expected range for similar catchments in Western Ghats: **8-25 t/ha/yr**\n\n")
        
        if 'rusle' in stats_data:
            overall_mean = stats_data['rusle']['mean'].mean()
            if 8 <= overall_mean <= 25:
                f.write(f"[OK] **PASSED** - Mean soil loss ({overall_mean:.2f} t/ha/yr) within literature range\n\n")
            else:
                f.write(f"[WARNING] **REVIEW** - Mean soil loss ({overall_mean:.2f} t/ha/yr) outside literature range\n\n")
        
        # Outputs
        f.write("## Outputs\n\n")
        f.write("### Generated Files\n\n")
        
        f.write("**Maps:**\n")
        f.write(f"- Annual soil loss maps: `outputs/maps/soil_loss_YYYY.tif` ({END_YEAR-START_YEAR+1} files)\n")
        f.write(f"- Erosion classification maps: `outputs/maps/erosion_class_YYYY.tif` ({END_YEAR-START_YEAR+1} files)\n")
        f.write("- Change detection map: `outputs/maps/soil_loss_change_*.tif`\n\n")
        
        f.write("**Statistics:**\n")
        f.write("- Annual RUSLE statistics: `outputs/statistics/rusle_annual_statistics.csv`\n")
        f.write("- Temporal statistics: `outputs/statistics/temporal_statistics.csv`\n")
        f.write("- Factor statistics: `outputs/statistics/*_factor_annual_statistics.csv`\n\n")
        
        f.write("**Visualizations:**\n")
        f.write("- All figures: `outputs/figures/*.png`\n\n")
        
        # Conclusions
        f.write("## Conclusions\n\n")
        
        if 'rusle' in stats_data:
            df = stats_data['rusle']
            
            # Calculate trends only if we have multiple years
            available_years = sorted(df['year'].unique())
            if len(available_years) >= 2:
                first_year_mean = df[df['year'] == available_years[0]]['mean'].values[0]
                last_year_mean = df[df['year'] == available_years[-1]]['mean'].values[0]
                change_pct = ((last_year_mean - first_year_mean) / first_year_mean) * 100
                
                f.write(f"1. **Soil Loss Magnitude:** Mean annual soil loss of {df['mean'].mean():.2f} t/ha/yr "
                       f"indicates {'moderate' if df['mean'].mean() < 15 else 'high'} erosion risk.\n\n")
                
                f.write(f"2. **Temporal Trends:** Soil loss has "
                       f"{'increased' if change_pct > 0 else 'decreased'} by {abs(change_pct):.1f}% "
                       f"from {available_years[0]} to {available_years[-1]}.\n\n")
            else:
                # Single year analysis
                year_mean = df['mean'].values[0]
                f.write(f"1. **Soil Loss Magnitude (Year {available_years[0]}):** Mean soil loss of {year_mean:.2f} t/ha/yr "
                       f"indicates {'slight' if year_mean < 5 else 'moderate' if year_mean < 15 else 'high'} erosion risk.\n\n")
            
            if 'Severe_pct' in summary_table.columns:
                severe_avg = summary_table['Severe_pct'].mean()
                f.write(f"3. **Severe Erosion:** {severe_avg:.1f}% of the catchment area experiences "
                       f"severe erosion (>40 t/ha/yr) on average.\n\n")
        
        f.write("4. **Data Quality:** All factor calculations include comprehensive validation "
               "and error checking.\n\n")
        
        # Recommendations
        f.write("## Recommendations\n\n")
        f.write("1. **Priority Areas:** Focus conservation efforts on areas classified as 'Very High' "
               "and 'Severe' erosion.\n\n")
        f.write("2. **Conservation Practices:** Implement terracing and contour farming on steep slopes "
               "in agricultural areas.\n\n")
        f.write("3. **Vegetation Cover:** Increase vegetation cover in areas with high C-factor values "
               "(low vegetation).\n\n")
        f.write("4. **Monitoring:** Continue annual monitoring to track effectiveness of conservation "
               "measures.\n\n")
        
        # References
        f.write("## References\n\n")
        f.write("- Wischmeier, W.H., Smith, D.D. (1978). Predicting Rainfall Erosion Losses.\n")
        f.write("- Renard, K.G., et al. (1997). Predicting Soil Erosion by Water: A Guide to "
               "Conservation Planning with the Revised Universal Soil Loss Equation (RUSLE).\n")
        f.write("- CHIRPS: Climate Hazards Group InfraRed Precipitation with Station data\n")
        f.write("- OpenLandMap: Global soil property maps\n")
        f.write("- Google Dynamic World: Near real-time land cover classification\n\n")
        
        f.write("---\n\n")
        f.write(f"*Report generated by RUSLE Analysis Pipeline v1.0*\n")
    
    logger.info(f"   [SAVED] Report saved: {report_path}")
    return report_path


def main():
    """Main execution function."""
    logger.info("="*80)
    logger.info("STEP 9: REPORT GENERATION")
    logger.info("="*80)
    
    try:
        # Load all statistics
        stats_data = load_all_statistics()
        
        if len(stats_data) == 0:
            logger.error("[ERROR] No statistics files found")
            return False
        
        # Create summary table
        summary_table = create_summary_table(stats_data)
        
        # Create visualizations
        create_area_distribution_chart(stats_data)
        create_factor_correlation_plot(stats_data)
        
        # Generate markdown report
        report_path = generate_markdown_report(stats_data, summary_table)
        
        logger.info("="*80)
        logger.info("[OK] REPORT GENERATION COMPLETED!")
        logger.info("="*80)
        logger.info(f"\n📄 Final Report: {report_path}")
        logger.info(f"[CHART] All figures: {FIGURES_DIR}/")
        logger.info(f"📈 All statistics: {STATS_DIR}/")
        logger.info(f"[MAP]  All maps: {MAPS_DIR}/")
        
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] REPORT GENERATION FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
