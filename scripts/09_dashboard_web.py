# # scripts/09_dashboard_web.py
# # Browser-based RUSLE Dashboard (single file)
# # Uses overlay maps in outputs/maps/ and A-factor in temp/erosion/
# # FINAL PATCHED VERSION — Chart sizes reduced

# from pathlib import Path
# import glob
# import numpy as np
# import pandas as pd
# from flask import Flask, jsonify, send_from_directory, render_template_string
# import rasterio

# # -----------------------------------------------------------
# # Paths
# # -----------------------------------------------------------
# BASE = Path(__file__).resolve().parents[1]
# MAP_DIR = BASE / "outputs" / "maps"
# EROS_DIR = BASE / "temp" / "erosion"
# STATS_DIR = BASE / "outputs" / "statistics" / "erosion"
# NODATA = -9999.0

# app = Flask(__name__)

# # -----------------------------------------------------------
# # Helpers
# # -----------------------------------------------------------
# def _latest_master_csv():
#     files = sorted(STATS_DIR.glob("a_factor_stats_master_*.csv"))
#     return files[-1] if files else None

# def _load_master_stats():
#     p = _latest_master_csv()
#     cols = ["year","min","mean","median","max","std","valid_count","total_pixels","coverage_pct"]
#     if not p:
#         return pd.DataFrame(columns=cols)
#     df = pd.read_csv(p)
#     for c in cols:
#         if c not in df.columns:
#             df[c] = None
#     df["year"] = df["year"].astype(int)
#     return df[cols].sort_values("year")

# def _years_with_maps():
#     years = []
#     for y in range(2016, 2026):
#         if (MAP_DIR / f"soil_loss_on_basemap_{y}.png").exists():
#             years.append(y)
#     if years:
#         return years
#     found = sorted(MAP_DIR.glob("soil_loss_on_basemap_*.png"))
#     return [int(p.stem.split("_")[-1]) for p in found]

# def _read_a(year: int):
#     tif = EROS_DIR / f"a_factor_{year}.tif"
#     if not tif.exists():
#         return None
#     with rasterio.open(tif) as src:
#         arr = src.read(1).astype(np.float32)
#         nod = src.nodata
#     nod = NODATA if nod is None else nod
#     arr[~np.isfinite(arr)] = nod
#     arr[arr < 0] = nod
#     return arr, nod

# def _compute_global_edges():
#     samples = []
#     for y in range(2016, 2026):
#         r = _read_a(y)
#         if not r:
#             continue
#         a, nod = r
#         v = a[(a != nod) & (a >= 0)]
#         if v.size > 800000:
#             idx = np.random.choice(v.size, 800000, replace=False)
#             v = v[idx]
#         if v.size:
#             samples.append(v)
#     if not samples:
#         return np.array([0.0,0.05,0.20,0.80,3.20,1e9],dtype=np.float64)
#     allv = np.concatenate(samples)
#     q = np.quantile(allv, [0.50,0.75,0.90,0.97])
#     hi = float(np.nanmax(allv)) + 1e-6
#     return np.array([0.0,q[0],q[1],q[2],q[3],hi])

# MASTER_STATS = _load_master_stats()
# GLOBAL_EDGES = _compute_global_edges()
# YEARS = sorted(set(_years_with_maps() or MASTER_STATS["year"].tolist()))

# # -----------------------------------------------------------
# # HTML
# # -----------------------------------------------------------
# @app.route("/")
# def index():
#     html = r"""
# <!doctype html>
# <html lang="en">
# <head>
# <meta charset="utf-8"/>
# <title>RUSLE Soil Erosion Dashboard</title>
# <meta name="viewport" content="width=device-width, initial-scale=1"/>

# <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet"/>
# <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3"></script>

# <style>
# body { font-family: system-ui; background:#f1f3f4; }
# header { background:#1f2937; text-align:center; }
# header h2 { color:#fff; margin-bottom:4px; }
# header .sub { color:#cbd5e1; }

# /* LAYOUT */
# .map-col { width:60%; float:left; padding-right:10px; }
# .chart-col { width:40%; float:right; display:flex; flex-direction:column; gap:10px; }

