# """
# Interactive RUSLE Analysis Dashboard
# Professional layout with table, map, and charts

# Author: Bhavya Singh  
# Date: 18 November 2025
# """

# import sys
# import tkinter as tk
# from tkinter import ttk
# import pandas as pd
# import matplotlib.pyplot as plt
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# from matplotlib.figure import Figure
# from pathlib import Path
# from PIL import Image, ImageTk

# # Paths
# BASE_DIR = Path(__file__).parent
# STATS_DIR = BASE_DIR / "outputs" / "statistics"
# MAPS_DIR = BASE_DIR / "outputs" / "maps"

# class RUSLEDashboard:
#     def __init__(self, window, container):
#         self.window = window 
#         self.root = container 
#         self.window.title("RUSLE Soil Erosion Dashboard - Mula-Mutha Catchment (2014-2024)")
#         self.window.state("zoomed")
#         self.window.configure(bg="#f5f5f5")

        
#         # Load data
#         self.load_data()
        
#         # Create UI
#         self.create_header()
#         self.create_year_selector()
#         self.create_data_table()
#         self.create_main_dashboard()
        
#         # Load initial year
#         self.update_display(2024)
    
#     def load_data(self):
#         """Load all statistics data"""
#         try:
#             self.rusle_stats = pd.read_csv(STATS_DIR / "rusle_annual_statistics.csv")
#         except Exception as e:
#             print(f"Error loading data: {e}")
#             sys.exit(1)
    
#     def create_header(self):
#         """Create header section"""
#         header = tk.Frame(self.root, bg='#2c3e50', height=70)
#         header.pack(fill=tk.X)
        
#         title = tk.Label(
#             header,
#             text="🌍 RUSLE Soil Erosion Analysis Dashboard",
#             font=('Arial', 22, 'bold'),
#             bg='#2c3e50',
#             fg='white'
#         )
#         title.pack(pady=10)
        
#         subtitle = tk.Label(
#             header,
#             text="Mula-Mutha River Catchment, Pune | 2014-2024 | MSc Geoinformatics Project",
#             font=('Arial', 11),
#             bg='#2c3e50',
#             fg='#ecf0f1'
#         )
#         subtitle.pack()
    
#     def create_year_selector(self):
#         """Create year selection panel"""
#         selector_frame = tk.Frame(self.root, bg='#ecf0f1', height=80)
#         selector_frame.pack(fill=tk.X, padx=20, pady=10)
        
#         tk.Label(
#             selector_frame,
#             text="Select Year:",
#             font=('Arial', 13, 'bold'),
#             bg='#ecf0f1'
#         ).pack(side=tk.LEFT, padx=10)
        
#         # Year buttons
#         years = sorted(self.rusle_stats['year'].unique())
#         for year in years:
#             btn = tk.Button(
#                 selector_frame,
#                 text=str(int(year)),
#                 font=('Arial', 11, 'bold'),
#                 bg='#3498db',
#                 fg='white',
#                 width=6,
#                 height=1,
#                 relief=tk.RAISED,
#                 command=lambda y=year: self.update_display(y)
#             )
#             btn.pack(side=tk.LEFT, padx=3)
        
#         # All years button
#         all_btn = tk.Button(
#             selector_frame,
#             text="ALL YEARS",
#             font=('Arial', 11, 'bold'),
#             bg='#e74c3c',
#             fg='white',
#             width=10,
#             height=1,
#             relief=tk.RAISED,
#             command=self.show_all_years
#         )
#         all_btn.pack(side=tk.LEFT, padx=5)
    
#     def create_data_table(self):
#         """Create data table showing all years statistics"""
#         table_frame = tk.LabelFrame(
#             self.root,
#             text="📊 Annual Statistics Summary",
#             font=('Arial', 12, 'bold'),
#             bg='white',
#             fg='#2c3e50',
#             relief=tk.RIDGE,
#             bd=3
#         )
#         table_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
#         # Create Treeview
#         columns = ('Year', 'Mean Erosion', 'Median Erosion', 'Maximum', 'Severe Erosion')
#         self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=5)
        
