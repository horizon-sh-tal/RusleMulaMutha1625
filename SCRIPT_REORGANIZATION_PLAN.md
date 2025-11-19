# SCRIPT REORGANIZATION PLAN

**Date**: 19 November 2025  
**Status**: ✅ **VERIFIED AND APPROVED**

---

## ✅ APPROACH VERIFICATION

Your approach is **100% CORRECT** and perfectly aligned with:
1. ✅ `YEAR_BY_YEAR_WORKFLOW_2016-2025.txt` (559 lines)
2. ✅ Your data source table (K-Factor: OpenLandMap 2016 for all years)
3. ✅ RUSLE methodology best practices

---

## 📋 SCRIPT REORGANIZATION

### Step 1: Delete Unnecessary Script ❌

**File to DELETE**: `scripts/00_download_dem.py`

**Reason**:
- DEM already exists: `temp/dem_srtm_90m.tif` (1.46 MB, 90m, validated)
- Downloaded manually from GEE Code Editor
- Won't be downloaded again
- No need to keep this script

**Action**:
```bash
mv scripts/00_download_dem.py scripts/old_scripts_backup/
# Or delete: rm scripts/00_download_dem.py
```

---

### Step 2: Keep and Modify Data Preparation ✅

**File to KEEP**: `scripts/01_data_preparation.py`

**Purpose**: First-time validation when client/friend runs project

**What it should do**:
1. ✅ Validate catchment shapefile exists and is correct
   - Check file: `catchment/Mula_Mutha_Catchment.shp`
   - Validate area: ~5,832 km²
   - Validate bounds: 73.34-74.39°E, 18.30-19.00°N

2. ✅ Validate DEM exists and is correct
   - Check file: `temp/dem_srtm_90m.tif`
   - Validate resolution: 90m × 90m
   - Validate dimensions: 1305 × 871 pixels
   - Validate elevation range: 32-1312m

3. ✅ Create validation visualizations
   - Generate: `outputs/figures/01_catchment_and_dem.png`
   - Show catchment boundary + DEM side-by-side

4. ✅ Optional: Clip DEM to catchment
   - Save: `temp/dem_processed.tif` (smaller, clipped version)
   - This is optional, Script 03 can use original DEM directly

**Status**: Review and modify if needed

---

### Step 3: Create K-Factor Script ✅ (NEW)

**File to CREATE**: `scripts/02_calculate_k_factor.py`

**Data Source**: OpenLandMap Soil Texture (2016-01-01)

**Process**:
1. Download from Google Earth Engine:
   - Dataset: `OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02`
   - Date: 2016-01-01 (static)
   - Bands: `b0` (0cm), `b10` (10cm), `b30` (30cm) - Use `b0` for surface

2. Extract soil texture percentages:
   - Sand % (USDA class 1-3)
   - Silt % (USDA class 4-6)
   - Clay % (USDA class 7-12)

3. Apply USDA K-Factor lookup table:
   - Based on sand%, silt%, clay% combination
   - K-Factor range: 0.005 - 0.07 (typical for soils)

4. Clip to catchment boundary

5. Save output:
   - File: `temp/factors/k_factor.tif`
   - Validate range: 0.005 - 0.07
   - Validate mean: ~0.02-0.04

**Usage**: This ONE file will be used for ALL 10 years (2016-2025)

**Status**: ⏳ TO BE CREATED

---

### Step 4: Create LS-Factor Script ✅ (NEW)

**File to CREATE**: `scripts/03_calculate_ls_factor.py`

**Data Source**: SRTM DEM (`temp/dem_srtm_90m.tif`) - Static

**Process**:
1. Load DEM: `temp/dem_srtm_90m.tif`

2. Calculate Slope:
   - Use `richdem` or `numpy.gradient`
   - Slope in degrees
   - Convert to slope factor (S)

3. Calculate Slope Length:
   - Flow accumulation analysis
   - Slope length factor (L)

