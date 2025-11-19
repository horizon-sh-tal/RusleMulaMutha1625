# 🚀 QUICK START GUIDE
## Resume RUSLE Project on New PC in 5 Minutes

---

## Step 1: Clone Repository (1 min)
```bash
git clone https://github.com/horizon-sh-tal/RusleMulaMutha1625.git
cd RusleMulaMutha1625
```

---

## Step 2: Setup Environment (2 min)
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Install all dependencies
pip install -r requirements.txt
```

---

## Step 3: Authenticate Earth Engine (1 min)
```bash
earthengine authenticate --force
```
Follow the browser prompt to authenticate.

---

## Step 4: Validate Everything (1 min)
```bash
# Check environment
python scripts/01_environment_validation.py

# Test DEM loading
python3 -c "import rasterio; print('✅ DEM OK:', rasterio.open('temp/dem_srtm_90m.tif').shape)"

# Test color scheme
python3 -c "from scripts.color_config import EROSION_PALETTE; print('✅ Colors OK:', len(EROSION_PALETTE), 'classes')"
```

**Expected Output:**
```
✅ All environment checks passed
✅ DEM OK: (871, 1305)
✅ Colors OK: 5 classes
```

---

## Step 5: Get Context & Continue
```bash
# Tell AI/Copilot:
"Read PROJECT_HANDOVER_GUIDE.md for full project context. 
This is a RUSLE soil erosion analysis for Mula-Mutha catchment (2016-2025).
DEM is ready. Next step: Calculate LS-factor from DEM.
Help me continue from there."
```

---

## 📍 YOU ARE HERE
- ✅ DEM data validated (`temp/dem_srtm_90m.tif`)
- ✅ Color scheme standardized (`scripts/color_config.py`)
- ✅ Configuration ready (`scripts/config.py`)
- 🔄 **NEXT:** Calculate LS-Factor (topographic factor)

---

## 🎯 Next Immediate Tasks

### Task 1: Calculate LS-Factor (PRIORITY 1)
Create `scripts/03_calculate_ls_factor.py`:
```python
import rasterio
import numpy as np
from pathlib import Path
from scripts.config import DEM_FILE

# Calculate slope and flow accumulation from DEM
# Apply LS-Factor formula
# Save to temp/factors/ls_factor.tif
```

### Task 2: Download Rainfall Data (PRIORITY 2)
```python
# Use Earth Engine to download CHIRPS data
# For years 2016-2025
# Calculate R-Factor for each year
```

### Task 3: Get Soil Data (PRIORITY 3)
- Download FAO soil texture data
- Calculate K-Factor using `scripts/02_calculate_k_factor.py`

---

## 📂 Critical Files
| File | Purpose |
|------|---------|
| `PROJECT_HANDOVER_GUIDE.md` | **READ THIS FIRST** - Complete project documentation |
| `temp/dem_srtm_90m.tif` | Active DEM (90m resolution, validated) |
| `scripts/config.py` | All project parameters |
| `scripts/color_config.py` | Standardized color scheme |
| `catchment/Mula_Mutha_Catchment.shp` | Study area boundary |

---

## ⚡ Common Commands
```bash
# Activate environment
source venv/bin/activate

# Check what's been completed
ls -lh temp/factors/
ls -lh outputs/maps/

# Commit changes
git add .
git commit -m "Completed LS-factor calculation"
git push origin main

# Run environment check
python scripts/01_environment_validation.py
```

---

## 🆘 Troubleshooting
| Issue | Solution |
|-------|----------|
| `earthengine` not found | Run `earthengine authenticate --force` |
| `rasterio` import error | Install GDAL: `sudo apt-get install gdal-bin libgdal-dev` |
| DEM not found | Run `git pull origin main` |
| Permission denied | Activate virtual environment first |

---

## 📞 For More Details
- **Full Documentation:** `PROJECT_HANDOVER_GUIDE.md`
- **Workflow Details:** `YEAR_BY_YEAR_WORKFLOW_2016-2025.txt`
- **GitHub Repo:** https://github.com/horizon-sh-tal/RusleMulaMutha1625

---

**Total Setup Time:** 5 minutes  
**Status:** Ready to continue from LS-Factor calculation  
**All foundational work is done. Just follow the next steps!** 🎉