#         # Define columns
#         self.tree.heading('Year', text='Year')
#         self.tree.heading('Mean Erosion', text='Mean Erosion (t/ha/yr)')
#         self.tree.heading('Median Erosion', text='Median Erosion (t/ha/yr)')
#         self.tree.heading('Maximum', text='Maximum (t/ha/yr)')
#         self.tree.heading('Severe Erosion', text='Severe Erosion (%)')
        
#         self.tree.column('Year', width=80, anchor='center')
#         self.tree.column('Mean Erosion', width=180, anchor='center')
#         self.tree.column('Median Erosion', width=180, anchor='center')
#         self.tree.column('Maximum', width=180, anchor='center')
#         self.tree.column('Severe Erosion', width=180, anchor='center')
        
#         # Add scrollbar
#         scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
#         self.tree.configure(yscroll=scrollbar.set)
        
#         # Pack
#         self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
#         scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
#         # Populate table
#         for _, row in self.rusle_stats.iterrows():
#             values = (
#                 int(row['year']),
#                 f"{row['mean']:.2f}",
#                 f"{row['median']:.2f}",
#                 f"{row['max']:.2f}",
#                 f"{row['Severe']:.2f}"
#             )
#             self.tree.insert('', tk.END, values=values)
    
#     def create_main_dashboard(self):
#         """Create main dashboard with map and charts"""
#         main_container = tk.Frame(self.root, bg='#f5f5f5')
#         main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        
#         # Large Map at top
#         map_frame = tk.LabelFrame(
#             main_container,
#             text="🗺️ SOIL EROSION RISK MAP - MULA-MUTHA CATCHMENT",
#             font=('Arial', 15, 'bold'),
#             bg='white',
#             fg='#2c3e50',
#             relief=tk.RIDGE,
#             bd=4
#         )
#         map_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
#         self.map_label = tk.Label(map_frame, bg='white', relief=tk.SUNKEN, bd=2)
#         self.map_label.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
#         # Charts at bottom (3 charts side by side)
#         charts_container = tk.Frame(main_container, bg='#f5f5f5')
#         charts_container.pack(fill=tk.X)
        
#         # Pie chart
#         pie_frame = tk.LabelFrame(
#             charts_container,
#             text="📈 Erosion Class Distribution",
#             font=('Arial', 11, 'bold'),
#             bg='white',
#             fg='#2c3e50',
#             relief=tk.RIDGE,
#             bd=3
#         )
#         pie_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
#         self.pie_fig = Figure(figsize=(5, 3.5), facecolor='white')
#         self.pie_canvas = FigureCanvasTkAgg(self.pie_fig, master=pie_frame)
#         self.pie_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
#         # Mean trend
#         mean_frame = tk.LabelFrame(
#             charts_container,
#             text="📊 Mean Erosion Trend",
#             font=('Arial', 11, 'bold'),
#             bg='white',
#             fg='#2c3e50',
#             relief=tk.RIDGE,
#             bd=3
#         )
#         mean_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
#         self.mean_fig = Figure(figsize=(5, 3.5), facecolor='white')
#         self.mean_canvas = FigureCanvasTkAgg(self.mean_fig, master=mean_frame)
#         self.mean_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
#         # Median trend
#         median_frame = tk.LabelFrame(
#             charts_container,
#             text="📊 Median Erosion Trend",
#             font=('Arial', 11, 'bold'),
#             bg='white',
#             fg='#2c3e50',
#             relief=tk.RIDGE,
#             bd=3
#         )
#         median_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
#         self.median_fig = Figure(figsize=(5, 3.5), facecolor='white')
#         self.median_canvas = FigureCanvasTkAgg(self.median_fig, master=median_frame)
#         self.median_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
#     def update_display(self, year):
#         """Update dashboard for selected year"""
#         # Highlight row in table
#         for item in self.tree.get_children():
#             values = self.tree.item(item)['values']
#             if int(values[0]) == year:
#                 self.tree.selection_set(item)
#                 self.tree.see(item)
#                 break
        
