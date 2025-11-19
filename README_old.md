# RUSLE Soil Erosion Analysis - Mula-Mutha Catchment# RUSLE Soil Erosion Analysis - Mula-Mutha Catchment



## Overview## Overview



This project analyzes soil erosion in the Mula-Mutha river catchment (Pune, India) using the **Revised Universal Soil Loss Equation (RUSLE)** with 11 years of real satellite data (2014-2024). The analysis combines remote sensing, GIS, and Python automation to assess erosion risk and identify conservation priorities.This project analyzes soil erosion in the Mula-Mutha river catchment (Pune, India) using the **Revised Universal Soil Loss Equation (RUSLE)** with 11 years of real satellite data (2014-2024). The analysis combines remote sensing, GIS, and Python automation to assess erosion risk and identify conservation priorities.



## What This Project Does## What This Project Does



**Calculates soil erosion** using the RUSLE equation: **A = R × K × LS × C × P****Calculates soil erosion** using the RUSLE equation: **A = R × K × LS × C × P**



Where:Where:

- **R**: Rainfall erosivity (from CHIRPS precipitation data)- **R**: Rainfall erosivity (from CHIRPS precipitation data)

- **K**: Soil erodibility (from OpenLandMap soil texture)- **K**: Soil erodibility (from OpenLandMap soil texture)

- **LS**: Topographic factor (from DEM - slope length and steepness)- **LS**: Topographic factor (from DEM - slope length and steepness)

- **C**: Vegetation cover factor (from Sentinel-2/Landsat 8 NDVI)- **C**: Vegetation cover factor (from Sentinel-2/Landsat 8 NDVI)

- **P**: Conservation practice factor (from Dynamic World land cover)- **P**: Conservation practice factor (from Dynamic World land cover)



**Analyzes temporal trends** to detect how erosion patterns changed over 11 years**Analyzes temporal trends** to detect how erosion patterns changed over 11 years



**Generates visualizations** including:**Generates visualizations** including:

- 11 annual soil erosion risk maps (GeoTIFF format)- 11 annual soil erosion risk maps (GeoTIFF format)

- Interactive web dashboard with maps, statistics, and charts- Interactive web dashboard with maps, statistics, and charts

- Statistical reports and trend analysis- Statistical reports and trend analysis



## Key Results## Key Results



- **Study Area**: Mula-Mutha catchment, Pune - 5,832 km²- **Study Area**: Mula-Mutha catchment, Pune - 5,832 km²

- **Analysis Period**: 2014-2024 (11 years of real satellite data)- **Analysis Period**: 2014-2024 (11 years of real satellite data)

- **Mean Soil Loss**: 643 t/ha/yr (median: 35.3 t/ha/yr)- **Mean Soil Loss**: 643 t/ha/yr (median: 35.3 t/ha/yr)

- **Erosion Trend**: **49% decrease** from 2014 to 2024- **Erosion Trend**: **49% decrease** from 2014 to 2024

- **Improvement**: 81.4% of catchment area shows reduced erosion- **Improvement**: 81.4% of catchment area shows reduced erosion

- **Risk Level**: 45% of area classified as severe erosion (>40 t/ha/yr)- **Risk Level**: 45% of area classified as severe erosion (>40 t/ha/yr)



## Approach & Methodology## Approach & Methodology



### 1. Data Acquisition (Google Earth Engine)### 1. Data Acquisition (Google Earth Engine)

- Download multi-year satellite datasets automatically- Download multi-year satellite datasets automatically

- Resample all data to 90m resolution to stay within GEE limits- Resample all data to 90m resolution to stay within GEE limits

- Handle NoData values properly during processing- Handle NoData values properly during processing



### 2. RUSLE Factor Calculation### 2. RUSLE Factor Calculation

Each factor is calculated following standard RUSLE methodology:Each factor is calculated following standard RUSLE methodology:

- **R-factor**: Derived from annual precipitation using established equations- **R-factor**: Derived from annual precipitation using established equations

- **K-factor**: Mapped from soil texture using USDA lookup tables- **K-factor**: Mapped from soil texture using USDA lookup tables

