"""
Color Configuration for RUSLE Analysis
Mula-Mutha Catchment (2016-2025)

Standardized color palette for soil erosion/degradation visualization
across all outputs: maps, figures, dashboards, and reports.
"""

# ============================================================================
# SOIL EROSION/DEGRADATION COLOR PALETTE
# ============================================================================

# Official color scheme for soil erosion severity classification
EROSION_COLORS = {
    'very_low': '#006837',      # Dark Green
    'low': '#7CB342',           # Light Green
    'moderate': '#FFEB3B',      # Yellow
    'high': '#FF9800',          # Orange
    'very_high': '#D32F2F'      # Red
}

# Color palette as list (for matplotlib, plotly)
EROSION_PALETTE = [
    '#006837',  # Very Low - Dark Green
    '#7CB342',  # Low - Light Green
    '#FFEB3B',  # Moderate - Yellow
    '#FF9800',  # High - Orange
    '#D32F2F'   # Very High - Red
]

# Color palette as hex string (for some plotting libraries)
EROSION_PALETTE_HEX = '#006837,#7CB342,#FFEB3B,#FF9800,#D32F2F'

# Category labels
EROSION_CATEGORIES = [
    'Very Low Degradation',
    'Low Degradation',
    'Moderate Degradation',
    'High Degradation',
    'Very High Degradation'
]

# Category labels (short version)
EROSION_CATEGORIES_SHORT = [
    'Very Low',
    'Low',
    'Moderate',
    'High',
    'Very High'
]

# ============================================================================
# EROSION CLASSIFICATION THRESHOLDS (t/ha/year)
# ============================================================================

# Standard RUSLE classification thresholds
EROSION_THRESHOLDS = {
    'very_low': (0, 5),          # 0-5 t/ha/year
    'low': (5, 10),              # 5-10 t/ha/year
    'moderate': (10, 20),        # 10-20 t/ha/year
    'high': (20, 40),            # 20-40 t/ha/year
    'very_high': (40, float('inf'))  # >40 t/ha/year
}

# Threshold values as list (for classification)
THRESHOLD_VALUES = [0, 5, 10, 20, 40]

# ============================================================================
# COLOR MAPPINGS FOR OTHER FACTORS
# ============================================================================

# DEM/Elevation colors (terrain)
DEM_COLORS = ['blue', 'green', 'yellow', 'orange', 'red', 'brown']
DEM_COLORMAP = 'terrain'

# Slope colors (for LS-Factor)
SLOPE_COLORMAP = 'YlOrRd'  # Yellow-Orange-Red
SLOPE_COLORS = ['#FFFFCC', '#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C', '#FC4E2A', '#E31A1C', '#BD0026']

# Rainfall (R-Factor) colors
RAINFALL_COLORMAP = 'Blues'
RAINFALL_COLORS = ['#F7FBFF', '#DEEBF7', '#C6DBEF', '#9ECAE1', '#6BAED6', '#4292C6', '#2171B5', '#084594']

# NDVI/Vegetation (C-Factor) colors
NDVI_COLORMAP = 'RdYlGn'  # Red-Yellow-Green
VEGETATION_COLORS = ['#A50026', '#D73027', '#F46D43', '#FDAE61', '#FEE08B', '#FFFFBF', '#D9EF8B', '#A6D96A', '#66BD63', '#1A9850', '#006837']

# Soil (K-Factor) colors
SOIL_COLORMAP = 'YlOrBr'  # Yellow-Orange-Brown
SOIL_COLORS = ['#FFFFE5', '#FFF7BC', '#FEE391', '#FEC44F', '#FE9929', '#EC7014', '#CC4C02', '#8C2D04']

# ============================================================================
# MATPLOTLIB COLOR CONFIGURATION
# ============================================================================

def get_erosion_cmap():
    """
    Create matplotlib colormap for erosion classification
    
    Returns:
        matplotlib.colors.ListedColormap: Custom colormap
    """
    from matplotlib.colors import ListedColormap
    return ListedColormap(EROSION_PALETTE, name='erosion')

def get_erosion_cmap_continuous():
    """
    Create continuous matplotlib colormap for erosion
    
    Returns:
        matplotlib.colors.LinearSegmentedColormap: Continuous colormap
    """
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list('erosion_continuous', EROSION_PALETTE)

# ============================================================================
# PLOTLY COLOR CONFIGURATION
# ============================================================================

PLOTLY_EROSION_SCALE = [
    [0.0, '#006837'],    # Very Low - Dark Green
    [0.25, '#7CB342'],   # Low - Light Green
    [0.5, '#FFEB3B'],    # Moderate - Yellow
    [0.75, '#FF9800'],   # High - Orange
    [1.0, '#D32F2F']     # Very High - Red
]

# ============================================================================
# FOLIUM/WEB MAP COLOR CONFIGURATION
# ============================================================================

FOLIUM_EROSION_COLORMAP = {
    'colors': EROSION_PALETTE,
    'vmin': 0,
    'vmax': 100,  # Will be adjusted based on actual max erosion
    'caption': 'Soil Erosion (t/ha/year)'
}

