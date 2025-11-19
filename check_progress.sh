#!/bin/bash
# Monitor the progress of the 11-year RUSLE analysis

LOG_FILE="/home/ubuntuksh/Desktop/RUSLE/analysis_11year.log"

echo "=========================================="
echo "RUSLE 11-YEAR ANALYSIS PROGRESS"
echo "=========================================="
echo ""

# Check if analysis is running
if pgrep -f "run_11year_analysis.sh" > /dev/null; then
    echo "📊 Status: RUNNING ✅"
else
    echo "⚠️  Status: NOT RUNNING (may have completed or stopped)"
fi
echo ""

# Show current step
echo "Current Activity:"
tail -5 "$LOG_FILE" 2>/dev/null | grep -E "Step|Processing year|Calculating|Downloading" || echo "Check log file for details"
echo ""

# Count completed years for each factor
echo "Progress Summary:"
echo "-------------------"

# R-factor
r_count=$(ls temp/factors/r_factor_*.tif 2>/dev/null | wc -l)
echo "R-factor (Rainfall):     $r_count/11 years"

# C-factor  
c_count=$(ls temp/factors/c_factor_*.tif 2>/dev/null | wc -l)
echo "C-factor (Vegetation):   $c_count/11 years"

# P-factor
p_count=$(ls temp/factors/p_factor_*.tif 2>/dev/null | wc -l)
echo "P-factor (Conservation): $p_count/11 years"

# Soil loss maps
sl_count=$(ls outputs/maps/soil_loss_*.tif 2>/dev/null | wc -l)
echo "Soil Loss Maps:          $sl_count/11 years"

echo ""
echo "Recent Log (last 20 lines):"
echo "----------------------------"
tail -20 "$LOG_FILE" 2>/dev/null
echo ""
echo "To view full log: tail -f $LOG_FILE"