- **LS-factor**: Calculated from slope and slope length using DEM- **LS-factor**: Calculated from slope and slope length using DEM

- **C-factor**: Computed from NDVI using exponential relationship- **C-factor**: Computed from NDVI using exponential relationship

- **P-factor**: Assigned based on land cover and slope classes- **P-factor**: Assigned based on land cover and slope classes



### 3. Annual Soil Loss Estimation### 3. Annual Soil Loss Estimation

- Multiply all 5 factors for each year (2014-2024)- Multiply all 5 factors for each year (2014-2024)

- Generate 11 annual soil loss maps in t/ha/yr- Generate 11 annual soil loss maps in t/ha/yr

- Classify erosion severity: Slight, Moderate, High, Very High, Severe- Classify erosion severity: Slight, Moderate, High, Very High, Severe



### 4. Temporal Trend Analysis### 4. Temporal Trend Analysis

- Calculate year-to-year changes in erosion- Calculate year-to-year changes in erosion

- Detect spatial patterns of increase/decrease- Detect spatial patterns of increase/decrease

- Generate change maps and statistical summaries- Generate change maps and statistical summaries



### 5. Visualization & Dashboard### 5. Visualization & Dashboard

- Create web-friendly map images from GeoTIFF files- Create web-friendly map images from GeoTIFF files

- Build interactive HTML dashboard with Plotly.js- Build interactive HTML dashboard with Plotly.js

- Display maps, statistics, and charts for all years- Display maps, statistics, and charts for all years



## Project Structure## Project Structure



``````

RUSLE/

├── catchment/                      # Input data```

│   ├── Mula_Mutha_Catchment.shp    # Catchment boundary shapefileRUSLE/

│   └── DEM_PUNE_merged.tif         # Digital Elevation Model├── catchment/              # Catchment boundary shapefile and DEM

│├── scripts/                # Python scripts (01-09)

├── scripts/                        # Processing scripts (run in order)│   ├── 01_data_preparation.py

│   ├── 01_data_preparation.py      # Load DEM and boundary│   ├── 02_calculate_ls_factor.py

│   ├── 02_calculate_ls_factor.py   # Calculate topographic factor│   ├── 03_calculate_k_factor.py

│   ├── 03_calculate_k_factor.py    # Calculate soil erodibility│   ├── 04_calculate_r_factor.py

│   ├── 04_calculate_r_factor.py    # Calculate rainfall erosivity (11 years)│   ├── 05_calculate_c_factor.py

│   ├── 05_calculate_c_factor.py    # Calculate vegetation cover (11 years)│   ├── 06_calculate_p_factor.py

│   ├── 06_calculate_p_factor.py    # Calculate conservation practice (11 years)│   ├── 07_calculate_rusle.py

│   ├── 07_calculate_rusle.py       # Calculate soil loss (11 maps)│   ├── 08_temporal_analysis.py

│   ├── 08_temporal_analysis.py     # Analyze trends over time│   └── 09_generate_report.py

│   └── 09_generate_report.py       # Generate statistics report├── outputs/                # Results

││   ├── maps/               # GeoTIFF soil loss maps (2014-2024)

├── outputs/                        # All results│   ├── statistics/         # CSV files with annual statistics

│   ├── maps/                       # GeoTIFF files (23 total)│   └── figures/            # PNG charts and visualizations

│   │   ├── soil_loss_2014.tif      # Annual soil loss maps├── RUSLE_Dashboard.html    # Interactive dashboard (open in browser)

│   │   ├── ...├── README.md               # This file

│   │   └── soil_loss_2024.tif└── RUN_INSTRUCTIONS.md     # Step-by-step execution guide

│   ├── web_maps/                   # PNG images for dashboard (11 total)```

│   │   ├── soil_loss_2014.png

│   │   ├── ...## Quick Start

│   │   └── soil_loss_2024.png

│   ├── statistics/                 # CSV files with annual dataSee **RUN_INSTRUCTIONS.md** for detailed setup and execution steps.

│   │   ├── rusle_annual_statistics.csv

│   │   ├── r_factor_annual_statistics.csv## Results

│   │   ├── c_factor_annual_statistics.csv

