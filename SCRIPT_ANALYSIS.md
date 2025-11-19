# SCRIPT ANALYSIS - STEP 0 COMPARISON

**Date**: 19 November 2025  
**Purpose**: Compare existing scripts and determine what's already done

---

## STEP 0 REQUIREMENTS (From Workflow)

According to `YEAR_BY_YEAR_WORKFLOW_2016-2025.txt`, there is **NO EXPLICIT STEP 0** in the workflow!

The workflow starts directly with:
- **STATIC FACTORS** (K-Factor, LS-Factor)
- Then **YEAR 2016** processing

However, we have these scripts:
- `00_download_dem.py` - Downloads SRTM DEM from GEE
- `01_data_preparation.py` - Loads catchment, validates DEM, clips and resamples

---

## WHAT HAS BEEN COMPLETED

### ✅ Already Done (Manual + Script 00):
1. **DEM Download**: `temp/dem_srtm_90m.tif` exists (1.5 MB, 90m resolution)
   - Source: CGIAR/SRTM90_V4
   - Downloaded manually from GEE Code Editor
   - Validated: 1305×871 pixels, 32-1312m elevation
   - Coverage: 100%

2. **Catchment Boundary**: `Mula_Mutha_Catchment.shp` exists
   - Area: 5,832 km²
   - Bounds: 73.34-74.39°E, 18.30-19.00°N

3. **Color Palette**: Standardized 5-category erosion classification

4. **Dashboard Design**: Exact catchment shape overlay approach defined

---

## WHAT SCRIPT 00 DOES (00_download_dem.py)

```
Function: download_srtm_dem()
├── Initialize Google Earth Engine
├── Load catchment boundary shapefile
├── Get bounding box
├── Load SRTM DEM from GEE (CGIAR/SRTM90_V4)
├── Clip to catchment area
├── Download DEM to temp/dem_srtm_90m.tif
└── Validate downloaded DEM (size, range, resolution)
```

**Status**: ✅ **ALREADY COMPLETED** (DEM exists and validated)

---

## WHAT SCRIPT 01 DOES (01_data_preparation.py)

```
Function: load_catchment_boundary()
├── Load shapefile
├── Validate geometry
├── Calculate area
├── Check bounds
├── Reproject to target CRS
└── Save validated catchment (temp/catchment_validated.geojson)

Function: load_and_validate_dem(catchment)
├── Load DEM (primary or backup)
├── Validate statistics
├── Clip to catchment boundary
├── Resample to target resolution (90m)
└── Save processed DEM (temp/dem_processed.tif)

Function: visualize_data(catchment, dem, transform)
├── Plot catchment boundary
├── Plot DEM
└── Save visualization (outputs/figures/01_catchment_and_dem.png)
```

**Status**: ⏳ **NOT RUN YET** (no temp/catchment_validated.geojson or temp/dem_processed.tif)

---

## CRITICAL FINDINGS

### 🔴 **DUPLICATION ISSUE**
Both scripts download/process DEM:
- **Script 00**: Downloads from GEE → `temp/dem_srtm_90m.tif`
- **Script 01**: Clips/resamples DEM → `temp/dem_processed.tif`

### 🔴 **MISSING FROM WORKFLOW**
The `YEAR_BY_YEAR_WORKFLOW_2016-2025.txt` does **NOT** mention:
- Catchment loading/validation
- DEM clipping
- DEM resampling
- Visualization generation

It starts directly with **K-Factor** and **LS-Factor** calculations!

### ✅ **WHAT WE ACTUALLY NEED**

According to the workflow, we should:
1. Have DEM ready ✅ (we have `temp/dem_srtm_90m.tif`)
2. Have catchment ready ✅ (we have `Mula_Mutha_Catchment.shp`)
3. Start with **LS-Factor calculation** (Script 02)

---

## RECOMMENDATION

### Option 1: **SKIP SCRIPT 01** (Recommended)
- We already have validated DEM (`temp/dem_srtm_90m.tif`)
- Catchment shapefile exists and is valid
- LS-Factor script (02) can load DEM directly
- **Action**: Move to Script 02 immediately

### Option 2: **RUN SCRIPT 01** (Extra validation)
- Create `temp/catchment_validated.geojson` for convenience
- Create `temp/dem_processed.tif` (clipped/resampled version)
- Generate visualization
- **Action**: Run Script 01, then Script 02

### Option 3: **MERGE SCRIPTS** (Clean approach)
- Combine 00 and 01 into single "00_setup_data.py"
- Make it optional (skip if files exist)
- **Action**: Create new script, move old ones to backup

---

## FILES TO BACKUP

Move these to `scripts/old_scripts_backup/`:
- `00_download_dem.py` ← Keep for reference
- `01_data_preparation.py` ← Keep for reference
- All other scripts 02-09 ← Will modify based on workflow

---

## NEXT STEPS

1. **Backup old scripts** ✅ (folder created)
2. **Verify DEM is ready** → Check `temp/dem_srtm_90m.tif`
3. **Verify catchment is ready** → Check `Mula_Mutha_Catchment.shp`
4. **DECISION POINT**:
   - Run Script 01? (creates validated files)
   - Skip to Script 02? (LS-Factor calculation)

---

## WORKFLOW ALIGNMENT

According to `YEAR_BY_YEAR_WORKFLOW_2016-2025.txt`:

```
STATIC FACTORS (ONE-TIME ONLY)
├── Step 1: K-Factor (Soil) ← Script 03
└── Step 2: LS-Factor (Topography) ← Script 02

YEAR 2016
├── Step 1: Use K-Factor
├── Step 2: Use LS-Factor
├── Step 3: R-Factor (Rainfall) ← Script 04
├── Step 4: C-Factor (Vegetation) ← Script 05
├── Step 5: P-Factor (Conservation) ← Script 06
├── Step 6: RUSLE Calculation ← Script 07
└── Step 7: Validation
```

**Scripts 00 and 01 are preparatory**, not in main workflow!

---

## CONCLUSION

✅ **Data is READY**:
- DEM: `temp/dem_srtm_90m.tif` (validated, 90m, 100% coverage)
- Catchment: `Mula_Mutha_Catchment.shp` (5,832 km²)

⏭️ **Next workflow step**: Calculate LS-Factor (Script 02)

🗂️ **Old scripts**: Move to backup folder for reference

🎯 **Immediate action**: Run Script 02 (02_calculate_ls_factor.py)