4. Apply RUSLE LS-Factor formula:
   ```
   L = (λ / 22.13)^m
   S = 10.8 × sin(θ) + 0.03  (for slope < 9%)
   S = 16.8 × sin(θ) - 0.50  (for slope ≥ 9%)
   LS = L × S
   ```
   Where:
   - λ = slope length (meters)
   - θ = slope angle (radians)
   - m = 0.5 (typical value)

5. Save output:
   - File: `temp/factors/ls_factor.tif`
   - Validate range: 0 - 50 (typical max)
   - Validate mean: ~2-5 (for hilly terrain)

**Usage**: This ONE file will be used for ALL 10 years (2016-2025)

**Status**: ⏳ TO BE CREATED

---

## 📊 STATIC vs DYNAMIC FACTORS

### Static Factors (Calculate ONCE) ✅

| Factor | Script | Data Source | Date | Output | Usage |
|--------|--------|-------------|------|--------|-------|
| K-Factor | 02 | OpenLandMap | 2016-01-01 | `temp/factors/k_factor.tif` | All 10 years |
| LS-Factor | 03 | SRTM DEM | Static | `temp/factors/ls_factor.tif` | All 10 years |

### Dynamic Factors (Calculate per YEAR) ⏳

| Year | R-Factor (04) | C-Factor (05) | P-Factor (06) |
|------|---------------|---------------|---------------|
| 2016 | CHIRPS 2016 | Landsat 8 2016 | Dynamic World 2016 |
| 2017 | CHIRPS 2017 | Landsat 8 2017 | Dynamic World 2017 |
| 2018 | CHIRPS 2018 | **Sentinel-2** 2018 | Dynamic World 2018 |
| 2019 | CHIRPS 2019 | Sentinel-2 2019 | Dynamic World 2019 |
| 2020 | CHIRPS 2020 | Sentinel-2 2020 | Dynamic World 2020 |
| 2021 | CHIRPS 2021 | Sentinel-2 2021 | Dynamic World 2021 |
| 2022 | CHIRPS 2022 | Sentinel-2 2022 | Dynamic World 2022 |
| 2023 | CHIRPS 2023 | Sentinel-2 2023 | Dynamic World 2023 |
| 2024 | CHIRPS 2024 | Sentinel-2 2024 | Dynamic World 2024 |
| 2025 | CHIRPS 2025* | Sentinel-2 2025* | Dynamic World 2025* |

*2025: Jan-Nov only (11 months)

---

## 🎯 SCRIPT EXECUTION ORDER

### First-Time Setup (Client/Friend runs project):

```bash
# Step 1: Validate data (run once)
python scripts/01_data_preparation.py
# → Validates DEM, catchment
# → Creates visualizations
# → Confirms everything is ready

# Step 2: Calculate K-Factor (run once)
python scripts/02_calculate_k_factor.py
# → Output: temp/factors/k_factor.tif
# → Use for ALL years

# Step 3: Calculate LS-Factor (run once)
python scripts/03_calculate_ls_factor.py
# → Output: temp/factors/ls_factor.tif
# → Use for ALL years
```

### Year-by-Year Processing (2016-2025):

```bash
# For each year (e.g., 2016):
python scripts/04_calculate_r_factor.py --year 2016  # CHIRPS
python scripts/05_calculate_c_factor.py --year 2016  # Landsat 8/Sentinel-2
python scripts/06_calculate_p_factor.py --year 2016  # Dynamic World
python scripts/07_calculate_rusle.py --year 2016     # R × K × LS × C × P

# Repeat for 2017-2025
```

---

## 🔄 WORKFLOW ALIGNMENT

From `YEAR_BY_YEAR_WORKFLOW_2016-2025.txt`:

```
STATIC FACTORS (ONE-TIME ONLY - USE FOR ALL YEARS)
├── Step 1: K-Factor (Soil Erodibility)        → 02_calculate_k_factor.py ✅
│   └── Download OpenLandMap soil texture (2016-01-01) ✅
└── Step 2: LS-Factor (Topography)             → 03_calculate_ls_factor.py ✅
    └── Calculate slope from DEM ✅

YEAR 2016
├── Step 1: Use existing K-Factor ✅
├── Step 2: Use existing LS-Factor ✅
├── Step 3: R-Factor (Rainfall)                → 04_calculate_r_factor.py
├── Step 4: C-Factor (Vegetation)              → 05_calculate_c_factor.py
├── Step 5: P-Factor (Conservation)            → 06_calculate_p_factor.py
└── Step 6: RUSLE Calculation                  → 07_calculate_rusle.py
```

**Perfect alignment!** ✅

---

## 📁 FILE STRUCTURE AFTER REORGANIZATION

```
scripts/
├── old_scripts_backup/
│   ├── 00_download_dem.py              ← MOVED (backup)
│   ├── 02_calculate_ls_factor.py       ← MOVED (will recreate as 03)
│   ├── 03_calculate_k_factor.py        ← MOVED (will recreate as 02)
│   └── ... (other old scripts)
│
├── 01_data_preparation.py              ← KEEP (first-time validation)
├── 02_calculate_k_factor.py            ← CREATE NEW (OpenLandMap 2016)
├── 03_calculate_ls_factor.py           ← CREATE NEW (SRTM DEM)
├── 04_calculate_r_factor.py            ← TO CREATE (CHIRPS, per year)
├── 05_calculate_c_factor.py            ← TO CREATE (Landsat/Sentinel, per year)
├── 06_calculate_p_factor.py            ← TO CREATE (Dynamic World, per year)
├── 07_calculate_rusle.py               ← TO CREATE (R×K×LS×C×P, per year)
├── 08_temporal_analysis.py             ← TO CREATE (after all years)
├── 09_generate_report.py               ← TO CREATE (final report)
└── config.py                           ← KEEP (configuration)

temp/
└── factors/
    ├── k_factor.tif                    ← STATIC (one file for all years)
    ├── ls_factor.tif                   ← STATIC (one file for all years)
    ├── r_factor_2016.tif               ← DYNAMIC (per year)
    ├── c_factor_2016.tif               ← DYNAMIC (per year)
    ├── p_factor_2016.tif               ← DYNAMIC (per year)
    ├── r_factor_2017.tif               ← DYNAMIC (per year)
    └── ... (continue for 2017-2025)
```

---

## ✅ IMMEDIATE ACTION ITEMS

### Priority 1: Cleanup ✅
- [ ] Move `scripts/00_download_dem.py` to `scripts/old_scripts_backup/`
- [ ] Move old `scripts/02_calculate_ls_factor.py` to backup
- [ ] Move old `scripts/03_calculate_k_factor.py` to backup

### Priority 2: Review Existing Script ✅
- [ ] Review `scripts/01_data_preparation.py`
- [ ] Ensure it validates DEM and catchment
- [ ] Test run to confirm it works

### Priority 3: Create K-Factor Script ✅ (NEXT)
- [ ] Create `scripts/02_calculate_k_factor.py`
- [ ] Implement OpenLandMap download (2016-01-01)
- [ ] Implement K-Factor calculation (USDA lookup)
- [ ] Test and validate output

### Priority 4: Create LS-Factor Script ✅
- [ ] Create `scripts/03_calculate_ls_factor.py`
- [ ] Implement slope calculation
- [ ] Implement slope length calculation
- [ ] Implement LS-Factor formula
- [ ] Test and validate output

---

## 🎉 SUMMARY

✅ **Your approach is VERIFIED and CORRECT!**

**Key Points**:
1. ✅ Delete `00_download_dem.py` (DEM already exists)
2. ✅ Keep `01_data_preparation.py` (validation)
3. ✅ Create `02_calculate_k_factor.py` (OpenLandMap 2016, static)
4. ✅ Create `03_calculate_ls_factor.py` (SRTM DEM, static)
5. ✅ K and LS factors calculated ONCE, used for ALL 10 years
6. ✅ Perfectly aligned with workflow document

**Ready to proceed!** 🚀

---

**End of Plan**