# /* CHART CARDS — SMALLER */
# .chart-card {
#     background:white;
#     border-radius:8px;
#     min-height:220px !important;
#     padding:8px !important;
#     box-shadow:0 1px 3px rgba(0,0,0,0.15);
# }

# #map-wrap img { width:100%; height:480px; object-fit:contain; }

# .table td, .table th { vertical-align:middle; }
# .btn-year { font-weight:700 !important; }
# </style>
# </head>

# <body>
# <header class="py-3 mb-3">
# <h2 class="fw-bold">RUSLE Soil Erosion Analysis Dashboard</h2>
# <div class="sub small">Mula-Mutha Bhima Catchment, Pune | 2016–2025 | MSc Geoinformatics Project</div>
# </header>

# <div class="container-fluid">

# <!-- YEAR SELECTOR -->
# <section class="mb-3 p-3 bg-white rounded-3 shadow-sm">
#   <span class="fw-bold me-2">Select Year:</span>
#   <div id="year-buttons" class="d-inline-block"></div>
#   <button id="btn-all" class="btn btn-sm btn-danger fw-bold ms-2">ALL YEARS</button>
# </section>

# <!-- STATS TABLE -->
# <section class="mb-3 p-3 bg-white rounded-3 shadow-sm">
# <h6 class="fw-bold mb-2">Annual Statistics</h6>
# <table class="table table-sm table-hover mb-0" id="stats-table">
# <thead class="table-light">
# <tr>
# <th>Year</th><th>Mean</th><th>Median</th><th>Max</th>
# </tr>
# </thead>
# <tbody></tbody>
# </table>
# </section>

# <!-- MAP -->
# <div class="map-col">
# <section class="p-3 bg-white rounded-3 shadow-sm">
# <h6 class="fw-bold mb-2">Soil Loss Map</h6>
# <div id="map-wrap"><img id="year-map"/></div>
# <div id="map-caption" class="small text-muted mt-1"></div>
# </section>
# </div>

# <!-- CHARTS -->
# <div class="chart-col">

# <div class="chart-card">
# <h6 class="fw-bold mb-1" style="font-size:13px;">Erosion Class Distribution</h6>
# <canvas id="pie-classes" width="400" height="180"></canvas>
# <div id="pie-caption" class="small text-muted"></div>
# </div>

# <div class="chart-card">
# <h6 class="fw-bold mb-1" style="font-size:13px;">Mean Trend</h6>
# <canvas id="mean-trend" width="400" height="180"></canvas>
# </div>

# <div class="chart-card">
# <h6 class="fw-bold mb-1" style="font-size:13px;">Median Trend</h6>
# <canvas id="median-trend" width="400" height="180"></canvas>
# </div>

# </div>

# </div> <!-- container-fluid -->

# <script>
# let YEARS=[];
# let STATS={rows:[],trend:{years:[],mean:[],median:[]}};
# let currentYear=null;

# let pieChart=null,meanChart=null,medianChart=null;

# const COLORS=["#006837","#7CB342","#FFEB3B","#FF9800","#D32F2F"];

# async function getJSON(url){
#   const r=await fetch(url); return r.json();
# }

# function fmt(n,d=2){ return(!n && n!==0)?"—":Number(n).toFixed(d); }

# function buildYearButtons(){
#   const wrap=document.getElementById("year-buttons");
#   wrap.innerHTML="";
#   YEARS.forEach(y=>{
#     let b=document.createElement("button");
#     b.className="btn btn-sm btn-primary btn-year me-1 mb-1";
#     b.textContent=y;
#     b.onclick=()=>updateYear(y);
#     wrap.appendChild(b);
#   });
#   document.getElementById("btn-all").onclick=showAllYears;
# }

# function fillStatsTable(y=null){
#   const body=document.querySelector("#stats-table tbody");
#   body.innerHTML="";
#   if(y===null){
#     STATS.rows.forEach(r=>{
#       const tr=document.createElement("tr");
#       tr.innerHTML=`<td>${r.year}</td><td>${fmt(r.mean)}</td><td>${fmt(r.median)}</td><td>${fmt(r.max)}</td>`;
#       tr.onclick=()=>updateYear(r.year);
#       body.appendChild(tr);
#     });
#     return;
#   }
#   const r=STATS.rows.find(x=>x.year===y);
#   if(!r) return;
#   const tr=document.createElement("tr");
#   tr.innerHTML=`<td>${r.year}</td><td>${fmt(r.mean)}</td><td>${fmt(r.median)}</td><td>${fmt(r.max)}</td>`;
#   body.appendChild(tr);
# }

