#!/bin/bash
# RUSLE Project - Installation and Setup Script
# Author: Bhavya Singh
# Date: 17 November 2025

echo "=========================================="
echo "RUSLE Project - Installation & Setup"
echo "Mula-Mutha Catchment (2014-2024)"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    echo -e "${RED}❌ Python 3.9+ required${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python version OK${NC}"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠️  Virtual environment already exists${NC}"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✅ Virtual environment activated${NC}"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel
echo -e "${GREEN}✅ Pip upgraded${NC}"
echo ""

# Install GDAL dependencies (system-level)
echo "Installing system dependencies..."
echo "This may require sudo password..."

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    OS=$(uname -s)
fi

case "$OS" in
    ubuntu|debian)
        echo "Detected Ubuntu/Debian"
        sudo apt-get update
        sudo apt-get install -y \
            gdal-bin \
            libgdal-dev \
            python3-gdal \
            libspatialindex-dev \
            build-essential
        ;;
    fedora|rhel|centos)
        echo "Detected Fedora/RHEL/CentOS"
        sudo dnf install -y \
            gdal \
            gdal-devel \
            python3-gdal \
            spatialindex-devel \
            gcc \
            gcc-c++
        ;;
    *)
        echo -e "${YELLOW}⚠️  Unknown OS. Please install GDAL manually.${NC}"
        ;;
esac

echo -e "${GREEN}✅ System dependencies installed${NC}"
echo ""

# Install Python packages
echo "Installing Python packages from requirements.txt..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All Python packages installed successfully${NC}"
else
    echo -e "${RED}❌ Some packages failed to install${NC}"
    echo "Trying individual installation..."
    
    # Core packages first
    pip install numpy scipy pandas
    pip install geopandas rasterio fiona shapely pyproj
    pip install matplotlib seaborn
    pip install earthengine-api geemap
    pip install tqdm python-dotenv
    
    # Optional packages
    pip install richdem --no-deps 2>/dev/null || echo "richdem skipped (optional)"
    pip install whitebox 2>/dev/null || echo "whitebox skipped (optional)"
fi
echo ""

# Verify key imports
echo "Verifying installations..."
python3 << EOF
import sys
packages = {
    'numpy': 'NumPy',
    'pandas': 'Pandas',
    'geopandas': 'GeoPandas',
    'rasterio': 'Rasterio',
    'matplotlib': 'Matplotlib',
    'ee': 'Earth Engine API'
}

all_ok = True
for module, name in packages.items():
    try:
        __import__(module)
        print(f"✅ {name}")
    except ImportError:
        print(f"❌ {name} - FAILED")
        all_ok = False

sys.exit(0 if all_ok else 1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All key packages verified${NC}"
else
    echo -e "${RED}❌ Some packages missing${NC}"
fi
echo ""

# Create directory structure
echo "Creating directory structure..."
python3 << EOF
from pathlib import Path

dirs = [
    'data',
    'outputs/maps',
    'outputs/statistics',
    'outputs/figures',
    'outputs/logs',
    'temp/factors'
]

for d in dirs:
    Path(d).mkdir(parents=True, exist_ok=True)
    print(f"✅ {d}")
EOF
echo ""

# Google Earth Engine setup
echo "=========================================="
echo "Google Earth Engine Setup"
echo "=========================================="
echo ""
echo "To use Google Earth Engine, you need to authenticate."
echo "Run the following command manually:"
echo ""
echo -e "${YELLOW}  earthengine authenticate${NC}"
echo ""
echo "This will open a browser window for authentication."
echo ""

# Summary
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Authenticate with Google Earth Engine:"
echo "   $ earthengine authenticate"
echo ""
echo "2. Activate virtual environment (if not already):"
echo "   $ source venv/bin/activate"
echo ""
echo "3. Run data preparation:"
echo "   $ python scripts/01_data_preparation.py"
echo ""
echo "4. Check outputs in:"
echo "   - outputs/figures/"
echo "   - outputs/logs/"
echo ""
echo "=========================================="
