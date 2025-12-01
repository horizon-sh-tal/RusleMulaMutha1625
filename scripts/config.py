"""
RUSLE Implementation - Configuration File
Mula-Mutha Catchment (2016-2025)

Author: Bhavya Singh
Date: 19 November 2025
Updated: Changed from 2014-2024 to 2016-2025
         Using SRTM 90m DEM from Google Earth Engine
"""

import os
from pathlib import Path
import numpy as np

# ============================================================================
# PROJECT PATHS
# ============================================================================
# Base directory - PORTABLE: works on any machine, any user
# Path(__file__).parent gets the 'scripts' directory
# .parent again gets the project root directory
BASE_DIR = Path(__file__).parent.parent

# Input data directories
CATCHMENT_DIR = BASE_DIR / 'catchment'
DATA_DIR = BASE_DIR / "data"
SCRIPTS_DIR = BASE_DIR / "scripts"

# Output directories
OUTPUT_DIR = BASE_DIR / "outputs"
MAPS_DIR = OUTPUT_DIR / "maps"
STATS_DIR = OUTPUT_DIR / "statistics"
FIGURES_DIR = OUTPUT_DIR / "figures"
LOGS_DIR = OUTPUT_DIR / "logs"

# Intermediate data (for debugging)
TEMP_DIR = BASE_DIR / "temp"
FACTORS_DIR = TEMP_DIR / "factors"