# function drawTrends(){
#   if(meanChart) meanChart.destroy();
#   meanChart=new Chart(document.getElementById("mean-trend"),{
#     type:"bar",
#     data:{labels:STATS.trend.years,datasets:[{data:STATS.trend.mean}]},
#     options:{responsive:false,maintainAspectRatio:false,scales:{y:{beginAtZero:true}},plugins:{legend:{display:false}}}
#   });

#   if(medianChart) medianChart.destroy();
#   medianChart=new Chart(document.getElementById("median-trend"),{
#     type:"line",
#     data:{labels:STATS.trend.years,datasets:[{data:STATS.trend.median,tension:0.25}]},
#     options:{responsive:false,maintainAspectRatio:false,scales:{y:{beginAtZero:true}},plugins:{legend:{display:false}}}
#   });
# }

# async function updatePie(y){
#   const r=await getJSON(`/api/classes/${y}`);
#   const e=r.edges, c=r.counts;
#   const labels=[`${e[0].toFixed(2)}–${e[1].toFixed(2)}`,`${e[1].toFixed(2)}–${e[2].toFixed(2)}`,`${e[2].toFixed(2)}–${e[3].toFixed(2)}`,`${e[3].toFixed(2)}–${e[4].toFixed(2)}`,`>${e[4].toFixed(2)}`];

#   if(pieChart) pieChart.destroy();
#   pieChart=new Chart(document.getElementById("pie-classes"),{
#     type:"pie",
#     data:{labels:labels,datasets:[{data:c,backgroundColor:COLORS}]},
#     options:{responsive:false,maintainAspectRatio:false,plugins:{legend:{position:"bottom",labels:{font:{size:9}}}}}
#   });
#   document.getElementById("pie-caption").textContent=`Year ${y}`;
# }

# function updateMap(y){
#   const img=document.getElementById("year-map");
#   if(y===null){ img.src=""; return; }
#   img.src=`/map/soil_loss_on_basemap_${y}.png`;
#   img.alt=`Map ${y}`;
#   document.getElementById("map-caption").textContent=`Soil loss map for ${y}`;
# }

# async function updateYear(y){
#   currentYear=y;
#   updateMap(y);
#   fillStatsTable(y);
#   await updatePie(y);
# }

# function showAllYears(){
#   fillStatsTable(null);
#   updateMap(null);
#   if(pieChart) pieChart.destroy();
#   document.getElementById("pie-caption").textContent="All Years Overview";
# }

# (async function boot(){
#   YEARS=await getJSON("/api/years");
#   STATS=await getJSON("/api/stats");
#   buildYearButtons();
#   drawTrends();
#   const defY=YEARS[YEARS.length-1] || 2025;
#   updateYear(defY);
# })();
# </script>

# </body>
# </html>
# """
#     return render_template_string(html)

# # -----------------------------------------------------------
# # API ROUTES
# # -----------------------------------------------------------
# @app.route("/api/years")
# def api_years():
#     return jsonify(YEARS)

# @app.route("/api/stats")
# def api_stats():
#     if len(MASTER_STATS)==0:
#         return jsonify({"rows":[], "trend":{"years":[],"mean":[],"median":[]}})
#     rows = MASTER_STATS.to_dict(orient="records")
#     trend = {
#         "years":[int(x) for x in MASTER_STATS["year"]],
#         "mean":[float(x) for x in MASTER_STATS["mean"]],
#         "median":[float(x) for x in MASTER_STATS["median"]],
#     }
#     return jsonify({"rows":rows,"trend":trend})

# @app.route("/api/classes/<int:year>")
# def api_classes(year):
#     r=_read_a(year)
#     if not r:
#         return jsonify({"edges":GLOBAL_EDGES.tolist(),"counts":[0]*5})
#     a, nod = r
#     m=(a!=nod)&(a>=0)
#     bins=GLOBAL_EDGES
#     cls=np.digitize(a[m], bins)-1
#     counts=[int((cls==i).sum()) for i in range(5)]
#     return jsonify({"edges":[float(x) for x in bins],"counts":counts})

