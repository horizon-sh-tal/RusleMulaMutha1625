#!/usr/bin/env python3
"""
RUSLE Project 2016-2025: Environment & Data Validation Script
==============================================================

Purpose: Comprehensive validation before running RUSLE analysis
- Checks system environment (Python, packages, disk space)
- Validates input data (DEM, catchment shapefile)
- Verifies directory structure
- Tests critical dependencies (GEE, GDAL, etc.)
- Creates validation report

Run this FIRST when setting up the project on a new machine!

Author: RUSLE Team
Date: 2025-01-19
"""

import sys
import os
import platform
import subprocess
from pathlib import Path
import importlib
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Terminal colors for better readability
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def check_python_version():
    """Check if Python version is adequate"""
    print_header("1. PYTHON VERSION CHECK")
    
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    print_info(f"Python version: {version_str}")
    print_info(f"Python executable: {sys.executable}")
    
    if version.major >= 3 and version.minor >= 8:
        print_success(f"Python {version_str} is compatible (>= 3.8 required)")
        return True
    else:
        print_error(f"Python {version_str} is too old! Need Python >= 3.8")
        return False

def check_required_packages():
    """Check if all required Python packages are installed"""
    print_header("2. PYTHON PACKAGES CHECK")
    
    required_packages = {
        'numpy': 'numpy',
        'pandas': 'pandas',
        'geopandas': 'geopandas',
        'rasterio': 'rasterio',
        'matplotlib': 'matplotlib',
        'scipy': 'scipy',
        'ee': 'earthengine-api',
        'folium': 'folium',
        'plotly': 'plotly',
        'shapely': 'shapely',
        'pyproj': 'pyproj',
        'tqdm': 'tqdm',
        'requests': 'requests'
    }
    
    all_installed = True
    installed = []
    missing = []
    
    for module_name, package_name in required_packages.items():
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, '__version__', 'unknown')
            print_success(f"{package_name:20s} - version {version}")
            installed.append(package_name)
        except ImportError:
            print_error(f"{package_name:20s} - NOT INSTALLED")
            missing.append(package_name)
            all_installed = False
    
    print(f"\n{Colors.BOLD}Summary:{Colors.ENDC}")
    print(f"  Installed: {len(installed)}/{len(required_packages)}")
    
    if missing:
        print_error(f"Missing packages: {', '.join(missing)}")
        print_info("Install missing packages with:")
        print(f"  pip install {' '.join(missing)}")
    
    return all_installed

def check_system_resources():
    """Check system resources (disk space, memory)"""
    print_header("3. SYSTEM RESOURCES CHECK")
    
    # Check disk space
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        
        total_gb = total / (1024**3)
        used_gb = used / (1024**3)
        free_gb = free / (1024**3)
        
        print_info(f"Disk Space:")
        print(f"  Total: {total_gb:.2f} GB")
        print(f"  Used:  {used_gb:.2f} GB ({used/total*100:.1f}%)")
        print(f"  Free:  {free_gb:.2f} GB ({free/total*100:.1f}%)")
        
        if free_gb >= 10:
            print_success(f"Sufficient disk space ({free_gb:.2f} GB free, need ~10 GB)")
        else:
            print_warning(f"Low disk space! {free_gb:.2f} GB free, recommend >= 10 GB")
    except Exception as e:
        print_error(f"Could not check disk space: {e}")
    
    # Check RAM
    try:
        import psutil
        ram = psutil.virtual_memory()
        ram_total_gb = ram.total / (1024**3)
        ram_available_gb = ram.available / (1024**3)
        
        print_info(f"\nRAM:")
        print(f"  Total:     {ram_total_gb:.2f} GB")
        print(f"  Available: {ram_available_gb:.2f} GB ({ram.percent:.1f}% used)")
        
        if ram_total_gb >= 8:
            print_success(f"Sufficient RAM ({ram_total_gb:.2f} GB, recommend >= 8 GB)")
        else:
            print_warning(f"Low RAM! {ram_total_gb:.2f} GB, recommend >= 8 GB")
    except ImportError:
        print_warning("psutil not installed - cannot check RAM (optional)")
    except Exception as e:
        print_error(f"Could not check RAM: {e}")
    
    # Check CPU
    try:
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        print_info(f"\nCPU Cores: {cpu_count}")
        if cpu_count >= 4:
            print_success(f"Good CPU count ({cpu_count} cores)")
        else:
            print_info(f"CPU cores: {cpu_count} (more cores = faster processing)")
    except Exception as e:
        print_error(f"Could not check CPU: {e}")
    
    return True

