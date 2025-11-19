#!/bin/bash
# Full 11-year RUSLE Analysis (2014-2024)
# This runs all scripts in sequence

cd /home/ubuntuksh/Desktop/RUSLE
source venv/bin/activate

echo "========================================"
echo "RUSLE Full Analysis: 2014-2024"
echo "Started: $(date)"
echo "========================================"

# Step 1: Data Preparation (one-time)
echo ""
echo "[1/9] Data Preparation..."
python scripts/01_data_preparation.py
if [ $? -ne 0 ]; then
    echo "❌ Step 1 failed!"
    exit 1
fi

# Step 2: LS Factor (one-time, static)
echo ""
echo "[2/9] Calculating LS Factor..."
python scripts/02_calculate_ls_factor.py
if [ $? -ne 0 ]; then
    echo "❌ Step 2 failed!"
    exit 1
fi

# Step 3: K Factor (one-time, static)
echo ""
echo "[3/9] Calculating K Factor..."
python scripts/03_calculate_k_factor.py
if [ $? -ne 0 ]; then
    echo "❌ Step 3 failed!"
    exit 1
fi

# Step 4: R Factor (11 years: 2014-2024)
echo ""
echo "[4/9] Calculating R Factor for 2014-2024..."
python scripts/04_calculate_r_factor.py --start-year 2014 --end-year 2024
if [ $? -ne 0 ]; then
    echo "❌ Step 4 failed!"
    exit 1
fi

# Step 5: C Factor (11 years: 2014-2024)
echo ""
echo "[5/9] Calculating C Factor for 2014-2024..."
python scripts/05_calculate_c_factor.py --start-year 2014 --end-year 2024
if [ $? -ne 0 ]; then
    echo "❌ Step 5 failed!"
    exit 1
fi

# Step 6: P Factor (11 years: 2014-2024)
echo ""
echo "[6/9] Calculating P Factor for 2014-2024..."
python scripts/06_calculate_p_factor.py --start-year 2014 --end-year 2024
if [ $? -ne 0 ]; then
    echo "❌ Step 6 failed!"
    exit 1
fi

# Step 7: RUSLE Calculation (11 years: 2014-2024)
echo ""
echo "[7/9] Calculating RUSLE for 2014-2024..."
python scripts/07_calculate_rusle.py --start-year 2014 --end-year 2024
if [ $? -ne 0 ]; then
    echo "❌ Step 7 failed!"
    exit 1
fi

# Step 8: Temporal Analysis
echo ""
echo "[8/9] Temporal Analysis..."
python scripts/08_temporal_analysis.py --start-year 2014 --end-year 2024
if [ $? -ne 0 ]; then
    echo "❌ Step 8 failed!"
    exit 1
fi

# Step 9: Report Generation
echo ""
echo "[9/9] Generating Report..."
python scripts/09_generate_report.py
if [ $? -ne 0 ]; then
    echo "❌ Step 9 failed!"
    exit 1
fi

echo ""
echo "========================================"
echo "✅ FULL ANALYSIS COMPLETED!"
echo "Finished: $(date)"
echo "========================================"
echo ""
echo "📂 Outputs:"
echo "   - Maps: outputs/maps/"
echo "   - Statistics: outputs/statistics/"
echo "   - Figures: outputs/figures/"
echo "   - Report: RUSLE_ANALYSIS_REPORT.md"