# ============================================================================
# CLASSIFICATION FUNCTION
# ============================================================================

def classify_erosion(erosion_value):
    """
    Classify erosion value into category
    
    Args:
        erosion_value (float): Erosion rate in t/ha/year
        
    Returns:
        tuple: (category_name, color_hex, category_index)
    """
    if erosion_value < 5:
        return ('Very Low Degradation', '#006837', 0)
    elif erosion_value < 10:
        return ('Low Degradation', '#7CB342', 1)
    elif erosion_value < 20:
        return ('Moderate Degradation', '#FFEB3B', 2)
    elif erosion_value < 40:
        return ('High Degradation', '#FF9800', 3)
    else:
        return ('Very High Degradation', '#D32F2F', 4)

def get_color_for_value(erosion_value):
    """
    Get color for a specific erosion value
    
    Args:
        erosion_value (float): Erosion rate in t/ha/year
        
    Returns:
        str: Hex color code
    """
    _, color, _ = classify_erosion(erosion_value)
    return color

# ============================================================================
# LEGEND CONFIGURATION
# ============================================================================

LEGEND_CONFIG = {
    'title': 'Soil Degradation',
    'categories': [
        {'name': 'Very Low Degradation', 'color': '#006837', 'range': '0-5 t/ha/year'},
        {'name': 'Low Degradation', 'color': '#7CB342', 'range': '5-10 t/ha/year'},
        {'name': 'Moderate Degradation', 'color': '#FFEB3B', 'range': '10-20 t/ha/year'},
        {'name': 'High Degradation', 'color': '#FF9800', 'range': '20-40 t/ha/year'},
        {'name': 'Very High Degradation', 'color': '#D32F2F', 'range': '>40 t/ha/year'}
    ]
}

# ============================================================================
# HTML/CSS LEGEND (for dashboards and reports)
# ============================================================================

HTML_LEGEND = """
<div style="font-family: Arial, sans-serif; padding: 10px; background-color: white; border: 1px solid #ccc; border-radius: 5px;">
    <h4 style="margin: 0 0 10px 0; font-size: 14px;">Soil Degradation Color Legend</h4>
    <table style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 5px;"><span style="display: inline-block; width: 20px; height: 20px; background-color: #006837; border: 1px solid #333;"></span></td>
            <td style="padding: 5px; font-size: 12px;">Very Low Degradation (0-5 t/ha/year)</td>
        </tr>
        <tr>
            <td style="padding: 5px;"><span style="display: inline-block; width: 20px; height: 20px; background-color: #7CB342; border: 1px solid #333;"></span></td>
            <td style="padding: 5px; font-size: 12px;">Low Degradation (5-10 t/ha/year)</td>
        </tr>
        <tr>
            <td style="padding: 5px;"><span style="display: inline-block; width: 20px; height: 20px; background-color: #FFEB3B; border: 1px solid #333;"></span></td>
            <td style="padding: 5px; font-size: 12px;">Moderate Degradation (10-20 t/ha/year)</td>
        </tr>
        <tr>
            <td style="padding: 5px;"><span style="display: inline-block; width: 20px; height: 20px; background-color: #FF9800; border: 1px solid #333;"></span></td>
            <td style="padding: 5px; font-size: 12px;">High Degradation (20-40 t/ha/year)</td>
        </tr>
        <tr>
            <td style="padding: 5px;"><span style="display: inline-block; width: 20px; height: 20px; background-color: #D32F2F; border: 1px solid #333;"></span></td>
            <td style="padding: 5px; font-size: 12px;">Very High Degradation (>40 t/ha/year)</td>
        </tr>
    </table>
</div>
"""

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
USAGE EXAMPLES:

1. Matplotlib:
    from color_config import EROSION_PALETTE, get_erosion_cmap
    plt.imshow(erosion_data, cmap=get_erosion_cmap())
    
2. Plotly:
    from color_config import PLOTLY_EROSION_SCALE
    fig = go.Figure(data=go.Heatmap(z=data, colorscale=PLOTLY_EROSION_SCALE))
    
3. Classification:
    from color_config import classify_erosion
    category, color, idx = classify_erosion(15.5)  # Returns ('Moderate Degradation', '#FFEB3B', 2)
    
4. Folium:
    from color_config import EROSION_PALETTE
    colormap = LinearColormap(colors=EROSION_PALETTE, vmin=0, vmax=50)
"""

if __name__ == "__main__":
    # Test color configuration
    print("="*80)
    print("RUSLE EROSION COLOR PALETTE")
    print("="*80)
    
    for i, (cat, color) in enumerate(zip(EROSION_CATEGORIES, EROSION_PALETTE)):
        print(f"{i+1}. {cat:30s} : {color}")
    
    print("\n" + "="*80)
    print("CLASSIFICATION EXAMPLES")
    print("="*80)
    
    test_values = [2.5, 7.8, 15.3, 28.9, 55.2]
    for val in test_values:
        cat, color, idx = classify_erosion(val)
        print(f"Erosion: {val:6.1f} t/ha/year → {cat:30s} ({color})")
    
    print("\n" + "="*80)
    print("✅ Color configuration loaded successfully!")
    print("="*80)
