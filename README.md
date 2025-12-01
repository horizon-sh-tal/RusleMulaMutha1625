# Soil Erosion Analysis for Mula-Mutha Catchment

## What is This Project?

This project calculates **soil erosion** (how much soil is being washed away) in the Mula-Mutha Catchment area using satellite data and scientific methods. It analyzes data from **2016 to 2025** and creates maps, charts, and reports showing where and how much soil erosion is happening.

The project uses the **RUSLE method** (Revised Universal Soil Loss Equation), which is a trusted scientific approach to estimate soil loss.

---

## What Does It Do?

- Downloads satellite images and terrain data automatically
- Calculates different factors that affect soil erosion (rainfall, soil type, slope, vegetation, etc.)
- Combines all factors to estimate annual soil loss
- Creates colorful maps and charts to visualize the results
- Generates statistics and reports you can share

---

## Requirements

Before running this project, you need:

1. **Python 3.8 or higher** installed on your computer
2. **Google Earth Engine account** (free to sign up at https://earthengine.google.com/)
3. **Internet connection** (to download satellite data)

---

## How to Run This Project

### Step 1: Install Required Software

Open a terminal/command prompt in the project folder and run:

```bash
pip install -r requirements.txt
```

This will install all necessary software libraries. It might take a few minutes.

### Step 2: Set Up Google Earth Engine

Run this command to connect your Google Earth Engine account:

```bash
python scripts/00_gee_setup.py
```

- It will open a web browser asking you to log in to Google
- Follow the instructions on screen
- Enter your Google Earth Engine project ID when asked

### Step 3: Run the Complete Analysis

To run everything automatically, use these commands **in order**:

```bash
# 1. Check that everything is set up correctly
python scripts/01_environment_validation.py

# 2. Prepare the study area
python scripts/02_build_aoi_mask.py

# 3. Calculate slope factor (LS)
python scripts/02_calculate_ls_factor.py

# 4. Calculate soil factor (K)
python scripts/03_calculate_k_factor.py

# 5. Calculate vegetation factor (C)
python scripts/04_calculate_c_factor.py

# 6. Calculate rainfall factor (R)
python scripts/05_prepare_r_inputs.py 
python scripts/05_calculate_r_factor.py

# 7. Calculate conservation practice factor (P)
python scripts/06_prepare_p_factor.py
python scripts/06_calculate_p_factor.py

# 8. Calculate final soil loss
python scripts/07_calculate_soil_loss.py

# 9. Create time series analysis
python scripts/08_temporal_analysis.py

# 10. Create interactive web maps
python scripts/09_make_overlay_maps.py
python scripts/09_dashboard.py
```

---

## Where to Find the Results

After running the scripts, you'll find all outputs organized in the `outputs` folder:

### **outputs/maps/**
- Contains the final erosion maps as image files (PNG format)
- You can open these with any image viewer

### **outputs/figures/**
- **erosion/** - Charts showing erosion patterns
- **temporal/** - Graphs showing how erosion changes over time

### **outputs/statistics/**
- **erosion/** - Excel-compatible CSV files with numbers and statistics
- **temporal/** - Time series data you can analyze in Excel

### **outputs/web_maps/**
- Interactive maps you can open in a web browser
- Click and zoom to explore the data

### **outputs/logs/**
- Technical logs showing what the program did
- Useful if something goes wrong

---

## Other Important Folders

- **catchment/** - Contains the boundary shapefile of your study area
- **scripts/** - All the Python programs that do the work

---

## Technical Details

- **Study Area:** Mula-Mutha Catchment
- **Time Period:** 2016-2025
- **Resolution:** 90 meters
- **Method:** RUSLE (Revised Universal Soil Loss Equation)
- **Data Sources:** Google Earth Engine (SRTM, CHIRPS, MODIS, SRTMGL1)

---