│   │   ├── p_factor_annual_statistics.csv- **Dashboard**: Open `RUSLE_Dashboard.html` in a web browser to explore results interactively

│   │   └── temporal_statistics.csv- **Maps**: View `outputs/maps/soil_loss_YYYY.tif` in QGIS or ArcGIS

│   └── figures/                    # PNG charts and visualizations- **Statistics**: See `outputs/statistics/rusle_annual_statistics.csv` for numeric data

│- **Charts**: View PNG figures in `outputs/figures/`

├── generate_map_images.py          # Convert GeoTIFF to PNG for web

├── generate_dashboard.py           # Create interactive dashboard## Technology

├── RUSLE_Dashboard.html            # ⭐ Interactive web dashboard

├── README.md                       # This file (project overview)- **Python 3.10+**: Data processing

└── RUN_INSTRUCTIONS.md             # Step-by-step execution guide- **Google Earth Engine**: Satellite data access

```- **GDAL/Rasterio**: Geospatial analysis

- **Plotly.js**: Interactive visualizations

## Quick Start

## Academic Context

See **RUN_INSTRUCTIONS.md** for detailed setup and execution steps.

This project is part of an MSc in Geoinformatics, demonstrating the application of remote sensing and GIS for environmental monitoring and erosion risk assessment.

**TL;DR:**

```bash```

# Install dependencies

pip install earthengine-api rasterio geopandas numpy pandas matplotlib scipy---



# Authenticate Google Earth Engine (one time only)## 🚀 Quick Start

earthengine authenticate

### 1. Install Dependencies

# Run all analysis scripts in order (takes 2-3 hours)

python scripts/01_data_preparation.py```bash

python scripts/02_calculate_ls_factor.pycd /home/ubuntuksh/Desktop/RUSLE

# ... continue through 09_generate_report.pychmod +x setup.sh

./setup.sh

# Generate dashboard map images```

python generate_map_images.py

### 2. Authenticate Google Earth Engine

# Create interactive dashboard

python generate_dashboard.py```bash

source venv/bin/activate

# Open RUSLE_Dashboard.html in your web browserearthengine authenticate

``````



## Viewing Results### 3. Run Analysis



### Interactive Dashboard (Recommended)```bash

**Open `RUSLE_Dashboard.html` in any web browser**# Full analysis (2014-2024)

python run_rusle_analysis.py

Features:

- **Year selector buttons** - Click to view data for 2014-2024# Specific year

- **Statistics cards** - Mean, median, max erosion, and severe erosion %python run_rusle_analysis.py --year 2020

- **Soil erosion risk map** - Color-coded spatial visualization (updates per year)

- **3 interactive charts** - Erosion classes, temporal trends, factor comparison# Year range

- **"ALL YEARS" view** - Compare all years at oncepython run_rusle_analysis.py --start-year 2014 --end-year 2024

