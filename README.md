# RUSLE Soil Erosion Analysis - Mula-Mutha Catchment (2016-2025)

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-In%20Development-yellow.svg)](https://github.com/horizon-sh-tal/RusleMulaMutha1625)

**MSc Geoinformatics Thesis Project**  
**Author:** Bhavya Singh  
**Institution:** BVIEER, Bharati Vidyapeeth University  
**Analysis Period:** 2016-2025 (10 years)

---

## 📋 Overview

This project analyzes **soil erosion** in the Mula-Mutha river catchment (Pune, Maharashtra, India) using the **Revised Universal Soil Loss Equation (RUSLE)** methodology with 10 years of satellite data (2016-2025) from Google Earth Engine.

### RUSLE Equation
```
A = R × K × LS × C × P
```

**Where:**
- **A** = Annual soil loss (tons/hectare/year)
- **R** = Rainfall erosivity factor (from CHIRPS precipitation data)
- **K** = Soil erodibility factor (from soil texture data)
- **LS** = Topographic factor (slope length and steepness from SRTM DEM)
- **C** = Cover management factor (from land cover data)
- **P** = Support practice factor (conservation practices)

---

## 🗺️ Study Area

- **Location:** Mula-Mutha Catchment, Pune, Maharashtra, India
- **Area:** ~5,832 km²
- **Coordinates:** 18.30°N - 19.00°N, 73.34°E - 74.39°E
- **Elevation Range:** 32m - 1,312m above sea level
- **Climate:** Semi-arid to sub-humid tropical

---

## 🚀 Quick Start

### New PC Setup (5 minutes)
```bash
# 1. Clone repository
git clone https://github.com/horizon-sh-tal/RusleMulaMutha1625.git
cd RusleMulaMutha1625

# 2. Setup environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac (or venv\Scripts\activate on Windows)
pip install -r requirements.txt

# 3. Authenticate Earth Engine
earthengine authenticate --force

# 4. Validate setup
python scripts/01_environment_validation.py
```

✅ **Setup complete!** See [QUICK_START.md](QUICK_START.md) for detailed instructions.

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[PROJECT_HANDOVER_GUIDE.md](PROJECT_HANDOVER_GUIDE.md)** | 📖 **START HERE** - Complete project documentation, status, and next steps |
| [QUICK_START.md](QUICK_START.md) | ⚡ 5-minute setup guide for new PC |
| [YEAR_BY_YEAR_WORKFLOW_2016-2025.txt](YEAR_BY_YEAR_WORKFLOW_2016-2025.txt) | 📋 Detailed workflow for each analysis year |
| [DEM_COMPARISON_REPORT.txt](DEM_COMPARISON_REPORT.txt) | 🗺️ DEM validation and comparison report |

---

## 📊 Current Status

### ✅ Completed
- [x] DEM data acquired and validated (SRTM 90m)
- [x] Catchment boundary prepared
- [x] Color scheme standardized (5-class erosion classification)
- [x] Project structure established
- [x] Environment validation script
- [x] Configuration files created
- [x] Dashboard mockup designed

### 🔄 In Progress
- [ ] LS-Factor calculation (topographic factor)
- [ ] Rainfall data download (R-Factor)
- [ ] Soil data acquisition (K-Factor)

### ⏳ Pending
- [ ] C-Factor calculation (land cover)
- [ ] P-Factor assignment
- [ ] RUSLE calculation (2016-2025)
- [ ] Temporal trend analysis
- [ ] Interactive dashboard generation
- [ ] Final report

**Progress:** ~20% Complete (Foundation established)

---

## 🛠️ Technology Stack

- **Python 3.8+** - Core programming language
- **Rasterio** - Geospatial raster processing
- **GeoPandas** - Vector data handling
- **Google Earth Engine** - Satellite data access (CHIRPS, MODIS, SRTM)
- **Matplotlib/Plotly** - Visualization
- **Folium** - Interactive web maps
- **NumPy/SciPy** - Scientific computing

---

## 📂 Project Structure

```
RUSLE/
├── catchment/                  # Study area boundary and reference DEMs
├── temp/
│   ├── dem_srtm_90m.tif       # ⭐ Active DEM (90m resolution)
│   └── factors/               # Generated RUSLE factor rasters
├── outputs/
│   ├── figures/               # Maps and visualizations
│   ├── maps/                  # Annual erosion maps
│   ├── web_maps/              # Interactive HTML maps
│   ├── statistics/            # Statistical summaries (CSV/JSON)
│   └── logs/                  # Processing logs
├── scripts/
│   ├── config.py              # ⭐ Main configuration
│   ├── color_config.py        # ⭐ Standardized color scheme
│   ├── 01_environment_validation.py
│   ├── 02_calculate_k_factor.py
│   └── ...                    # Additional analysis scripts
├── data/                      # Downloaded datasets (rainfall, soil, land cover)
├── docs/                      # Documentation and reports
├── PROJECT_HANDOVER_GUIDE.md  # 📖 Complete project documentation
├── QUICK_START.md             # ⚡ Quick setup guide
└── requirements.txt           # Python dependencies
```

---

## � Erosion Classification

| Category | Color | Range (t/ha/year) | Hex Code |
|----------|-------|-------------------|----------|
| Very Low | Dark Green | 0 - 5 | `#006837` |
| Low | Light Green | 5 - 10 | `#7CB342` |
| Moderate | Yellow | 10 - 20 | `#FFEB3B` |
| High | Orange | 20 - 40 | `#FF9800` |
| Very High | Red | > 40 | `#D32F2F` |

**Consistent across all outputs:** Maps, dashboards, reports, and web visualizations.

---

## 🎯 Project Goals

### Primary Deliverables
1. **10 Annual Erosion Maps** (2016-2025) with consistent visualization
2. **Interactive Web Dashboard** with 3D terrain basemap overlay
3. **Temporal Trend Analysis** showing erosion patterns over time
4. **Statistical Summaries** for each year and overall trends
5. **Comprehensive Technical Report** (PDF)

### Scientific Objectives
- Quantify annual soil loss in Mula-Mutha catchment
- Identify erosion hotspots (persistent high-risk areas)
- Analyze temporal trends (2016-2025)
- Assess impact of land cover changes on erosion
- Provide recommendations for soil conservation measures

---

## 🔧 Key Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `01_environment_validation.py` | Validate dependencies and setup | ✅ Ready |
| `02_calculate_k_factor.py` | Calculate soil erodibility factor | ✅ Ready (needs soil data) |
| `03_calculate_ls_factor.py` | Calculate topographic factor | 🔄 Next step |
| `04_calculate_r_factor.py` | Calculate rainfall erosivity | ⏳ To create |
| `05_calculate_c_factor.py` | Calculate cover management factor | ⏳ To create |
| `07_calculate_rusle_yearly.py` | Annual RUSLE calculation | ⏳ To create |
| `08_temporal_analysis.py` | Trend analysis across years | ⏳ To create |
| `dashboard.py` | Interactive dashboard generator | ⏳ To enhance |

---

## � Data Sources

| Data Type | Source | Resolution | Purpose |
|-----------|--------|------------|---------|
| **DEM** | CGIAR SRTM90 V4 | 90m | LS-Factor (topography) |
| **Rainfall** | CHIRPS Daily | ~5km | R-Factor (erosivity) |
| **Soil** | FAO/OpenLandMap | 250m | K-Factor (erodibility) |
| **Land Cover** | ESA WorldCover | 10m | C-Factor (vegetation) |
| **Catchment** | Manual delineation | Vector | Study area boundary |

---

## 🧑‍💻 For Developers

### Adding New Analysis
1. Create script in `scripts/` directory
2. Import configuration from `scripts/config.py`
3. Use colors from `scripts/color_config.py`
4. Save outputs to appropriate `outputs/` subdirectory
5. Update this README and project documentation

### Code Style
- Follow PEP 8 guidelines
- Use descriptive variable names
- Add docstrings to functions
- Include error handling and logging

### Git Workflow
```bash
git add .
git commit -m "Descriptive message about changes"
git push origin main
```

---

## 📞 Support & Contact

- **GitHub Repository:** https://github.com/horizon-sh-tal/RusleMulaMutha1625
- **Issues:** Report bugs or request features via GitHub Issues
- **Documentation:** See [PROJECT_HANDOVER_GUIDE.md](PROJECT_HANDOVER_GUIDE.md)

---

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 🙏 Acknowledgments

- **CGIAR-CSI** for SRTM elevation data
- **UCSB Climate Hazards Center** for CHIRPS rainfall data
- **ESA** for WorldCover land cover data
- **Google Earth Engine** for data access and processing platform
- **Bharati Vidyapeeth University** for academic support

---

## 📝 Citation

If you use this project or methodology, please cite:

```
Singh, B. (2025). RUSLE-based Soil Erosion Analysis of Mula-Mutha Catchment (2016-2025).
MSc Geoinformatics Thesis, BVIEER, Bharati Vidyapeeth University, Pune, India.
GitHub: https://github.com/horizon-sh-tal/RusleMulaMutha1625
```

---

**Last Updated:** 19 November 2025  
**Version:** 1.0  
**Status:** Active Development 🚧

- **Elevation Range:** 32m - 1,312m

- **LS**: Topographic factor (from DEM - slope length and steepness)- **LS**: Topographic factor (from DEM - slope length and steepness)

---

- **C**: Vegetation cover factor (from Sentinel-2/Landsat 8 NDVI)- **C**: Vegetation cover factor (from Sentinel-2/Landsat 8 NDVI)

## 📊 Data Sources (All from Google Earth Engine)

- **P**: Conservation practice factor (from Dynamic World land cover)- **P**: Conservation practice factor (from Dynamic World land cover)

| Factor | Source | Resolution |

|--------|--------|------------|

| R (Rainfall) | CHIRPS | 90m |

| K (Soil) | OpenLandMap | 90m |**Analyzes temporal trends** to detect how erosion patterns changed over 11 years**Analyzes temporal trends** to detect how erosion patterns changed over 11 years

| LS (Topography) | SRTM DEM v4 | 90m |

| C (Vegetation) | Landsat 8 / Sentinel-2 | 90m |

| P (Land Cover) | Dynamic World | 90m |

**Generates visualizations** including:**Generates visualizations** including:

---

- 11 annual soil erosion risk maps (GeoTIFF format)- 11 annual soil erosion risk maps (GeoTIFF format)

## 🚀 Quick Start

- Interactive web dashboard with maps, statistics, and charts- Interactive web dashboard with maps, statistics, and charts

```bash

# Clone repository- Statistical reports and trend analysis- Statistical reports and trend analysis

git clone https://github.com/horizon-sh-tal/RusleMulaMutha1625.git

cd RusleMulaMutha1625



# Setup environment## Key Results## Key Results

python -m venv venv

source venv/bin/activate

pip install -r requirements.txt

- **Study Area**: Mula-Mutha catchment, Pune - 5,832 km²- **Study Area**: Mula-Mutha catchment, Pune - 5,832 km²

# Authenticate GEE

earthengine authenticate- **Analysis Period**: 2014-2024 (11 years of real satellite data)- **Analysis Period**: 2014-2024 (11 years of real satellite data)



# Run analysis- **Mean Soil Loss**: 643 t/ha/yr (median: 35.3 t/ha/yr)- **Mean Soil Loss**: 643 t/ha/yr (median: 35.3 t/ha/yr)

python scripts/00_download_dem.py

python run_rusle_analysis.py --start-year 2016 --end-year 2025- **Erosion Trend**: **49% decrease** from 2014 to 2024- **Erosion Trend**: **49% decrease** from 2014 to 2024

```

- **Improvement**: 81.4% of catchment area shows reduced erosion- **Improvement**: 81.4% of catchment area shows reduced erosion

---

- **Risk Level**: 45% of area classified as severe erosion (>40 t/ha/yr)- **Risk Level**: 45% of area classified as severe erosion (>40 t/ha/yr)

## 📁 Project Structure



```

RUSLE/## Approach & Methodology## Approach & Methodology

├── scripts/           # Analysis scripts (00-09)

├── catchment/         # Study area boundary

├── outputs/           # Results (maps, stats, figures)

├── temp/              # Intermediate data### 1. Data Acquisition (Google Earth Engine)### 1. Data Acquisition (Google Earth Engine)

└── docs/              # Documentation

```- Download multi-year satellite datasets automatically- Download multi-year satellite datasets automatically



---- Resample all data to 90m resolution to stay within GEE limits- Resample all data to 90m resolution to stay within GEE limits



## 📈 Status- Handle NoData values properly during processing- Handle NoData values properly during processing



- ✅ DEM Downloaded (SRTM 90m)

- ⏳ Factor Calculations (In Progress)

- ⏳ Temporal Analysis (Pending)### 2. RUSLE Factor Calculation### 2. RUSLE Factor Calculation



**Last Updated:** 19 November 2025Each factor is calculated following standard RUSLE methodology:Each factor is calculated following standard RUSLE methodology:


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
