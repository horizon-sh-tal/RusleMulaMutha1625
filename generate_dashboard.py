"""
Generate Interactive HTML Dashboard for RUSLE Analysis
Creates a standalone HTML file with charts and statistics

Author: Bhavya Singh
Date: 17 November 2025
"""

import pandas as pd
import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
STATS_DIR = BASE_DIR / "outputs" / "statistics"
OUTPUT_FILE = BASE_DIR / "RUSLE_Dashboard.html"

# Load data
rusle_stats = pd.read_csv(STATS_DIR / "rusle_annual_statistics.csv")
temporal_stats = pd.read_csv(STATS_DIR / "temporal_statistics.csv")
r_stats = pd.read_csv(STATS_DIR / "r_factor_annual_statistics.csv")
c_stats = pd.read_csv(STATS_DIR / "c_factor_annual_statistics.csv")
p_stats = pd.read_csv(STATS_DIR / "p_factor_annual_statistics.csv")

# Prepare data for JavaScript
years = rusle_stats['year'].astype(int).tolist()
mean_erosion = rusle_stats['mean'].round(1).tolist()
median_erosion = rusle_stats['median'].round(1).tolist()
severe_pct = rusle_stats['Severe'].round(1).tolist()

# Generate HTML
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RUSLE Soil Erosion Dashboard - Mula-Mutha Catchment</title>
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            overflow-x: hidden;
        }}
        
        .container {{
            max-width: 100%;
            width: 1920px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .year-selector {{
            background: #ecf0f1;
            padding: 20px;
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 10px;
        }}
        
        .year-btn {{
            background: #3498db;
            color: white;
            border: none;
            padding: 15px 25px;
            font-size: 16px;
            font-weight: bold;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .year-btn:hover {{
            background: #2980b9;
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.2);
        }}
        
        .year-btn.active {{
            background: #e74c3c;
            transform: scale(1.05);
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-card.card-1 {{ background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); }}
        .stat-card.card-2 {{ background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); }}
        .stat-card.card-3 {{ background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%); }}
        .stat-card.card-4 {{ background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%); }}
        .stat-card.card-5 {{ background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%); }}
        
        .stat-card h3 {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
        }}
        
        .stat-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .charts-section {
            padding: 30px;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 30px;
        }
        
        .chart-container {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .chart-container.full-width {
            grid-column: 1 / -1;
        }
        
        .footer {{
            background: #2c3e50;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌍 RUSLE Soil Erosion Analysis Dashboard</h1>
            <p>Mula-Mutha River Catchment, Pune | 2014-2024 | MSc Geoinformatics Project</p>
        </div>
        
        <div class="year-selector">
            <button class="year-btn" onclick="showYear(2014, this)">2014</button>
            <button class="year-btn" onclick="showYear(2015, this)">2015</button>
            <button class="year-btn" onclick="showYear(2016, this)">2016</button>
            <button class="year-btn" onclick="showYear(2017, this)">2017</button>
            <button class="year-btn" onclick="showYear(2018, this)">2018</button>
            <button class="year-btn" onclick="showYear(2019, this)">2019</button>
            <button class="year-btn" onclick="showYear(2020, this)">2020</button>
            <button class="year-btn" onclick="showYear(2021, this)">2021</button>
            <button class="year-btn" onclick="showYear(2022, this)">2022</button>
            <button class="year-btn" onclick="showYear(2023, this)">2023</button>
            <button class="year-btn active" onclick="showYear(2024, this)">2024</button>
            <button class="year-btn" style="background:#e74c3c" onclick="showAllYears(this)">ALL YEARS</button>
        </div>
        
        <div class="stats-grid" id="statsGrid">
            <div class="stat-card card-1">
                <h3>Year</h3>
                <div class="value" id="statYear">2024</div>
            </div>
            <div class="stat-card card-2">
                <h3>Mean Erosion (t/ha/yr)</h3>
                <div class="value" id="statMean">---</div>
            </div>
            <div class="stat-card card-3">
                <h3>Median Erosion (t/ha/yr)</h3>
                <div class="value" id="statMedian">---</div>
            </div>
            <div class="stat-card card-4">
                <h3>Maximum (t/ha/yr)</h3>
                <div class="value" id="statMax">---</div>
            </div>
            <div class="stat-card card-5">
                <h3>Severe Erosion (% area)</h3>
                <div class="value" id="statSevere">---</div>
            </div>
        </div>
        
        <div class="map-section" style="padding: 30px; background: white; margin: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h2 style="text-align: center; color: #2c3e50; margin-bottom: 20px;">📍 Soil Erosion Risk Map</h2>
            <div style="text-align: center; margin-bottom: 20px;">
                <img id="erosionMap" src="outputs/web_maps/soil_loss_2024.png" 
                     style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);" 
                     alt="Soil Erosion Map">
            </div>
            <p style="text-align: center; color: #7f8c8d; font-size: 14px;">
                Click on a year button above to view the corresponding erosion risk map
            </p>
        </div>
        
        <div class="charts-section">
            <div class="chart-container">
                <div id="erosionClassChart"></div>
            </div>
            <div class="chart-container">
                <div id="comparisonChart"></div>
            </div>
            <div class="chart-container full-width">
                <div id="temporalTrendChart"></div>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2025 RUSLE Analysis Dashboard | Generated using Python & Plotly.js</p>
            <p>Data Source: Google Earth Engine (CHIRPS, Sentinel-2, Dynamic World, OpenLandMap)</p>
        </div>
    </div>
    
    <script>
        // Data from Python
        const data = {json.dumps({
            'years': years,
            'rusle_stats': rusle_stats.to_dict('records'),
            'r_stats': r_stats.to_dict('records'),
            'c_stats': c_stats.to_dict('records'),
            'p_stats': p_stats.to_dict('records')
        })};
        
        function showYear(year, element) {{
            // Update active button
            document.querySelectorAll('.year-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            if (element) element.classList.add('active');
            
            // Find year data
            const yearData = data.rusle_stats.find(d => d.year === year);
            if (!yearData) return;
            
            // Update stats cards
            document.getElementById('statYear').textContent = year;
            document.getElementById('statMean').textContent = yearData.mean.toFixed(1);
            document.getElementById('statMedian').textContent = yearData.median.toFixed(1);
            document.getElementById('statMax').textContent = yearData.max.toFixed(0);
            document.getElementById('statSevere').textContent = yearData.Severe.toFixed(1);
            
            // Update map image
            document.getElementById('erosionMap').src = `outputs/web_maps/soil_loss_${{year}}.png`;
            
            // Update charts
            updateErosionClassChart(yearData);
            updateTemporalTrendChart(year);
            updateComparisonChart(year);
        }}
        
        function showAllYears(element) {{
            document.querySelectorAll('.year-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            if (element) element.classList.add('active');
            
            // Calculate overall statistics
            const avgMean = data.rusle_stats.reduce((sum, d) => sum + d.mean, 0) / data.rusle_stats.length;
            const avgMedian = data.rusle_stats.reduce((sum, d) => sum + d.median, 0) / data.rusle_stats.length;
            const maxVal = Math.max(...data.rusle_stats.map(d => d.max));
            const avgSevere = data.rusle_stats.reduce((sum, d) => sum + d.Severe, 0) / data.rusle_stats.length;
            
            document.getElementById('statYear').textContent = 'ALL';
            document.getElementById('statMean').textContent = avgMean.toFixed(1);
            document.getElementById('statMedian').textContent = avgMedian.toFixed(1);
            document.getElementById('statMax').textContent = maxVal.toFixed(0);
            document.getElementById('statSevere').textContent = avgSevere.toFixed(1);
            
            // Show 2024 map for ALL YEARS view
            document.getElementById('erosionMap').src = 'outputs/web_maps/soil_loss_2024.png';
            
            updateAllYearsCharts();
        }}
        
        function updateErosionClassChart(yearData) {{
            const trace = {{
                x: ['Very Low<br>(<5)', 'Low<br>(5-10)', 'Moderate<br>(10-20)', 'High<br>(20-40)', 'Very High<br>(>40)'],
                y: [yearData.Slight, yearData.Moderate, yearData.High, yearData['Very High'], yearData.Severe],
                type: 'bar',
                marker: {{
                    color: ['#006837', '#7CB342', '#FFEB3B', '#FF9800', '#D32F2F'],  // New soil degradation colors
                    line: {{color: 'black', width: 2}}
                }},
                text: [yearData.Slight.toFixed(1), yearData.Moderate.toFixed(1), 
                       yearData.High.toFixed(1), yearData['Very High'].toFixed(1), 
                       yearData.Severe.toFixed(1)],
                textposition: 'outside',
                textfont: {{size: 14, weight: 'bold'}}
            }};
            
            const layout = {{
                title: {{
                    text: `Erosion Class Distribution - ${{yearData.year}}`,
                    font: {{size: 20, weight: 'bold'}}
                }},
                xaxis: {{title: 'Erosion Class', titlefont: {{size: 14, weight: 'bold'}}}},
                yaxis: {{title: 'Area (%)', titlefont: {{size: 14, weight: 'bold'}}}},
                plot_bgcolor: '#f8f9fa',
                paper_bgcolor: '#f8f9fa'
            }};
            
            Plotly.newPlot('erosionClassChart', [trace], layout, {{responsive: true}});
        }}
        
        function updateTemporalTrendChart(currentYear) {{
            const trace1 = {{
                x: data.years,
                y: data.rusle_stats.map(d => d.mean),
                mode: 'lines+markers',
                name: 'Mean Erosion',
                line: {{color: '#3498db', width: 3}},
                marker: {{size: 10, color: '#3498db'}}
            }};
            
            const trace2 = {{
                x: [currentYear],
                y: [data.rusle_stats.find(d => d.year === currentYear).mean],
                mode: 'markers',
                name: `Year ${{currentYear}}`,
                marker: {{size: 20, color: '#e74c3c', symbol: 'star'}}
            }};
            
            const layout = {{
                title: {{
                    text: 'Temporal Trend (2014-2024)',
                    font: {{size: 20, weight: 'bold'}}
                }},
                xaxis: {{title: 'Year', titlefont: {{size: 14, weight: 'bold'}}}},
                yaxis: {{title: 'Mean Soil Loss (t/ha/yr)', titlefont: {{size: 14, weight: 'bold'}}}},
                plot_bgcolor: '#f8f9fa',
                paper_bgcolor: '#f8f9fa',
                showlegend: true
            }};
            
            Plotly.newPlot('temporalTrendChart', [trace1, trace2], layout, {{responsive: true}});
        }}
        
        function updateComparisonChart(year) {{
            const yearData = data.rusle_stats.find(d => d.year === year);
            const rData = data.r_stats.find(d => d.year === year);
            const cData = data.c_stats.find(d => d.year === year);
            const pData = data.p_stats.find(d => d.year === year);
            
            const trace = {{
                x: ['R-Factor<br>(Rainfall)', 'K-Factor<br>(Soil)', 'LS-Factor<br>(Slope)', 
                    'C-Factor<br>(Vegetation)', 'P-Factor<br>(Conservation)', 'Soil Loss<br>(Final)'],
                y: [
                    rData ? rData.r_mean : 0,
                    0.018,  // K-factor is static
                    131.8,  // LS-factor is static
                    cData ? cData.c_mean : 0,
                    pData ? pData.p_mean : 0,
                    yearData.mean
                ],
                type: 'bar',
                marker: {{
                    color: ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#e67e22'],
                    line: {{color: 'black', width: 2}}
                }},
                text: [
                    rData ? rData.r_mean.toFixed(0) : '0',
                    '0.018',
                    '131.8',
                    cData ? cData.c_mean.toFixed(3) : '0',
                    pData ? pData.p_mean.toFixed(2) : '0',
                    yearData.mean.toFixed(1)
                ],
                textposition: 'outside',
                textfont: {{size: 12, weight: 'bold'}}
            }};
            
            const layout = {{
                title: {{
                    text: `RUSLE Factors - ${{year}}`,
                    font: {{size: 20, weight: 'bold'}}
                }},
                xaxis: {{title: 'Factor', titlefont: {{size: 14, weight: 'bold'}}}},
                yaxis: {{title: 'Value', titlefont: {{size: 14, weight: 'bold'}}, type: 'log'}},
                plot_bgcolor: '#f8f9fa',
                paper_bgcolor: '#f8f9fa'
            }};
            
            Plotly.newPlot('comparisonChart', [trace], layout, {{responsive: true}});
        }}
        
        function updateAllYearsCharts() {{
            // Erosion class average
            const avgSlight = data.rusle_stats.reduce((sum, d) => sum + d.Slight, 0) / data.rusle_stats.length;
            const avgModerate = data.rusle_stats.reduce((sum, d) => sum + d.Moderate, 0) / data.rusle_stats.length;
            const avgHigh = data.rusle_stats.reduce((sum, d) => sum + d.High, 0) / data.rusle_stats.length;
            const avgVeryHigh = data.rusle_stats.reduce((sum, d) => sum + d['Very High'], 0) / data.rusle_stats.length;
            const avgSevere = data.rusle_stats.reduce((sum, d) => sum + d.Severe, 0) / data.rusle_stats.length;
            
            const trace1 = {{
                x: ['Very Low<br>(<5)', 'Low<br>(5-10)', 'Moderate<br>(10-20)', 'High<br>(20-40)', 'Very High<br>(>40)'],
                y: [avgSlight, avgModerate, avgHigh, avgVeryHigh, avgSevere],
                type: 'bar',
                marker: {{
                    color: ['#006837', '#7CB342', '#FFEB3B', '#FF9800', '#D32F2F'],  // New soil degradation colors
                    line: {{color: 'black', width: 2}}
                }},
                text: [avgSlight.toFixed(1), avgModerate.toFixed(1), 
                       avgHigh.toFixed(1), avgVeryHigh.toFixed(1), 
                       avgSevere.toFixed(1)],
                textposition: 'outside',
                textfont: {{size: 14, weight: 'bold'}}
            }};
            
            Plotly.newPlot('erosionClassChart', [trace1], {{
                title: {{text: 'Average Erosion Class Distribution (2014-2024)', font: {{size: 20}}}},
                xaxis: {{title: 'Erosion Class'}},
                yaxis: {{title: 'Area (%)'}},
                plot_bgcolor: '#f8f9fa',
                paper_bgcolor: '#f8f9fa'
            }}, {{responsive: true}});
            
            // All years comparison
            const trace2 = {{
                x: data.years,
                y: data.rusle_stats.map(d => d.mean),
                type: 'bar',
                name: 'Mean',
                marker: {{color: '#e74c3c'}}
            }};
            
            const trace3 = {{
                x: data.years,
                y: data.rusle_stats.map(d => d.median),
                type: 'bar',
                name: 'Median',
                marker: {{color: '#2ecc71'}}
            }};
            
            Plotly.newPlot('temporalTrendChart', [trace2, trace3], {{
                title: {{text: 'Mean vs Median Erosion (2014-2024)', font: {{size: 20}}}},
                xaxis: {{title: 'Year'}},
                yaxis: {{title: 'Soil Loss (t/ha/yr)'}},
                plot_bgcolor: '#f8f9fa',
                paper_bgcolor: '#f8f9fa',
                barmode: 'group'
            }}, {{responsive: true}});
            
            // Severe erosion trend
            const trace4 = {{
                x: data.years,
                y: data.rusle_stats.map(d => d.Severe),
                mode: 'lines+markers',
                line: {{color: '#c0392b', width: 4}},
                marker: {{size: 12, color: '#e74c3c'}},
                fill: 'tozeroy',
                fillcolor: 'rgba(231, 76, 60, 0.2)'
            }};
            
            Plotly.newPlot('comparisonChart', [trace4], {{
                title: {{text: 'Severe Erosion Trend (>40 t/ha/yr)', font: {{size: 20}}}},
                xaxis: {{title: 'Year'}},
                yaxis: {{title: 'Severe Erosion (%)'}},
                plot_bgcolor: '#f8f9fa',
                paper_bgcolor: '#f8f9fa'
            }}, {{responsive: true}});
        }}
        
        // Initialize with 2024 on page load
        window.onload = function() {{
            showYear(2024, document.querySelector('.year-btn.active'));
        }};
    </script>
</body>
</html>
"""

# Write HTML file
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ Dashboard created: {OUTPUT_FILE}")
print(f"📊 Open this file in your web browser to view the dashboard")