#         # Update charts and map
#         self.plot_pie_chart(year)
#         self.plot_trends(year)
#         self.load_map_image(year)
    
#     def plot_pie_chart(self, year):
#         """Plot pie chart for erosion classes"""
#         self.pie_fig.clear()
#         ax = self.pie_fig.add_subplot(111)
        
#         year_data = self.rusle_stats[self.rusle_stats['year'] == year].iloc[0]
        
#         labels = ['Very Low\n(<5)', 'Low\n(5-10)', 'Moderate\n(10-20)', 'High\n(20-40)', 'Very High\n(>40)']
#         sizes = [year_data['Slight'], year_data['Moderate'], year_data['High'], 
#                  year_data['Very High'], year_data['Severe']]
#         colors = ['#006837', '#7CB342', '#FFEB3B', '#FF9800', '#D32F2F']
        
#         wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
#                                            autopct='%1.1f%%', startangle=90,
#                                            textprops={'fontsize': 8, 'weight': 'bold'})
        
#         for autotext in autotexts:
#             autotext.set_color('white')
        
#         ax.set_title(f'Year {int(year)}', fontsize=11, fontweight='bold')
#         self.pie_fig.tight_layout()
#         self.pie_canvas.draw()
    
#     def plot_trends(self, current_year):
#         """Plot temporal trends"""
#         years = sorted(self.rusle_stats['year'].unique())
#         means = [self.rusle_stats[self.rusle_stats['year'] == y]['mean'].values[0] for y in years]
#         medians = [self.rusle_stats[self.rusle_stats['year'] == y]['median'].values[0] for y in years]
        
#         # Mean trend
#         self.mean_fig.clear()
#         ax1 = self.mean_fig.add_subplot(111)
#         bars = ax1.bar(years, means, color='#3498db', edgecolor='black', linewidth=1, alpha=0.8)
        
#         idx = years.index(current_year)
#         bars[idx].set_color('#e74c3c')
        
#         ax1.set_xlabel('Year', fontsize=9, fontweight='bold')
#         ax1.set_ylabel('Mean (t/ha/yr)', fontsize=9, fontweight='bold')
#         ax1.grid(axis='y', alpha=0.3)
#         ax1.tick_params(labelsize=8)
        
#         self.mean_fig.tight_layout()
#         self.mean_canvas.draw()
        
#         # Median trend
#         self.median_fig.clear()
#         ax2 = self.median_fig.add_subplot(111)
#         ax2.plot(years, medians, 'o-', linewidth=2, markersize=6, color='#2ecc71',
#                 markeredgecolor='black', markeredgewidth=1)
#         ax2.plot(current_year, medians[idx], 'o', markersize=12, color='#e74c3c',
#                 markeredgecolor='black', markeredgewidth=2, zorder=5)
        
#         ax2.set_xlabel('Year', fontsize=9, fontweight='bold')
#         ax2.set_ylabel('Median (t/ha/yr)', fontsize=9, fontweight='bold')
#         ax2.grid(True, alpha=0.3)
#         ax2.fill_between(years, medians, alpha=0.2, color='#2ecc71')
#         ax2.tick_params(labelsize=8)
        
#         self.median_fig.tight_layout()
#         self.median_canvas.draw()
    
#     def load_map_image(self, year):
#         """Load and display map"""
#         map_path = MAPS_DIR / f"soil_loss_map_{year}.png"
        
#         if map_path.exists():
#             try:
#                 img = Image.open(map_path)
#                 img.thumbnail((1200, 550), Image.Resampling.LANCZOS)
#                 photo = ImageTk.PhotoImage(img)
#                 self.map_label.config(image=photo)
#                 self.map_label.image = photo
#             except Exception as e:
#                 self.map_label.config(text=f"Error loading map: {e}")
#         else:
#             self.map_label.config(text=f"Map not found for {year}")
    