# @app.route("/map/<path:filename>")
# def serve_map(filename):
#     return send_from_directory(MAP_DIR, filename)

# # -----------------------------------------------------------
# # MAIN
# # -----------------------------------------------------------
# if __name__ == "__main__":
#     app.run(host="127.0.0.1", port=5001, debug=True)

# scripts/09_dashboard_web.py
# Browser-based RUSLE Dashboard (single file)
# Uses overlay maps in outputs/maps/ and A-factor in temp/erosion/
# FINAL PATCHED VERSION — Chart sizes reduced + ALL-YEARS aggregated pie + map fallback to latest

from pathlib import Path
import glob
import numpy as np
import pandas as pd
from flask import Flask, jsonify, send_from_directory, render_template_string
import rasterio

# -----------------------------------------------------------
# Paths
# -----------------------------------------------------------
BASE = Path(__file__).resolve().parents[1]
MAP_DIR = BASE / "outputs" / "maps"
EROS_DIR = BASE / "temp" / "erosion"
STATS_DIR = BASE / "outputs" / "statistics" / "erosion"
NODATA = -9999.0

app = Flask(__name__)

# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------
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
    samples = []
    for y in range(2016, 2026):
        r = _read_a(y)
        if not r:
            continue
        a, nod = r
        v = a[(a != nod) & (a >= 0)]
        if v.size > 800000:
            idx = np.random.choice(v.size, 800000, replace=False)
            v = v[idx]
        if v.size:
            samples.append(v)
    if not samples:
        return np.array([0.0,0.05,0.20,0.80,3.20,1e9],dtype=np.float64)
    allv = np.concatenate(samples)
    q = np.quantile(allv, [0.50,0.75,0.90,0.97])
    hi = float(np.nanmax(allv)) + 1e-6
    return np.array([0.0,q[0],q[1],q[2],q[3],hi])

MASTER_STATS = _load_master_stats()
GLOBAL_EDGES = _compute_global_edges()
YEARS = sorted(set(_years_with_maps() or MASTER_STATS["year"].tolist()))

# -----------------------------------------------------------
# HTML
# -----------------------------------------------------------
@app.route("/")
def index():
    html = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>RUSLE Soil Erosion Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3"></script>

