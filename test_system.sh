#!/bin/bash
# Complete System Test - Tests all scripts with 2024 data only
# Author: Bhavya Singh
# Date: 17 November 2025

set -e  # Exit on error

cd /home/ubuntuksh/Desktop/RUSLE
source venv/bin/activate

echo "=========================================="
echo "RUSLE COMPLETE SYSTEM TEST"
echo "Testing with year 2024 only"
echo "=========================================="
echo ""

# Test 01: Data Preparation
echo "📋 [1/9] Testing Data Preparation..."
python scripts/01_data_preparation.py > /dev/null 2>&1 && echo "   ✅ PASSED" || echo "   ❌ FAILED"

# Test 02: LS Factor
echo "📋 [2/9] Testing LS Factor..."
python scripts/02_calculate_ls_factor.py > /dev/null 2>&1 && echo "   ✅ PASSED" || echo "   ❌ FAILED"

# Test 03: K Factor
echo "📋 [3/9] Testing K Factor..."
python scripts/03_calculate_k_factor.py > /dev/null 2>&1 && echo "   ✅ PASSED" || echo "   ❌ FAILED"

# Test 04: R Factor
echo "📋 [4/9] Testing R Factor (2024)..."
python scripts/04_calculate_r_factor.py --start-year 2024 --end-year 2024 > /dev/null 2>&1 && echo "   ✅ PASSED" || echo "   ❌ FAILED"

# Test 05: C Factor  
echo "📋 [5/9] Testing C Factor (2024)..."
python scripts/05_calculate_c_factor.py --start-year 2024 --end-year 2024 > /dev/null 2>&1 && echo "   ✅ PASSED" || echo "   ❌ FAILED"

# Test 06: P Factor
echo "📋 [6/9] Testing P Factor (2024)..."
python scripts/06_calculate_p_factor.py --start-year 2024 --end-year 2024 > /dev/null 2>&1 && echo "   ✅ PASSED" || echo "   ❌ FAILED"

# Test 07: RUSLE Calculation
echo "📋 [7/9] Testing RUSLE Calculation (2024)..."
python scripts/07_calculate_rusle.py --start-year 2024 --end-year 2024 > /dev/null 2>&1 && echo "   ✅ PASSED" || echo "   ❌ FAILED"

# Test 08: Temporal Analysis
echo "📋 [8/9] Testing Temporal Analysis..."
python scripts/08_temporal_analysis.py --start-year 2024 --end-year 2024 > /dev/null 2>&1 && echo "   ✅ PASSED" || echo "   ❌ FAILED"

# Test 09: Report Generation
echo "📋 [9/9] Testing Report Generation..."
python scripts/09_generate_report.py > /dev/null 2>&1 && echo "   ✅ PASSED" || echo "   ❌ FAILED"

echo ""
echo "=========================================="
echo "SYSTEM TEST COMPLETE"
echo "=========================================="
echo ""
echo "📂 Check outputs:"
echo "   - Maps: outputs/maps/"
echo "   - Statistics: outputs/statistics/"
echo "   - Figures: outputs/figures/"
echo "   - Logs: outputs/logs/"
