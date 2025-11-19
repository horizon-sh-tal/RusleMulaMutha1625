#!/bin/bash
# Full 11-year RUSLE Analysis (2014-2024)
# Estimated time: 6-8 hours

set -e  # Exit on error
source venv/bin/activate

echo "=========================================="
echo "FULL 11-YEAR RUSLE ANALYSIS (2014-2024)"
echo "Started: $(date)"
echo "=========================================="
echo ""

# Step 1-3: Static factors (already done)
echo "✅ Steps 1-3: Static factors already completed (DEM, LS, K)"
echo ""

# Step 4: R-factor for all years
echo "📊 Step 4: Calculating R-factor (2014-2024)..."
echo "   Downloading rainfall data from CHIRPS..."
python scripts/04_calculate_r_factor.py --start-year 2014 --end-year 2024
if [ $? -eq 0 ]; then
    echo "✅ R-factor completed for all years"
else
    echo "❌ R-factor failed"
    exit 1
fi
echo ""

# Step 5: C-factor for all years  
echo "📊 Step 5: Calculating C-factor (2014-2024)..."
echo "   Downloading NDVI from Sentinel-2/Landsat 8..."
python scripts/05_calculate_c_factor.py --start-year 2014 --end-year 2024
if [ $? -eq 0 ]; then
    echo "✅ C-factor completed for all years"
else
    echo "❌ C-factor failed"
    exit 1
fi
echo ""

# Step 6: P-factor for all years
echo "📊 Step 6: Calculating P-factor (2014-2024)..."
echo "   Downloading land cover from Dynamic World..."
python scripts/06_calculate_p_factor.py --start-year 2014 --end-year 2024
if [ $? -eq 0 ]; then
    echo "✅ P-factor completed for all years"
else
    echo "❌ P-factor failed"
    exit 1
fi
echo ""

# Step 7: RUSLE calculation for all years
echo "📊 Step 7: Calculating RUSLE (2014-2024)..."
python scripts/07_calculate_rusle.py --start-year 2014 --end-year 2024
if [ $? -eq 0 ]; then
    echo "✅ RUSLE calculation completed for all years"
else
    echo "❌ RUSLE calculation failed"
    exit 1
fi
echo ""

# Step 8: Temporal analysis
echo "📊 Step 8: Temporal analysis..."
python scripts/08_temporal_analysis.py --start-year 2014 --end-year 2024
if [ $? -eq 0 ]; then
    echo "✅ Temporal analysis completed"
else
    echo "❌ Temporal analysis failed"
    exit 1
fi
echo ""

# Step 9: Final report
echo "📊 Step 9: Generating final report..."
python scripts/09_generate_report.py
if [ $? -eq 0 ]; then
    echo "✅ Report generated"
else
    echo "❌ Report generation failed"
    exit 1
fi
echo ""

echo "=========================================="
echo "✅ FULL 11-YEAR ANALYSIS COMPLETED!"
echo "Finished: $(date)"
echo "=========================================="
echo ""
echo "📂 Outputs:"
echo "   - Maps: outputs/maps/"
echo "   - Statistics: outputs/statistics/"
echo "   - Figures: outputs/figures/"
echo "   - Report: RUSLE_ANALYSIS_REPORT.md"
echo ""