#     def show_all_years(self):
#         """Show average for all years"""
#         self.tree.selection_remove(self.tree.selection())
        
#         # Average pie chart
#         self.pie_fig.clear()
#         ax = self.pie_fig.add_subplot(111)
        
#         avg_slight = self.rusle_stats['Slight'].mean()
#         avg_moderate = self.rusle_stats['Moderate'].mean()
#         avg_high = self.rusle_stats['High'].mean()
#         avg_very_high = self.rusle_stats['Very High'].mean()
#         avg_severe = self.rusle_stats['Severe'].mean()
        
#         labels = ['Very Low\n(<5)', 'Low\n(5-10)', 'Moderate\n(10-20)', 'High\n(20-40)', 'Very High\n(>40)']
#         sizes = [avg_slight, avg_moderate, avg_high, avg_very_high, avg_severe]
#         colors = ['#006837', '#7CB342', '#FFEB3B', '#FF9800', '#D32F2F']
        
#         wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
#                                            autopct='%1.1f%%', startangle=90,
#                                            textprops={'fontsize': 8, 'weight': 'bold'})
        
#         for autotext in autotexts:
#             autotext.set_color('white')
        
#         ax.set_title('Average (2014-2024)', fontsize=11, fontweight='bold')
#         self.pie_fig.tight_layout()
#         self.pie_canvas.draw()
        
#         # Show trends for all years (2024 highlighted)
#         self.plot_trends(2024)
#         self.load_map_image(2024)


# def main():
#     """Launch dashboard with full scroll support"""
#     root = tk.Tk()
#     root.title("RUSLE Soil Erosion Dashboard")
#     root.state("zoomed")
#     root.configure(bg="#f5f5f5")

#     # Scrollable container
#     main_canvas = tk.Canvas(root, bg="#f5f5f5", highlightthickness=0)
#     scrollbar = tk.Scrollbar(root, orient="vertical", command=main_canvas.yview)
#     scroll_frame = tk.Frame(main_canvas, bg="#f5f5f5")

#     # Update scroll region when frame changes
#     scroll_frame.bind(
#         "<Configure>",
#         lambda e: main_canvas.configure(
#             scrollregion=main_canvas.bbox("all")
#         )
#     )

#     main_canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
#     main_canvas.configure(yscrollcommand=scrollbar.set)

#     main_canvas.pack(side="left", fill="both", expand=True)
#     scrollbar.pack(side="right", fill="y")

#     # Launch dashboard inside scroll frame
#     aapp = RUSLEDashboard(root, scroll_frame)


#     root.mainloop()


# if __name__ == "__main__":
#     main()



# scripts/09_dashboard_web.py
# Browser-based RUSLE Dashboard (single file)
# Uses your overlay maps in outputs/maps/ and A-factor in temp/erosion/
# Author: Bhavya (integrated by GPT)

from pathlib import Path
import glob
import numpy as np
import pandas as pd
from flask import Flask, jsonify, send_from_directory, render_template_string
import rasterio

# --------------------------------------------------------------------------------------
# Paths / config
# --------------------------------------------------------------------------------------
BASE = Path(__file__).resolve().parents[1]           # project root
MAP_DIR   = BASE / "outputs" / "maps"                # soil_loss_on_basemap_<year>.png
EROS_DIR  = BASE / "temp" / "erosion"                # a_factor_<year>.tif
STATS_DIR = BASE / "outputs" / "statistics" / "erosion"
NODATA = -9999.0

app = Flask(__name__)

# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def _latest_master_csv():
    files = sorted(STATS_DIR.glob("a_factor_stats_master_*.csv"))
    return files[-1] if files else None

def _load_master_stats():
    p = _latest_master_csv()
    cols = ["year","min","mean","median","max","std","valid_count","total_pixels","coverage_pct"]
    if not p:
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(p)
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df["year"] = df["year"].astype(int)
    return df[cols].sort_values("year")