def check_directory_structure():
    """Verify project directory structure exists"""
    print_header("4. DIRECTORY STRUCTURE CHECK")
    
    base_dir = Path(__file__).parent.parent
    
    required_dirs = {
        'catchment': 'Catchment shapefile directory',
        'data': 'Downloaded data storage',
        'temp': 'Temporary processing files',
        'temp/factors': 'RUSLE factor rasters',
        'outputs': 'Analysis results',
        'outputs/figures': 'Generated figures',
        'outputs/maps': 'Static maps',
        'outputs/web_maps': 'Interactive web maps',
        'outputs/statistics': 'Statistical outputs',
        'outputs/logs': 'Processing logs',
        'scripts': 'Python scripts'
    }
    
    all_exist = True
    
    for dir_path, description in required_dirs.items():
        full_path = base_dir / dir_path
        if full_path.exists():
            print_success(f"{dir_path:25s} - {description}")
        else:
            print_warning(f"{dir_path:25s} - MISSING, will create")
            try:
                full_path.mkdir(parents=True, exist_ok=True)
                print_info(f"  Created: {full_path}")
            except Exception as e:
                print_error(f"  Failed to create: {e}")
                all_exist = False
    
    return all_exist

def check_catchment_shapefile():
    """Validate catchment shapefile exists and is valid"""
    print_header("5. CATCHMENT SHAPEFILE VALIDATION")
    
    base_dir = Path(__file__).parent.parent
    catchment_dir = base_dir / 'catchment'
    
    # Look for shapefile
    shapefiles = list(catchment_dir.glob('*.shp'))
    
    if not shapefiles:
        print_error("No shapefile (.shp) found in catchment/ directory!")
        print_info("Expected: catchment/Mula_Mutha_Catchment.shp")
        return False
    
    shapefile = shapefiles[0]
    print_info(f"Found shapefile: {shapefile.name}")
    
    # Validate with geopandas
    try:
        import geopandas as gpd
        
        gdf = gpd.read_file(shapefile)
        
        print_info(f"Shapefile details:")
        print(f"  Features: {len(gdf)}")
        print(f"  CRS: {gdf.crs}")
        print(f"  Bounds: {gdf.total_bounds}")
        
        # Calculate area
        if gdf.crs and gdf.crs.is_geographic:
            # Reproject to projected CRS for area calculation
            gdf_proj = gdf.to_crs('EPSG:32643')  # WGS84 UTM 43N for Pune
            area_km2 = gdf_proj.geometry.area.sum() / 1_000_000
        else:
            area_km2 = gdf.geometry.area.sum() / 1_000_000
        
        print(f"  Area: {area_km2:,.2f} km²")
        
        # Validate geometry
        if gdf.geometry.is_valid.all():
            print_success("Shapefile geometry is valid")
        else:
            print_warning("Some geometries are invalid, may need repair")
        
        # Check if area is reasonable for Mula-Mutha
        if 5000 < area_km2 < 7000:
            print_success(f"Area {area_km2:,.2f} km² is within expected range (5,000-7,000 km²)")
        else:
            print_warning(f"Area {area_km2:,.2f} km² outside expected range - verify catchment")
        
        return True
        
    except ImportError:
        print_error("geopandas not installed - cannot validate shapefile")
        return False
    except Exception as e:
        print_error(f"Error reading shapefile: {e}")
        return False

