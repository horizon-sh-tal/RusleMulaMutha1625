#!/usr/bin/env python3
"""
RUSLE Master Execution Script
Runs complete soil erosion analysis for 2014-2024

Author: Bhavya Singh
Date: 17 November 2025

Usage:
    python run_rusle_analysis.py [--year YEAR] [--validate-only]
    
Examples:
    # Run full analysis (2014-2024)
    python run_rusle_analysis.py
    
    # Run for specific year
    python run_rusle_analysis.py --year 2020
    
    # Validation only
    python run_rusle_analysis.py --validate-only
"""

import sys
import argparse
from pathlib import Path
import logging
from datetime import datetime
import json

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent / 'scripts'))

from config import *

# Setup main logger
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(LOGS_DIR / f"rusle_master_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print project banner."""
    banner = """
    ╔════════════════════════════════════════════════════════════════╗
    ║                                                                ║
    ║           RUSLE SOIL EROSION ANALYSIS                         ║
    ║           Mula-Mutha Catchment, Pune                          ║
    ║           2014-2024 (11 Years)                                ║
    ║                                                                ║
    ║  Author: Bhavya Singh                                         ║
    ║  Institution: BVIEER, Bharati Vidyapeeth University           ║
    ║  Date: 17 November 2025                                       ║
    ║                                                                ║
    ╚════════════════════════════════════════════════════════════════╝
    """
    print(banner)
    logger.info(banner)


def validate_environment():
    """
    Validate that all required packages and data are available.
    
    Returns:
        bool: True if environment is valid
    """
    logger.info("="*80)
    logger.info("VALIDATING ENVIRONMENT")
    logger.info("="*80)
    
    all_ok = True
    
    # Check Python packages
    logger.info("Checking Python packages...")
    required_packages = [
        'numpy', 'pandas', 'geopandas', 'rasterio', 
        'matplotlib', 'scipy', 'ee', 'geemap'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"  ✅ {package}")
        except ImportError:
            logger.error(f"  ❌ {package} - NOT FOUND")
            all_ok = False
    
    # Check input files
    logger.info("\nChecking input files...")
    required_files = [
        CATCHMENT_SHP,
        DEM_FILE if DEM_FILE.exists() else DEM_BACKUP
    ]
    
    for filepath in required_files:
        if filepath.exists():
            logger.info(f"  ✅ {filepath.name}")
        else:
            logger.error(f"  ❌ {filepath.name} - NOT FOUND")
            all_ok = False
    
    # Check directories
    logger.info("\nChecking directories...")
    for directory in [OUTPUT_DIR, TEMP_DIR, MAPS_DIR, STATS_DIR, FIGURES_DIR]:
        if directory.exists():
            logger.info(f"  ✅ {directory}")
        else:
            logger.warning(f"  ⚠️  {directory} - Creating...")
            directory.mkdir(parents=True, exist_ok=True)
    
    # Check Google Earth Engine
    logger.info("\nChecking Google Earth Engine...")
    try:
        import ee
        ee.Initialize()
        logger.info("  ✅ Google Earth Engine authenticated")
    except Exception as e:
        logger.error(f"  ❌ Google Earth Engine - {e}")
        logger.error("     Run: earthengine authenticate")
        all_ok = False
    
    logger.info("\n" + "="*80)
    if all_ok:
        logger.info("✅ ENVIRONMENT VALIDATION PASSED")
    else:
        logger.error("❌ ENVIRONMENT VALIDATION FAILED")
    logger.info("="*80 + "\n")
    
    return all_ok


def run_step(step_number, step_name, script_name, **kwargs):
    """
    Run a processing step.
    
    Args:
        step_number: Step number
        step_name: Human-readable step name
        script_name: Script filename to execute
        **kwargs: Additional arguments to pass to script
        
    Returns:
        bool: True if step succeeded
    """
    logger.info("="*80)
    logger.info(f"STEP {step_number}: {step_name}")
    logger.info("="*80)
    
    script_path = SCRIPTS_DIR / script_name
    
    if not script_path.exists():
        logger.error(f"❌ Script not found: {script_path}")
        return False
    
    try:
        # Import and run the script's main function
        import importlib.util
        spec = importlib.util.spec_from_file_location("module", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Run main function
        if hasattr(module, 'main'):
            success = module.main(**kwargs)
            
            if success:
                logger.info(f"✅ STEP {step_number} COMPLETED: {step_name}")
            else:
                logger.error(f"❌ STEP {step_number} FAILED: {step_name}")
            
            return success
        else:
            logger.error(f"❌ Script has no main() function: {script_name}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error in {step_name}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def run_full_analysis(start_year=None, end_year=None):
    """
    Run complete RUSLE analysis.
    
    Args:
        start_year: Start year (default: from config)
        end_year: End year (default: from config)
        
    Returns:
        bool: True if analysis succeeded
    """
    start_year = start_year or START_YEAR
    end_year = end_year or END_YEAR
    
    logger.info(f"Running analysis for years {start_year}-{end_year}")
    
    steps = [
        (1, "Data Preparation & Validation", "01_data_preparation.py", {}),
        (2, "Topographic Factor (LS) Calculation", "02_calculate_ls_factor.py", {}),
        (3, "Soil Erodibility (K) Factor", "03_calculate_k_factor.py", {}),
        (4, "Rainfall Erosivity (R) Factor", "04_calculate_r_factor.py", 
         {"start_year": start_year, "end_year": end_year}),
        (5, "Cover Management (C) Factor", "05_calculate_c_factor.py",
         {"start_year": start_year, "end_year": end_year}),
        (6, "Support Practice (P) Factor", "06_calculate_p_factor.py",
         {"start_year": start_year, "end_year": end_year}),
        (7, "RUSLE Calculation & Classification", "07_calculate_rusle.py",
         {"start_year": start_year, "end_year": end_year}),
        (8, "Temporal Analysis & Validation", "08_temporal_analysis.py",
         {"start_year": start_year, "end_year": end_year}),
        (9, "Report Generation", "09_generate_report.py",
         {"start_year": start_year, "end_year": end_year}),
    ]
    
    results = {}
    overall_success = True
    
    for step_num, step_name, script_name, kwargs in steps:
        success = run_step(step_num, step_name, script_name, **kwargs)
        results[step_name] = success
        
        if not success:
            overall_success = False
            logger.error(f"❌ Stopping due to failure in: {step_name}")
            break
    
    # Save results
    results_file = OUTPUT_DIR / f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'start_year': start_year,
            'end_year': end_year,
            'overall_success': overall_success,
            'step_results': results
        }, f, indent=2)
    
    logger.info(f"\n💾 Results saved: {results_file}")
    
    return overall_success


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='RUSLE Soil Erosion Analysis for Mula-Mutha Catchment'
    )
    parser.add_argument(
        '--year', 
        type=int, 
        help='Analyze specific year only (2014-2024)'
    )
    parser.add_argument(
        '--start-year',
        type=int,
        default=START_YEAR,
        help=f'Start year (default: {START_YEAR})'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        default=END_YEAR,
        help=f'End year (default: {END_YEAR})'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate environment, do not run analysis'
    )
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip environment validation'
    )
    
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Validate environment
    if not args.skip_validation:
        if not validate_environment():
            logger.error("❌ Environment validation failed. Fix issues and try again.")
            return False
    
    if args.validate_only:
        logger.info("✅ Validation complete. Exiting.")
        return True
    
    # Determine year range
    if args.year:
        start_year = args.year
        end_year = args.year
    else:
        start_year = args.start_year
        end_year = args.end_year
    
    # Validate year range
    if start_year < 2014 or end_year > 2024:
        logger.error("❌ Year must be between 2014 and 2024")
        return False
    
    # Run analysis
    logger.info(f"\n🚀 Starting RUSLE analysis: {start_year}-{end_year}\n")
    
    start_time = datetime.now()
    success = run_full_analysis(start_year, end_year)
    end_time = datetime.now()
    
    duration = end_time - start_time
    
    # Final summary
    logger.info("\n" + "="*80)
    if success:
        logger.info("✅ ANALYSIS COMPLETED SUCCESSFULLY!")
    else:
        logger.info("❌ ANALYSIS FAILED!")
    logger.info("="*80)
    logger.info(f"⏱️  Duration: {duration}")
    logger.info(f"📂 Outputs: {OUTPUT_DIR}")
    logger.info(f"📊 Maps: {MAPS_DIR}")
    logger.info(f"📈 Statistics: {STATS_DIR}")
    logger.info(f"🖼️  Figures: {FIGURES_DIR}")
    logger.info(f"📝 Logs: {LOGS_DIR}")
    logger.info("="*80 + "\n")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