def _years_with_maps():
    years = []
    for y in range(2016, 2026):
        if (MAP_DIR / f"soil_loss_on_basemap_{y}.png").exists():
            years.append(y)
    if years:
        return years
    # fallback: parse names
    found = sorted(MAP_DIR.glob("soil_loss_on_basemap_*.png"))
    return [int(p.stem.split("_")[-1]) for p in found]

def _read_a(year: int):
    tif = EROS_DIR / f"a_factor_{year}.tif"
    if not tif.exists():
        return None
    with rasterio.open(tif) as src:
        arr = src.read(1).astype(np.float32)
        nod = src.nodata
    nod = NODATA if nod is None else nod
    arr[~np.isfinite(arr)] = nod
    arr[arr < 0] = nod
    return arr, nod

def _compute_global_edges():
    """Quantile-based 5-bin edges across all years; matches map classification spirit."""
    samples = []
    for y in range(2016, 2026):
        r = _read_a(y)
        if not r:
            continue
        a, nod = r
        v = a[(a != nod) & (a >= 0)]
        if v.size == 0:
            continue
        if v.size > 800_000:
            idx = np.random.choice(v.size, 800_000, replace=False)
            v = v[idx]
        samples.append(v)
    if not samples:
        # Safe default bands (won't crash)
        return np.array([0.0, 0.05, 0.20, 0.80, 3.20, 1e9], dtype=np.float64)
    allv = np.concatenate(samples)
    q = np.quantile(allv, [0.50, 0.75, 0.90, 0.97])  # 50/75/90/97 percentiles -> 5 classes
    hi = float(np.nanmax(allv)) + 1e-6
    edges = np.array([0.0, q[0], q[1], q[2], q[3], hi], dtype=np.float64)
    return edges

MASTER_STATS = _load_master_stats()
GLOBAL_EDGES = _compute_global_edges()
YEARS = _years_with_maps() or (MASTER_STATS["year"].tolist() if len(MASTER_STATS) else list(range(2016, 2026)))
YEARS = sorted(set(YEARS))