def check_dem_file():
    """Validate DEM file exists and is valid"""
    print_header("6. DEM FILE VALIDATION")
    
    base_dir = Path(__file__).parent.parent
    dem_file = base_dir / 'temp' / 'dem_srtm_90m.tif'
    
    if not dem_file.exists():
        print_error(f"DEM file not found: {dem_file}")
        print_info("Expected location: temp/dem_srtm_90m.tif")
        print_info("Download instructions: See PROJECT_CONTINUATION_GUIDE.md")
        return False
    
    print_info(f"Found DEM: {dem_file.name}")
    print_info(f"Size: {dem_file.stat().st_size / (1024*1024):.2f} MB")
    
    # Validate with rasterio
    try:
        import rasterio
        import numpy as np
        
        with rasterio.open(dem_file) as src:
            print_info(f"DEM details:")
            print(f"  Dimensions: {src.width} × {src.height} pixels")
            print(f"  Resolution: {abs(src.res[0])*111320:.1f}m × {abs(src.res[1])*111320:.1f}m")
            print(f"  CRS: {src.crs}")
            print(f"  Bounds: {src.bounds}")
            
            # Read data
            dem_data = src.read(1)
            valid_data = dem_data[dem_data > 0]
            
            print(f"  Elevation range: {valid_data.min():.0f}m - {valid_data.max():.0f}m")
            print(f"  Mean elevation: {valid_data.mean():.1f}m")
            print(f"  Coverage: {len(valid_data)/dem_data.size*100:.1f}%")
            
            # Validate
            if src.crs and 'EPSG:4326' in str(src.crs):
                print_success("CRS is WGS84 (EPSG:4326) - correct!")
            else:
                print_warning(f"CRS is {src.crs}, expected EPSG:4326")
            
            if 80 <= abs(src.res[0])*111320 <= 100:
                print_success("Resolution ~90m - correct!")
            else:
                print_warning(f"Resolution {abs(src.res[0])*111320:.0f}m, expected ~90m")
            
            if 100 <= valid_data.max() <= 2000:
                print_success("Elevation range reasonable for Pune region")
            else:
                print_warning("Elevation range unusual - verify DEM")
            
            return True
            
    except ImportError:
        print_error("rasterio not installed - cannot validate DEM")
        return False
    except Exception as e:
        print_error(f"Error reading DEM: {e}")
        return False

def check_google_earth_engine():
    """Check Google Earth Engine authentication"""
    print_header("7. GOOGLE EARTH ENGINE (GEE) CHECK")
    
    try:
        import ee
        
        # Try to initialize
        try:
            ee.Initialize()
            print_success("Google Earth Engine is initialized and authenticated!")
            
            # Test with a simple query
            try:
                image = ee.Image('CGIAR/SRTM90_V4')
                info = image.getInfo()
                print_success("Successfully tested GEE connection")
                return True
            except Exception as e:
                print_warning(f"GEE authenticated but test query failed: {e}")
                print_info("This might be a temporary connection issue")
                return True
                
        except Exception as e:
            print_error("Google Earth Engine not authenticated!")
            print_info("Authenticate with: earthengine authenticate")
            print_info("Or in Python: import ee; ee.Authenticate()")
            return False
            
    except ImportError:
        print_error("earthengine-api not installed")
        print_info("Install with: pip install earthengine-api")
        return False

def check_config_files():
    """Check if configuration files exist"""
    print_header("8. CONFIGURATION FILES CHECK")
    
    base_dir = Path(__file__).parent.parent
    
    config_files = {
        'scripts/config.py': 'Main configuration file',
        'scripts/color_config.py': 'Color palette configuration',
        'requirements.txt': 'Python dependencies list',
        'README.md': 'Project documentation'
    }
    
    all_exist = True
    
    for file_path, description in config_files.items():
        full_path = base_dir / file_path
        if full_path.exists():
            size_kb = full_path.stat().st_size / 1024
            print_success(f"{file_path:30s} - {description} ({size_kb:.1f} KB)")
        else:
            print_warning(f"{file_path:30s} - MISSING")
            all_exist = False
    
    return all_exist