```

### GIS Software

- Open `outputs/maps/soil_loss_YYYY.tif` in QGIS or ArcGIS---

- View high-resolution erosion maps with original data values

- Perform spatial analysis and create custom visualizations## 📊 Outputs



### Spreadsheet Analysis### Maps (GeoTIFF)

- Open `outputs/statistics/rusle_annual_statistics.csv` in Excel- `soil_loss_YYYY.tif` - Annual soil loss (t/ha/yr)

- Analyze trends, calculate statistics, create custom charts- `erosion_class_YYYY.tif` - Erosion severity (1-5)



## Technology Stack### Statistics (CSV)

- Annual mean, median, std, min, max

- **Python 3.10+**: Core data processing- Area per erosion class

- **Google Earth Engine**: Cloud-based satellite data access- Temporal trends

- **GDAL/Rasterio**: Geospatial raster processing

- **GeoPandas**: Vector data handling### Figures (PNG)

- **Matplotlib**: Static visualizations- Soil loss maps

- **Plotly.js**: Interactive dashboard charts- Erosion classification maps

- Pie charts

## Data Sources- Temporal trend plots

- Change detection maps

| Component | Source | Resolution | Coverage |

|-----------|--------|------------|----------|---

| Precipitation | CHIRPS | ~5 km | Daily, 2014-2024 |

| Soil Texture | OpenLandMap | 250 m | Static (2018) |## 🗺️ Study Area

| Elevation | SRTM DEM | 90 m | Static |

| NDVI | Sentinel-2 / Landsat 8 | 10/30 m | 2014-2024 |**Mula-Mutha Catchment**

| Land Cover | Dynamic World | 10 m | 2015-2024 |- **Location:** Pune District, Maharashtra, India

- **Coordinates:** 18°17′–18°31′ N, 73°25′–73°53′ E

All data downloaded at **90m resolution** for analysis.- **Area:** ~600 km²

- **Elevation:** 560m (plains) to 1,200m (Western Ghats foothills)

## Academic Context- **Land Use:** Mixed urban, agricultural, forested



**MSc Geoinformatics Thesis Project**  ---

Demonstrates integration of remote sensing, GIS, and Python for environmental monitoring and erosion risk assessment in data-scarce regions.

## 📦 Data Sources

## Notes

| Factor | Data Source | Resolution | Temporal |

- This analysis uses **real satellite observations**, not predictions|--------|-------------|------------|----------|

- All data processing is fully automated and reproducible| **R** | CHIRPS Daily Precipitation | ~5 km | 2014-2024 |

- The 49% erosion decrease likely reflects improved vegetation cover and conservation practices| **K** | OpenLandMap Soil Texture | 250 m | 2018 |

- High severe erosion (45% of area) indicates ongoing conservation needs in steep terrain| **LS** | SRTM DEM v3 | 90 m | Static |

| **C** | Sentinel-2 NDVI (Dynamic World) | 10 m | 2015-2024 |
| **P** | Derived from slope + land cover | 90 m | Annual |

---

## 🔬 Methodology Highlights

### R-Factor (Rainfall Erosivity)
```python
R = 79 + 0.363 × Annual_Precipitation
```

### K-Factor (Soil Erodibility)
Lookup table based on USDA soil texture classification (0.0053 - 0.045)

### LS-Factor (Topographic)
```python
LS = sqrt(500/100) × (0.53×S + 0.076×S² + 0.76)
```

### C-Factor (Cover Management)
```python
NDVI = (NIR - Red) / (NIR + Red)
C = exp(-2 × NDVI / (1 - NDVI))
```

### P-Factor (Support Practice)
Slope-based (0.1 for terraced cropland, 1.0 for steep/non-agricultural)

---

## ✅ Quality Control

### Validation Thresholds
- **Mean Soil Loss:** 5-30 t/ha/yr (Western Ghats typical)
- **Max Soil Loss:** < 200 t/ha/yr
- **R Factor:** 200-1200
- **K Factor:** 0.005-0.07
- **LS Factor:** 0-50
- **C Factor:** 0-1
- **P Factor:** 0.1-1.0

### Spatial Validation
- High erosion on steep, bare slopes ✓
- Low erosion in forests ✓
- Low erosion in urban areas ✓

### Temporal Validation
- Gradual year-to-year changes ✓
- No sudden jumps (>50%) ✓

---

## 📚 References

1. Renard et al. (1997) - RUSLE Guide (USDA Handbook 703)
2. Shinde et al. (2010) - RUSLE in Western Ghats
3. Ganasri & Ramesh (2016) - GIS-based RUSLE
4. Papaiordanidis & Jirka (2019) - RUSLE in Google Earth Engine
5. Ghosh et al. (2023) - Python-based decadal assessment

---

## 🤝 Contributing

This is an academic thesis project. For questions or collaboration:

**Bhavya Singh**  
MSc Geoinformatics Student  
BVIEER, Bharati Vidyapeeth University  
Email: [Add your email]

---

## 📄 License

Academic Use Only - MSc Thesis Project (2023-2025)

---

## 🙏 Acknowledgments

- **Dr. Lakshmi Kantakumar N.** - Project Supervisor
- **BVIEER** - Institutional Support
- **Google Earth Engine** - Cloud computing platform
- **CHIRPS, OpenLandMap, ESA** - Open data providers

---

**Last Updated:** 17 November 2025  
**Status:** Implementation Phase - Ready to Execute