# --------------------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------------------
@app.route("/")
def index():
    # Inline Bootstrap + Chart.js + minimal CSS to keep it single-file.
    # Soil Degradation palette (Very Low→Very High): Green→Red
    html = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>RUSLE Soil Erosion Dashboard — Mula-Mutha (2016–2025)</title>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet"/>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3"></script>
  <style>
    body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial; }
    header { background: #1f2937; }
    header h2 { color: #fff; }
    header .sub { color: #cbd5e1; }
    #map-wrap img { object-fit: contain; background: #dfe6e9; }
    .table td, .table th { vertical-align: middle; }
    .btn-year { font-weight: 700 !important; }
  </style>
</head>
<body class="bg-light">
  <header class="py-3 mb-3 border-bottom">
    <div class="container">
      <h2 class="mb-0 fw-bold">🌍 RUSLE Soil Erosion Analysis Dashboard</h2>
      <div class="sub small">Mula-Mutha River Catchment, Pune | 2016–2025 | MSc Geoinformatics Project</div>
    </div>
  </header>

  <main class="container">
    <!-- Year selector -->
    <section class="mb-3 p-3 bg-white rounded-3 shadow-sm">
      <div class="d-flex align-items-center flex-wrap gap-2">
        <span class="fw-bold me-2">Select Year:</span>
        <div id="year-buttons" class="d-flex flex-wrap gap-2"></div>
        <button id="btn-all" class="btn btn-sm btn-danger fw-bold ms-2">ALL YEARS</button>
      </div>
    </section>

    <!-- Stats table -->
    <section class="mb-3 p-3 bg-white rounded-3 shadow-sm">
      <h6 class="fw-bold mb-2">📊 Annual Statistics Summary</h6>
      <div class="table-responsive">
        <table class="table table-sm table-hover align-middle mb-0" id="stats-table">
          <thead class="table-light">
            <tr>
              <th>Year</th>
              <th>Mean (t/ha/yr)</th>
              <th>Median (t/ha/yr)</th>
              <th>Max (t/ha/yr)</th>
              <th>Coverage (%)</th>
              <th>Valid Pixels</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>

    <!-- Big Map -->
    <section class="mb-3 p-3 bg-white rounded-3 shadow-sm">
      <h6 class="fw-bold mb-2">🗺️ Soil Loss (A) on Colored Basemap</h6>
      <div class="ratio ratio-16x9 border rounded-3 bg-dark-subtle" id="map-wrap">
        <img id="year-map" alt="Map" class="w-100 h-100"/>
      </div>
      <div id="map-caption" class="small text-muted mt-1">
        Basemap: Esri WorldTopoMap with expanded extent; AOI overlay uses the Soil Degradation palette.
      </div>
    </section>

    <!-- Charts -->
    <section class="row g-3">
      <div class="col-lg-4">
        <div class="p-3 bg-white rounded-3 shadow-sm h-100">
          <h6 class="fw-bold mb-2">📈 Erosion Class Distribution</h6>
          <canvas id="pie-classes"></canvas>
          <div class="small mt-2 text-muted" id="pie-caption"></div>
        </div>
      </div>
      <div class="col-lg-4">
        <div class="p-3 bg-white rounded-3 shadow-sm h-100">
          <h6 class="fw-bold mb-2">📊 Mean Erosion Trend</h6>
          <canvas id="mean-trend"></canvas>
        </div>
      </div>
      <div class="col-lg-4">
        <div class="p-3 bg-white rounded-3 shadow-sm h-100">
          <h6 class="fw-bold mb-2">📊 Median Erosion Trend</h6>
          <canvas id="median-trend"></canvas>
        </div>
      </div>
    </section>

    <div class="my-4"></div>
  </main>

<script>
let YEARS = [];
let STATS = { rows: [], trend: { years: [], mean: [], median: [] } };
let currentYear = null;

let pieChart = null;
let meanChart = null;
let medianChart = null;

// Soil Degradation palette (Very Low→Very High)
const COLORS = ["#006837","#7CB342","#FFEB3B","#FF9800","#D32F2F"];

async function getJSON(url){ const r=await fetch(url); if(!r.ok) throw new Error("HTTP "+r.status); return r.json(); }
function fmt(n,d=2){ return (n===null||n===undefined||Number.isNaN(n)) ? "—" : Number(n).toFixed(d); }

function buildYearButtons(){
  const wrap=document.getElementById("year-buttons"); wrap.innerHTML="";
  YEARS.forEach(y=>{
    const b=document.createElement("button");
    b.className="btn btn-sm btn-primary btn-year";
    b.textContent=y;
    b.onclick=()=>updateYear(y);
    wrap.appendChild(b);
  });
  document.getElementById("btn-all").onclick=showAllYears;
}

function fillStatsTable(){
  const body=document.querySelector("#stats-table tbody"); body.innerHTML="";
  STATS.rows.forEach(r=>{
    const tr=document.createElement("tr");
    tr.innerHTML = `
      <td class="fw-bold">${r.year}</td>
      <td>${fmt(r.mean)}</td>
      <td>${fmt(r.median)}</td>
      <td>${fmt(r.max)}</td>
      <td>${fmt(r.coverage_pct)}</td>
      <td>${r.valid_count}</td>`;
    tr.onclick=()=>updateYear(r.year);
    body.appendChild(tr);
  });
}

function drawTrends(){
  const yrs=STATS.trend.years, means=STATS.trend.mean, med=STATS.trend.median;

  if(meanChart) meanChart.destroy();
  meanChart=new Chart(document.getElementById("mean-trend"),{
    type:"bar",
    data:{ labels:yrs, datasets:[{ label:"Mean (t/ha/yr)", data:means }]},
    options:{ responsive:true, scales:{y:{beginAtZero:true}}, plugins:{legend:{display:false}}}
  });

  if(medianChart) medianChart.destroy();
  medianChart=new Chart(document.getElementById("median-trend"),{
    type:"line",
    data:{ labels:yrs, datasets:[{ label:"Median (t/ha/yr)", data:med, tension:0.25, fill:true }]},
    options:{ responsive:true, scales:{y:{beginAtZero:true}}, plugins:{legend:{display:false}}}
  });
}

async function updatePie(year){
  const res=await getJSON(`/api/classes/${year}`);
  const e=res.edges, counts=res.counts;
  const labels=[
    `${e[0].toFixed(2)}–${e[1].toFixed(2)}`,
    `${e[1].toFixed(2)}–${e[2].toFixed(2)}`,
    `${e[2].toFixed(2)}–${e[3].toFixed(2)}`,
    `${e[3].toFixed(2)}–${e[4].toFixed(2)}`,
    `>${e[4].toFixed(2)}`
  ];
  if(pieChart) pieChart.destroy();
  pieChart=new Chart(document.getElementById("pie-classes"),{
    type:"pie",
    data:{ labels, datasets:[{ data:counts, backgroundColor:COLORS }]},
    options:{ responsive:true, plugins:{ legend:{ position:"bottom" } } }
  });
  document.getElementById("pie-caption").textContent = `Global class edges; colors match overlay maps. Year ${year}.`;
}

function updateMap(year){
  const img=document.getElementById("year-map");
  img.src=`/map/soil_loss_on_basemap_${year}.png`;
  img.alt=`Soil loss on basemap — ${year}`;
}

async function updateYear(year){
  currentYear=year;
  updateMap(year);
  await updatePie(year);
}

function showAllYears(){
  if(YEARS.length) updateYear(YEARS[YEARS.length-1]);
}

(async function boot(){
  YEARS = await getJSON("/api/years");
  STATS = await getJSON("/api/stats");
  buildYearButtons();
  fillStatsTable();
  drawTrends();
  const defY = YEARS[YEARS.length-1] || 2025;
  updateYear(defY);
})();
</script>
</body>
</html>
    """
    return render_template_string(html)

@app.route("/api/years")
def api_years():
    return jsonify(YEARS)

@app.route("/api/stats")
def api_stats():
    if len(MASTER_STATS) == 0:
        rows = []
        trend = {"years": [], "mean": [], "median": []}
        return jsonify({"rows": rows, "trend": trend})
    rows = MASTER_STATS.to_dict(orient="records")
    trend = {
        "years": [int(x) for x in MASTER_STATS["year"].tolist()],
        "mean":  [float(x) for x in MASTER_STATS["mean"].tolist()],
        "median":[float(x) for x in MASTER_STATS["median"].tolist()],
    }
    return jsonify({"rows": rows, "trend": trend})

@app.route("/api/classes/<int:year>")
def api_classes(year):
    r = _read_a(year)
    if not r:
        return jsonify({"edges": GLOBAL_EDGES.tolist(), "counts": [0,0,0,0,0]})
    a, nod = r
    m = (a != nod) & (a >= 0)
    bins = GLOBAL_EDGES
    cls = np.digitize(a[m], bins, right=False) - 1  # 0..4
    counts = [int((cls == i).sum()) for i in range(5)]
    return jsonify({"edges": [float(x) for x in bins], "counts": counts})

@app.route("/map/<path:filename>")
def serve_map(filename):
    return send_from_directory(MAP_DIR, filename)

@app.route("/api/maps")
def api_maps():
    files = sorted(glob.glob(str(MAP_DIR / "soil_loss_on_basemap_*.png")))
    return jsonify(files)

# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
if __name__ == "__main__":
    # Run: python scripts/09_dashboard_web.py
    # Requires: pip install flask pandas numpy rasterio
    app.run(host="127.0.0.1", port=5001, debug=True)