# Create directories if they don't exist
for directory in [DATA_DIR, OUTPUT_DIR, MAPS_DIR, STATS_DIR, 
                  FIGURES_DIR, LOGS_DIR, TEMP_DIR, FACTORS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# AOI directory and preferred AOI raster names (added)
AOI_DIR = TEMP_DIR / "aoi"
AOI_MASK_RASTER_CANDIDATES = [
    AOI_DIR / "aoi_mask_90m.tif",
    AOI_DIR / "aoi_mask.tif",
]

# ============================================================================
# INPUT FILES
# ============================================================================
# Catchment boundary (AOI)
CATCHMENT_SHP = CATCHMENT_DIR / "Mula_Mutha_Catchment.shp"

# DEM Configuration - Download from Google Earth Engine
DEM_GEE_ASSET = "CGIAR/SRTM90_V4"  # SRTM 90m Digital Elevation Model
DEM_FILE = TEMP_DIR / "dem_srtm_90m.tif"  # Downloaded DEM will be saved here

# --- ADDED: alias for scripts that expect DEM_PATH override support ---
DEM_PATH = DEM_FILE  # (added) keep both names consistent for all scripts

# ============================================================================
# TEMPORAL PARAMETERS
# ============================================================================
START_YEAR = 2016
END_YEAR = 2025
YEARS = list(range(START_YEAR, END_YEAR + 1))
NUM_YEARS = len(YEARS)

# ============================================================================
# SPATIAL PARAMETERS
# ============================================================================
# Target Coordinate Reference System
TARGET_CRS = "EPSG:4326"  # WGS 84

# Target spatial resolution (meters)
TARGET_RESOLUTION = 90

# Resampling method
RESAMPLING_METHOD = "bilinear"  # for continuous data

# ============================================================================
# RUSLE FACTOR PARAMETERS
# ============================================================================
# R-Factor (Rainfall Erosivity)
R_FORMULA = lambda P: 79 + 0.363 * P  # P = annual precipitation (mm)

# --- ADDED: parameters used by scripts that apply R = a * P^b ---
# Calibrated so that at basin mean P (from your 2016–2025 prep stats)
# the power-law equals the classic linear 79 + 0.363*P.
# Basin mean P ≈ 1214.564 mm ⇒ a = 79/P + 0.363 ≈ 0.428044, b = 1.0
R_COEFF_A = 0.428044
R_COEFF_B = 1.0
R_FORMULA_NAME = "PowerLaw_R=a*P^b (calibrated to 79+0.363P at basin mean)"
R_OUTPUT_UNIT = "MJ·mm·ha⁻¹·h⁻¹·yr⁻¹ (relative-scaled)"

# Expected rainfall range for validation (mm/year)
RAINFALL_MIN = 500
RAINFALL_MAX = 2500

# K-Factor (Soil Erodibility) - Lookup table
# Based on OpenLandMap USDA Soil Texture Classification
SOIL_K_VALUES = {
    1: 0.0053,   # Clay
    2: 0.0170,   # Silty Clay
    3: 0.0280,   # Silty Clay Loam
    4: 0.0280,   # Sandy Clay
    5: 0.0340,   # Sandy Clay Loam
    6: 0.0400,   # Clay Loam
    7: 0.0430,   # Silt Loam
    8: 0.0450,   # Loam
    9: 0.0450,   # Silt
    10: 0.0170,  # Sandy Loam
    11: 0.0053,  # Loamy Sand
    12: 0.0053,  # Sand
}

# LS-Factor (Topographic) - Parameters
SLOPE_LENGTH = 500  # meters (assumed constant for basin)
LS_CELL_SIZE = 100  # normalization constant

# C-Factor (Cover Management) - NDVI-based
C_FORMULA = lambda ndvi: np.exp(-2 * ndvi / (1 - ndvi + 1e-6))

# NDVI valid range
NDVI_MIN = -0.1
NDVI_MAX = 0.9

# P-Factor (Support Practice) - Slope-based lookup
# Returns P-value based on slope percentage
def get_p_factor(slope_pct, landcover_class):
    """
    Calculate P-factor based on slope and land cover.
    
    Args:
        slope_pct: Slope in percentage
        landcover_class: Land cover type (from Dynamic World)
            0: Water
            1: Trees
            2: Grass
            3: Flooded vegetation
            4: Crops
            5: Shrub/scrub
            6: Built
            7: Bare
            8: Snow/ice
    
    Returns:
        P-factor value (0.1 to 1.0)
    """
    # For cropland (class 4), apply slope-based P
    if landcover_class == 4:
        if slope_pct < 5:
            return 0.10  # Well-terraced
        elif slope_pct < 10:
            return 0.30  # Some terracing
        elif slope_pct < 20:
            return 0.50  # Minimal conservation
        else:
            return 1.00  # No conservation (too steep)
    else:
        # For non-agricultural land, P = 1.0
        return 1.0

# ============================================================================
# GOOGLE EARTH ENGINE DATASETS
# ============================================================================
# Rainfall data
GEE_CHIRPS = "UCSB-CHG/CHIRPS/DAILY"
CHIRPS_BAND = "precipitation"

# Soil erodibility
GEE_SOIL = "OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02"
SOIL_BAND = "b0"  # 0-30cm depth

# NDVI / Land Cover (Sentinel-2 based)
GEE_DYNAMIC_WORLD = "GOOGLE/DYNAMICWORLD/V1"
DW_NDVI_BAND = "label"  # Land cover classification
DW_START_DATE = "2015-06-23"  # Sentinel-2 availability

# Alternative for 2014: Landsat 8
GEE_LANDSAT8 = "LANDSAT/LC08/C02/T1_L2"
L8_START_DATE = "2013-04-11"

# ============================================================================
# EROSION CLASSIFICATION
# ============================================================================
# Soil loss severity classes (t/ha/yr) - Updated Soil Degradation Colors
EROSION_CLASSES = {
    1: {"range": (0, 5), "label": "Very Low Degradation", "color": "#006837"},      # Dark Green
    2: {"range": (5, 10), "label": "Low Degradation", "color": "#7CB342"},          # Light Green
    3: {"range": (10, 20), "label": "Moderate Degradation", "color": "#FFEB3B"},    # Yellow
    4: {"range": (20, 40), "label": "High Degradation", "color": "#FF9800"},        # Orange
    5: {"range": (40, float('inf')), "label": "Very High Degradation", "color": "#D32F2F"},  # Red
}

# ============================================================================
# VALIDATION THRESHOLDS
# ============================================================================
# Expected soil loss range for Western Ghats (t/ha/yr)
SOIL_LOSS_MIN_EXPECTED = 5
SOIL_LOSS_MAX_EXPECTED = 30
SOIL_LOSS_ABSOLUTE_MAX = 200  # Flag if exceeded

# Factor ranges for validation
FACTOR_RANGES = {
    "R": (200, 1200),      # MJ·mm·ha⁻¹·h⁻¹·yr⁻¹
    "K": (0.005, 0.07),    # t·h·MJ⁻¹·mm⁻¹
    "LS": (0, 50),         # dimensionless
    "C": (0, 1),           # dimensionless
    "P": (0.1, 1.0),       # dimensionless
}

# ============================================================================
# VISUALIZATION SETTINGS
# ============================================================================
# Color ramps
CMAP_SOIL_LOSS = "YlOrRd"  # Yellow-Orange-Red
CMAP_NDVI = "RdYlGn"       # Red-Yellow-Green
CMAP_SLOPE = "terrain"     # Terrain colors

# Figure settings
FIG_DPI = 300
FIG_SIZE = (12, 10)

# ============================================================================
# PROCESSING FLAGS
# ============================================================================
# Enable/disable processing steps (for debugging)
PROCESS_DEM = True
PROCESS_RAINFALL = True
PROCESS_SOIL = True
PROCESS_NDVI = True
PROCESS_LANDCOVER = True

# Verbose logging
VERBOSE = True

# Save intermediate outputs
SAVE_INTERMEDIATES = True

# ============================================================================
# COLOR CONFIGURATION (Standardized)
# ============================================================================
# Import standardized color palette for soil erosion visualization
try:
    from color_config import (
        EROSION_COLORS,
        EROSION_PALETTE,
        EROSION_CATEGORIES,
        EROSION_THRESHOLDS,
        THRESHOLD_VALUES,
        classify_erosion,
        get_erosion_cmap,
        PLOTLY_EROSION_SCALE,
        LEGEND_CONFIG,
        HTML_LEGEND
    )
    print("[OK] Standardized color configuration loaded")
except ImportError:
    # Fallback if color_config.py not available
    EROSION_PALETTE = ['#006837', '#7CB342', '#FFEB3B', '#FF9800', '#D32F2F']
    EROSION_CATEGORIES = ['Very Low', 'Low', 'Moderate', 'High', 'Very High']
    THRESHOLD_VALUES = [0, 5, 10, 20, 40]
    print("[WARNING] Using fallback color configuration")

# ============================================================================
# ERROR HANDLING
# ============================================================================
# Maximum retries for GEE downloads
GEE_MAX_RETRIES = 3

# Timeout for GEE operations (seconds)
GEE_TIMEOUT = 600

# NoData value
NODATA_VALUE = -9999

# ============================================================================
# METADATA
# ============================================================================
PROJECT_NAME = "RUSLE Mula-Mutha Catchment Analysis"
AUTHOR = "Bhavya Singh"
INSTITUTION = "BVIEER, Bharati Vidyapeeth University"
VERSION = "1.0"
LAST_UPDATED = "2025-11-17"

# ============================================================================
# LOGGING FORMAT
# ============================================================================
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

print(f"[OK] Configuration loaded successfully!")
print(f"Analysis period: {START_YEAR}-{END_YEAR} ({NUM_YEARS} years)")
print(f"Output directory: {OUTPUT_DIR}")
print(f"Target CRS: {TARGET_CRS}")
print(f"Target resolution: {TARGET_RESOLUTION}m")