def generate_validation_report(results):
    """Generate a validation report file"""
    print_header("9. GENERATING VALIDATION REPORT")
    
    base_dir = Path(__file__).parent.parent
    report_file = base_dir / 'VALIDATION_REPORT.txt'
    
    try:
        with open(report_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("RUSLE PROJECT 2016-2025: ENVIRONMENT VALIDATION REPORT\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Date: {Path(__file__).stat().st_mtime}\n")
            f.write(f"Platform: {platform.system()} {platform.release()}\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"Working Directory: {base_dir}\n\n")
            
            f.write("VALIDATION RESULTS:\n")
            f.write("-" * 80 + "\n")
            
            for check_name, passed in results.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                f.write(f"{check_name:40s} {status}\n")
            
            f.write("\n" + "="*80 + "\n")
            
            passed_count = sum(results.values())
            total_count = len(results)
            
            f.write(f"\nOVERALL: {passed_count}/{total_count} checks passed\n")
            
            if all(results.values()):
                f.write("\n✅ SYSTEM IS READY FOR RUSLE ANALYSIS!\n")
            else:
                f.write("\n⚠️  SOME CHECKS FAILED - REVIEW REPORT ABOVE\n")
            
            f.write("\n" + "="*80 + "\n")
        
        print_success(f"Validation report saved to: {report_file}")
        return True
        
    except Exception as e:
        print_error(f"Could not generate report: {e}")
        return False

def main():
    """Main validation function"""
    
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "RUSLE PROJECT 2016-2025" + " "*35 + "║")
    print("║" + " "*15 + "Environment & Data Validation" + " "*34 + "║")
    print("╚" + "="*78 + "╝")
    print(f"{Colors.ENDC}\n")
    
    print_info("This script will validate your environment and data files")
    print_info("Run this FIRST when setting up the project on a new machine!\n")
    
    # Run all validation checks
    results = {}
    
    results['Python Version'] = check_python_version()
    results['Python Packages'] = check_required_packages()
    results['System Resources'] = check_system_resources()
    results['Directory Structure'] = check_directory_structure()
    results['Catchment Shapefile'] = check_catchment_shapefile()
    results['DEM File'] = check_dem_file()
    results['Google Earth Engine'] = check_google_earth_engine()
    results['Configuration Files'] = check_config_files()
    
    # Generate report
    generate_validation_report(results)
    
    # Final summary
    print_header("VALIDATION SUMMARY")
    
    passed_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n{Colors.BOLD}Results:{Colors.ENDC}")
    for check_name, passed in results.items():
        if passed:
            print_success(f"{check_name:30s} PASSED")
        else:
            print_error(f"{check_name:30s} FAILED")
    
    print(f"\n{Colors.BOLD}Overall: {passed_count}/{total_count} checks passed{Colors.ENDC}\n")
    
    if all(results.values()):
        print(f"{Colors.OKGREEN}{Colors.BOLD}")
        print("╔" + "="*78 + "╗")
        print("║" + " "*15 + "✅ SYSTEM IS READY FOR RUSLE ANALYSIS!" + " "*23 + "║")
        print("╚" + "="*78 + "╝")
        print(f"{Colors.ENDC}\n")
        print_info("Next steps:")
        print("  1. Run: scripts/02_calculate_k_factor.py")
        print("  2. Run: scripts/03_calculate_ls_factor.py")
        print("  3. Then proceed with year-by-year analysis (2016-2025)")
        return 0
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}")
        print("╔" + "="*78 + "╗")
        print("║" + " "*10 + "⚠️  VALIDATION FAILED - FIX ISSUES BEFORE PROCEEDING" + " "*16 + "║")
        print("╚" + "="*78 + "╝")
        print(f"{Colors.ENDC}\n")
        print_info("Fix the failed checks above and run this script again")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
