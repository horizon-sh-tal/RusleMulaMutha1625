#!/usr/bin/env python3
"""
Generate PNG images from GeoTIFF files for web dashboard
"""

import rasterio
from rasterio.plot import show
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import numpy as np
from pathlib import Path
import json

# Setup paths
OUTPUT_DIR = Path("outputs")
MAPS_DIR = OUTPUT_DIR / "maps"
WEB_MAPS_DIR = OUTPUT_DIR / "web_maps"
WEB_MAPS_DIR.mkdir(exist_ok=True)

# Color schemes for different maps
RUSLE_COLORS = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c', '#8e44ad']
RUSLE_BOUNDS = [0, 5, 10, 20, 40, 200]  # Erosion classes

def create_rusle_map(year):
    """Create soil loss map for a specific year"""
    input_file = MAPS_DIR / f"soil_loss_{year}.tif"
    output_file = WEB_MAPS_DIR / f"soil_loss_{year}.png"
    
    if not input_file.exists():
        print(f"⚠️  File not found: {input_file}")
        return None
    
    with rasterio.open(input_file) as src:
        data = src.read(1)
        
        # Mask nodata
        data = np.ma.masked_equal(data, -9999)
        data = np.ma.masked_equal(data, 0)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Create custom colormap
        cmap = colors.ListedColormap(RUSLE_COLORS)
        norm = colors.BoundaryNorm(RUSLE_BOUNDS, cmap.N)
        
        # Plot
        im = ax.imshow(data, cmap=cmap, norm=norm, interpolation='nearest')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, orientation='horizontal', 
                           pad=0.05, fraction=0.046)
        cbar.set_label('Soil Loss (t/ha/yr)', fontsize=14, weight='bold')
        cbar.set_ticks([2.5, 7.5, 15, 30, 100])
        cbar.ax.set_xticklabels(['0-5\nSlight', '5-10\nModerate', '10-20\nHigh', 
                                  '20-40\nVery High', '>40\nSevere'], fontsize=11)
        
        ax.set_title(f'Soil Erosion Risk Map - {year}', fontsize=16, weight='bold', pad=20)
        ax.axis('off')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"✅ Created: {output_file.name}")
        
        # Get bounds for later use
        bounds = src.bounds
        return {
            'year': year,
            'file': f'outputs/web_maps/soil_loss_{year}.png',
            'bounds': [[bounds.bottom, bounds.left], [bounds.top, bounds.right]]
        }

def create_factor_map(factor_name, year=None):
    """Create map for R, K, LS, C, or P factor"""
    if factor_name == 'LS':
        input_file = MAPS_DIR / "ls_factor.tif"
        output_file = WEB_MAPS_DIR / "ls_factor.png"
        title = "LS Factor (Topographic)"
        cmap = 'YlOrRd'
        vmin, vmax = 0, 50
    elif factor_name == 'K':
        input_file = MAPS_DIR / "k_factor.tif"
        output_file = WEB_MAPS_DIR / "k_factor.png"
        title = "K Factor (Soil Erodibility)"
        cmap = 'RdYlGn_r'
        vmin, vmax = 0.005, 0.07
    elif factor_name == 'R' and year:
        input_file = MAPS_DIR / f"r_factor_{year}.tif"
        output_file = WEB_MAPS_DIR / f"r_factor_{year}.png"
        title = f"R Factor (Rainfall Erosivity) - {year}"
        cmap = 'Blues'
        vmin, vmax = 200, 1200
    elif factor_name == 'C' and year:
        input_file = MAPS_DIR / f"c_factor_{year}.tif"
        output_file = WEB_MAPS_DIR / f"c_factor_{year}.png"
        title = f"C Factor (Vegetation Cover) - {year}"
        cmap = 'RdYlGn_r'
        vmin, vmax = 0, 1
    elif factor_name == 'P' and year:
        input_file = MAPS_DIR / f"p_factor_{year}.tif"
        output_file = WEB_MAPS_DIR / f"p_factor_{year}.png"
        title = f"P Factor (Conservation Practice) - {year}"
        cmap = 'RdYlGn_r'
        vmin, vmax = 0.1, 1.0
    else:
        return None
    
    if not input_file.exists():
        print(f"⚠️  File not found: {input_file}")
        return None
    
    with rasterio.open(input_file) as src:
        data = src.read(1)
        
        # Mask nodata
        data = np.ma.masked_equal(data, -9999)
        data = np.ma.masked_less_equal(data, 0)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Plot
        im = ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax, interpolation='nearest')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, orientation='horizontal', 
                           pad=0.05, fraction=0.046)
        cbar.set_label(title, fontsize=14, weight='bold')
        
        ax.set_title(title, fontsize=16, weight='bold', pad=20)
        ax.axis('off')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"✅ Created: {output_file.name}")
        
        bounds = src.bounds
        return {
            'factor': factor_name,
            'year': year,
            'file': str(output_file),
            'bounds': [[bounds.bottom, bounds.left], [bounds.top, bounds.right]]
        }

# Main execution
if __name__ == "__main__":
    print("🗺️  Generating web map images...")
    print()
    
    map_info = []
    
    # Generate soil loss maps for all years
    print("📊 Generating soil loss maps (2014-2024)...")
    for year in range(2014, 2025):
        info = create_rusle_map(year)
        if info:
            map_info.append(info)
    
    print()
    
    # Generate static factor maps
    print("🗺️  Generating factor maps...")
    create_factor_map('K')
    create_factor_map('LS')
    
    # Generate temporal factor maps
    print()
    print("📅 Generating temporal factor maps (2014-2024)...")
    for year in range(2014, 2025):
        create_factor_map('R', year)
        create_factor_map('C', year)
        create_factor_map('P', year)
    
    print()
    print("✅ All map images generated!")
    print(f"📁 Location: {WEB_MAPS_DIR}/")