<style>
body { font-family: system-ui; background:#f1f3f4; }
header { background:#1f2937; text-align:center; }
header h2 { color:#fff; margin-bottom:4px; }
header .sub { color:#cbd5e1; }

/* LAYOUT */
.map-col { width:60%; float:left; padding-right:10px; }
.chart-col { width:40%; float:right; display:flex; flex-direction:column; gap:10px; }

/* CHART CARDS — SMALLER */
.chart-card {
    background:white;
    border-radius:8px;
    min-height:220px !important;
    padding:8px !important;
    box-shadow:0 1px 3px rgba(0,0,0,0.15);
}

#map-wrap img { width:100%; height:480px; object-fit:contain; }

.table td, .table th { vertical-align:middle; }
.btn-year { font-weight:700 !important; }
</style>
</head>

<body>
<header class="py-3 mb-3">
<h2 class="fw-bold">RUSLE Soil Erosion Analysis Dashboard</h2>
<div class="sub small">Mula-Mutha Bhima Catchment, Pune | 2016–2025 | MSc Geoinformatics Project</div>
</header>

<div class="container-fluid">

<!-- YEAR SELECTOR -->
<section class="mb-3 p-3 bg-white rounded-3 shadow-sm">
  <span class="fw-bold me-2">Select Year:</span>
  <div id="year-buttons" class="d-inline-block"></div>
  <button id="btn-all" class="btn btn-sm btn-danger fw-bold ms-2">ALL YEARS</button>
</section>

<!-- STATS TABLE -->
<section class="mb-3 p-3 bg-white rounded-3 shadow-sm">
<h6 class="fw-bold mb-2">Annual Statistics</h6>
<table class="table table-sm table-hover mb-0" id="stats-table">
<thead class="table-light">
<tr>
<th>Year</th><th>Mean</th><th>Median</th><th>Max</th>
</tr>
</thead>
<tbody></tbody>
</table>
</section>

<!-- MAP -->
<div class="map-col">
<section class="p-3 bg-white rounded-3 shadow-sm">
<h6 class="fw-bold mb-2">Soil Loss Map</h6>
<div id="map-wrap"><img id="year-map"/></div>
<div id="map-caption" class="small text-muted mt-1"></div>
</section>
</div>

<!-- CHARTS -->
<div class="chart-col">

<div class="chart-card">
<h6 class="fw-bold mb-1" style="font-size:13px;">Erosion Class Distribution</h6>
<canvas id="pie-classes" width="400" height="180"></canvas>
<div id="pie-caption" class="small text-muted"></div>
</div>

<div class="chart-card">
<h6 class="fw-bold mb-1" style="font-size:13px;">Mean Trend</h6>
<canvas id="mean-trend" width="400" height="180"></canvas>
</div>

<div class="chart-card">
<h6 class="fw-bold mb-1" style="font-size:13px;">Median Trend</h6>
<canvas id="median-trend" width="400" height="180"></canvas>
</div>

</div>

</div> <!-- container-fluid -->

<script>
let YEARS=[];
let STATS={rows:[],trend:{years:[],mean:[],median:[]}};
let currentYear=null;

let pieChart=null,meanChart=null,medianChart=null;

const COLORS=["#006837","#7CB342","#FFEB3B","#FF9800","#D32F2F"];

async function getJSON(url){
  const r=await fetch(url);
  if(!r.ok) throw new Error("HTTP "+r.status);
  return r.json();
}

function fmt(n,d=2){ return (n===null||n===undefined||isNaN(n)?"—":Number(n).toFixed(d)); }

function buildYearButtons(){
  const wrap=document.getElementById("year-buttons");
  wrap.innerHTML="";
  YEARS.forEach(y=>{
    let b=document.createElement("button");
    b.className="btn btn-sm btn-primary btn-year me-1 mb-1";
    b.textContent=y;
    b.onclick=()=>updateYear(y);
    wrap.appendChild(b);
  });
  document.getElementById("btn-all").onclick=showAllYears;
}

function fillStatsTable(y=null){
  const body=document.querySelector("#stats-table tbody");
  body.innerHTML="";
  if(y===null){
    STATS.rows.forEach(r=>{
      const tr=document.createElement("tr");
      tr.innerHTML=`<td>${r.year}</td><td>${fmt(r.mean)}</td><td>${fmt(r.median)}</td><td>${fmt(r.max)}</td>`;
      tr.onclick=()=>updateYear(r.year);
      body.appendChild(tr);
    });
    return;
  }
  const r=STATS.rows.find(x=>x.year===y);
  if(!r) return;
  const tr=document.createElement("tr");
  tr.innerHTML=`<td>${r.year}</td><td>${fmt(r.mean)}</td><td>${fmt(r.median)}</td><td>${fmt(r.max)}</td>`;
  body.appendChild(tr);
}

function drawTrends(){
  if(meanChart) meanChart.destroy();
  meanChart=new Chart(document.getElementById("mean-trend"),{
    type:"bar",
    data:{labels:STATS.trend.years,datasets:[{data:STATS.trend.mean}]},
    options:{responsive:false,maintainAspectRatio:false,scales:{y:{beginAtZero:true}},plugins:{legend:{display:false}}}
  });

  if(medianChart) medianChart.destroy();
  medianChart=new Chart(document.getElementById("median-trend"),{
    type:"line",
    data:{labels:STATS.trend.years,datasets:[{data:STATS.trend.median,tension:0.25}]},
    options:{responsive:false,maintainAspectRatio:false,scales:{y:{beginAtZero:true}},plugins:{legend:{display:false}}}
  });
}

// updatePie can accept a year number or null for ALL years aggregated
async function updatePie(y){
  let endpoint = (y === null) ? "/api/classes/all" : `/api/classes/${y}`;
  const r = await getJSON(endpoint);
  const e = r.edges, c = r.counts;
  const labels = [
    `${e[0].toFixed(2)}–${e[1].toFixed(2)}`,
    `${e[1].toFixed(2)}–${e[2].toFixed(2)}`,
    `${e[2].toFixed(02)}–${e[3].toFixed(2)}`.replace('02','2'),
    `${e[3].toFixed(2)}–${e[4].toFixed(2)}`,
    `>${e[4].toFixed(2)}`
  ];
  if(pieChart) pieChart.destroy();
  pieChart=new Chart(document.getElementById("pie-classes"),{
    type:"pie",
    data:{labels:labels,datasets:[{data:c,backgroundColor:COLORS}]},
    options:{responsive:false,maintainAspectRatio:false,plugins:{legend:{position:"bottom",labels:{font:{size:9}}}}}
  });
  document.getElementById("pie-caption").textContent = (y === null) ? "All years (aggregated)" : `Year ${y}`;
}

function updateMap(y){
  const img=document.getElementById("year-map");
  if(y===null){
    // if ALL selected, show the latest available year map as a visual fallback
    const latest = (YEARS && YEARS.length) ? YEARS[YEARS.length - 1] : null;
    if(latest !== null){
      img.src = `/map/soil_loss_on_basemap_${latest}.png`;
      img.alt = `Latest available: ${latest}`;
      document.getElementById("map-caption").textContent = `Showing latest available map (${latest}) while viewing ALL years aggregated.`;
    } else {
      img.src = "";
      img.alt = "";
      document.getElementById("map-caption").textContent = "No map available.";
    }
    return;
  }
  img.src=`/map/soil_loss_on_basemap_${y}.png`;
  img.alt=`Map ${y}`;
  document.getElementById("map-caption").textContent=`Soil loss map for ${y}`;
}

async function updateYear(y){
  currentYear=y;
  updateMap(y);
  fillStatsTable(y);
  await updatePie(y);
}

async function showAllYears(){
  // show full stats table and aggregated pie + map fallback
  fillStatsTable(null);
  updateMap(null);
  await updatePie(null);
}

(async function boot(){
  YEARS = await getJSON("/api/years");
  STATS = await getJSON("/api/stats");
  buildYearButtons();
  drawTrends();
  // pick a sensible default
  const defY = (YEARS && YEARS.length) ? YEARS[YEARS.length-1] : 2025;
  await updateYear(defY);
})();
</script>

</body>
</html>
"""
    return render_template_string(html)

# -----------------------------------------------------------
# API ROUTES
# -----------------------------------------------------------
@app.route("/api/years")
def api_years():
    return jsonify(YEARS)

@app.route("/api/stats")
def api_stats():
    if len(MASTER_STATS)==0:
        return jsonify({"rows":[], "trend":{"years":[],"mean":[],"median":[]}})
    rows = MASTER_STATS.to_dict(orient="records")
    trend = {
        "years":[int(x) for x in MASTER_STATS["year"]],
        "mean":[float(x) for x in MASTER_STATS["mean"]],
        "median":[float(x) for x in MASTER_STATS["median"]],
    }
    return jsonify({"rows":rows,"trend":trend})

@app.route("/api/classes/<int:year>")
def api_classes(year):
    r=_read_a(year)
    if not r:
        return jsonify({"edges":GLOBAL_EDGES.tolist(),"counts":[0]*5})
    a, nod = r
    m=(a!=nod)&(a>=0)
    bins=GLOBAL_EDGES
    cls=np.digitize(a[m], bins)-1
    counts=[int((cls==i).sum()) for i in range(5)]
    return jsonify({"edges":[float(x) for x in bins],"counts":counts})

@app.route("/api/classes/all")
def api_classes_all():
    """Aggregate counts across all available years (sums counts per class)."""
    bins = GLOBAL_EDGES
    agg = np.zeros(len(bins)-1, dtype=np.int64)
    for y in YEARS:
        r = _read_a(y)
        if not r:
            continue
        a, nod = r
        m = (a != nod) & (a >= 0)
        if not np.any(m):
            continue
        cls = np.digitize(a[m], bins) - 1
        # count each class and add
        for i in range(len(agg)):
            agg[i] += int((cls == i).sum())
    return jsonify({"edges":[float(x) for x in bins],"counts":agg.tolist()})

@app.route("/map/<path:filename>")
def serve_map(filename):
    return send_from_directory(MAP_DIR, filename)

# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
