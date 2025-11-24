# # # scripts/09_dashboard_web.py
# # # Browser-based RUSLE Dashboard (single file)
# # # Uses your overlay maps in outputs/maps/ and A-factor in temp/erosion/
# # # Author: Bhavya (integrated by GPT)

# # from pathlib import Path
# # import glob
# # import numpy as np
# # import pandas as pd
# # from flask import Flask, jsonify, send_from_directory, render_template_string
# # import rasterio

# # # --------------------------------------------------------------------------------------
# # # Paths / config
# # # --------------------------------------------------------------------------------------
# # BASE = Path(__file__).resolve().parents[1]           # project root
# # MAP_DIR   = BASE / "outputs" / "maps"                # soil_loss_on_basemap_<year>.png
# # EROS_DIR  = BASE / "temp" / "erosion"                # a_factor_<year>.tif
# # STATS_DIR = BASE / "outputs" / "statistics" / "erosion"
# # NODATA = -9999.0

# # app = Flask(__name__)

# # # --------------------------------------------------------------------------------------
# # # Helpers
# # # --------------------------------------------------------------------------------------
# # def _latest_master_csv():
# #     files = sorted(STATS_DIR.glob("a_factor_stats_master_*.csv"))
# #     return files[-1] if files else None

# # def _load_master_stats():
# #     p = _latest_master_csv()
# #     cols = ["year","min","mean","median","max","std","valid_count","total_pixels","coverage_pct"]
# #     if not p:
# #         return pd.DataFrame(columns=cols)
# #     df = pd.read_csv(p)
# #     for c in cols:
# #         if c not in df.columns:
# #             df[c] = None
# #     df["year"] = df["year"].astype(int)
# #     return df[cols].sort_values("year")

# # def _years_with_maps():
# #     years = []
# #     for y in range(2016, 2026):
# #         if (MAP_DIR / f"soil_loss_on_basemap_{y}.png").exists():
# #             years.append(y)
# #     if years:
# #         return years
# #     # fallback: parse names
# #     found = sorted(MAP_DIR.glob("soil_loss_on_basemap_*.png"))
# #     return [int(p.stem.split("_")[-1]) for p in found]

# # def _read_a(year: int):
# #     tif = EROS_DIR / f"a_factor_{year}.tif"
# #     if not tif.exists():
# #         return None
# #     with rasterio.open(tif) as src:
# #         arr = src.read(1).astype(np.float32)
# #         nod = src.nodata
# #     nod = NODATA if nod is None else nod
# #     arr[~np.isfinite(arr)] = nod
# #     arr[arr < 0] = nod
# #     return arr, nod

# # def _compute_global_edges():
# #     """Quantile-based 5-bin edges across all years; matches map classification spirit."""
# #     samples = []
# #     for y in range(2016, 2026):
# #         r = _read_a(y)
# #         if not r:
# #             continue
# #         a, nod = r
# #         v = a[(a != nod) & (a >= 0)]
# #         if v.size == 0:
# #             continue
# #         if v.size > 800_000:
# #             idx = np.random.choice(v.size, 800_000, replace=False)
# #             v = v[idx]
# #         samples.append(v)
# #     if not samples:
# #         # Safe default bands (won't crash)
# #         return np.array([0.0, 0.05, 0.20, 0.80, 3.20, 1e9], dtype=np.float64)
# #     allv = np.concatenate(samples)
# #     q = np.quantile(allv, [0.50, 0.75, 0.90, 0.97])  # 50/75/90/97 percentiles -> 5 classes
# #     hi = float(np.nanmax(allv)) + 1e-6
# #     edges = np.array([0.0, q[0], q[1], q[2], q[3], hi], dtype=np.float64)
# #     return edges

# # MASTER_STATS = _load_master_stats()
# # GLOBAL_EDGES = _compute_global_edges()
# # YEARS = _years_with_maps() or (MASTER_STATS["year"].tolist() if len(MASTER_STATS) else list(range(2016, 2026)))
# # YEARS = sorted(set(YEARS))

# # # --------------------------------------------------------------------------------------
# # # Routes
# # # --------------------------------------------------------------------------------------
# # @app.route("/")
# # def index():
# #     # Inline Bootstrap + Chart.js + minimal CSS to keep it single-file.
# #     # Soil Degradation palette (Very Low→Very High): Green→Red
# #     html = r"""
# # <!doctype html>
# # <html lang="en">
# # <head>
# #   <meta charset="utf-8"/>
# #   <title>RUSLE Soil Erosion Dashboard — Mula-Mutha (2016–2025)</title>
# #   <meta name="viewport" content="width=device-width, initial-scale=1"/>
# #   <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet"/>
# #   <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3"></script>
# #   <style>
# #     body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial; }
# #     header { background: #1f2937; }
# #     header h2 { color: #fff; }
# #     header .sub { color: #cbd5e1; }
# #     #map-wrap img { object-fit: contain; background: #dfe6e9; }
# #     .table td, .table th { vertical-align: middle; }
# #     .btn-year { font-weight: 700 !important; }
# #   </style>
# # </head>
# # <body class="bg-light">
# #   <header class="py-3 mb-3 border-bottom">
# #     <div class="container">
# #       <h2 class="mb-0 fw-bold">🌍 RUSLE Soil Erosion Analysis Dashboard</h2>
# #       <div class="sub small">Mula-Mutha River Catchment, Pune | 2016–2025 | MSc Geoinformatics Project</div>
# #     </div>
# #   </header>

# #   <main class="container">
# #     <!-- Year selector -->
# #     <section class="mb-3 p-3 bg-white rounded-3 shadow-sm">
# #       <div class="d-flex align-items-center flex-wrap gap-2">
# #         <span class="fw-bold me-2">Select Year:</span>
# #         <div id="year-buttons" class="d-flex flex-wrap gap-2"></div>
# #         <button id="btn-all" class="btn btn-sm btn-danger fw-bold ms-2">ALL YEARS</button>
# #       </div>
# #     </section>

# #     <!-- Stats table -->
# #     <section class="mb-3 p-3 bg-white rounded-3 shadow-sm">
# #       <h6 class="fw-bold mb-2">📊 Annual Statistics Summary</h6>
# #       <div class="table-responsive">
# #         <table class="table table-sm table-hover align-middle mb-0" id="stats-table">
# #           <thead class="table-light">
# #             <tr>
# #               <th>Year</th>
# #               <th>Mean (t/ha/yr)</th>
# #               <th>Median (t/ha/yr)</th>
# #               <th>Max (t/ha/yr)</th>
# #               <th>Coverage (%)</th>
# #               <th>Valid Pixels</th>
# #             </tr>
# #           </thead>
# #           <tbody></tbody>
# #         </table>
# #       </div>
# #     </section>

# #     <!-- Big Map -->
# #     <section class="mb-3 p-3 bg-white rounded-3 shadow-sm">
# #       <h6 class="fw-bold mb-2">🗺️ Soil Loss (A) on Colored Basemap</h6>
# #       <div class="ratio ratio-16x9 border rounded-3 bg-dark-subtle" id="map-wrap">
# #         <img id="year-map" alt="Map" class="w-100 h-100"/>
# #       </div>
# #       <div id="map-caption" class="small text-muted mt-1">
# #         Basemap: Esri WorldTopoMap with expanded extent; AOI overlay uses the Soil Degradation palette.
# #       </div>
# #     </section>

# #     <!-- Charts -->
# #     <section class="row g-3">
# #       <div class="col-lg-4">
# #         <div class="p-3 bg-white rounded-3 shadow-sm h-100">
# #           <h6 class="fw-bold mb-2">📈 Erosion Class Distribution</h6>
# #           <canvas id="pie-classes"></canvas>
# #           <div class="small mt-2 text-muted" id="pie-caption"></div>
# #         </div>
# #       </div>
# #       <div class="col-lg-4">
# #         <div class="p-3 bg-white rounded-3 shadow-sm h-100">
# #           <h6 class="fw-bold mb-2">📊 Mean Erosion Trend</h6>
# #           <canvas id="mean-trend"></canvas>
# #         </div>
# #       </div>
# #       <div class="col-lg-4">
# #         <div class="p-3 bg-white rounded-3 shadow-sm h-100">
# #           <h6 class="fw-bold mb-2">📊 Median Erosion Trend</h6>
# #           <canvas id="median-trend"></canvas>
# #         </div>
# #       </div>
# #     </section>

# #     <div class="my-4"></div>
# #   </main>

# # <script>
# # let YEARS = [];
# # let STATS = { rows: [], trend: { years: [], mean: [], median: [] } };
# # let currentYear = null;

# # let pieChart = null;
# # let meanChart = null;
# # let medianChart = null;

# # // Soil Degradation palette (Very Low→Very High)
# # const COLORS = ["#006837","#7CB342","#FFEB3B","#FF9800","#D32F2F"];

# # async function getJSON(url){ const r=await fetch(url); if(!r.ok) throw new Error("HTTP "+r.status); return r.json(); }
# # function fmt(n,d=2){ return (n===null||n===undefined||Number.isNaN(n)) ? "—" : Number(n).toFixed(d); }

# # function buildYearButtons(){
# #   const wrap=document.getElementById("year-buttons"); wrap.innerHTML="";
# #   YEARS.forEach(y=>{
# #     const b=document.createElement("button");
# #     b.className="btn btn-sm btn-primary btn-year";
# #     b.textContent=y;
# #     b.onclick=()=>updateYear(y);
# #     wrap.appendChild(b);
# #   });
# #   document.getElementById("btn-all").onclick=showAllYears;
# # }

# # # function fillStatsTable(){
# # #   const body=document.querySelector("#stats-table tbody"); body.innerHTML="";
# # #   STATS.rows.forEach(r=>{
# # #     const tr=document.createElement("tr");
# # #     tr.innerHTML = `
# # #       <td class="fw-bold">${r.year}</td>
# # #       <td>${fmt(r.mean)}</td>
# # #       <td>${fmt(r.median)}</td>
# # #       <td>${fmt(r.max)}</td>
# # #       <td>${fmt(r.coverage_pct)}</td>
# # #       <td>${r.valid_count}</td>`;
# # #     tr.onclick=()=>updateYear(r.year);
# # #     body.appendChild(tr);
# # #   });
# # # }

# # function fillStatsTable(selectedYear = null){
# #   const body = document.querySelector("#stats-table tbody");
# #   body.innerHTML = "";

# #   let row = null;

# #   if (selectedYear !== null) {
# #     row = STATS.rows.find(r => r.year === selectedYear);
# #   }

# #   if (!row) return;

# #   const tr = document.createElement("tr");
# #   tr.innerHTML = `
# #       <td class="fw-bold">${row.year}</td>
# #       <td>${fmt(row.mean)}</td>
# #       <td>${fmt(row.median)}</td>
# #       <td>${fmt(row.max)}</td>
# #       <td>${fmt(row.coverage_pct)}</td>
# #       <td>${row.valid_count}</td>`;
# #   tr.onclick = () => updateYear(row.year);
# #   body.appendChild(tr);
# # }


# # function drawTrends(){
# #   const yrs=STATS.trend.years, means=STATS.trend.mean, med=STATS.trend.median;

# #   if(meanChart) meanChart.destroy();
# #   meanChart=new Chart(document.getElementById("mean-trend"),{
# #     type:"bar",
# #     data:{ labels:yrs, datasets:[{ label:"Mean (t/ha/yr)", data:means }]},
# #     options:{ responsive:true, scales:{y:{beginAtZero:true}}, plugins:{legend:{display:false}}}
# #   });

# #   if(medianChart) medianChart.destroy();
# #   medianChart=new Chart(document.getElementById("median-trend"),{
# #     type:"line",
# #     data:{ labels:yrs, datasets:[{ label:"Median (t/ha/yr)", data:med, tension:0.25, fill:true }]},
# #     options:{ responsive:true, scales:{y:{beginAtZero:true}}, plugins:{legend:{display:false}}}
# #   });
# # }

# # async function updatePie(year){
# #   const res=await getJSON(`/api/classes/${year}`);
# #   const e=res.edges, counts=res.counts;
# #   const labels=[
# #     `${e[0].toFixed(2)}–${e[1].toFixed(2)}`,
# #     `${e[1].toFixed(2)}–${e[2].toFixed(2)}`,
# #     `${e[2].toFixed(2)}–${e[3].toFixed(2)}`,
# #     `${e[3].toFixed(2)}–${e[4].toFixed(2)}`,
# #     `>${e[4].toFixed(2)}`
# #   ];
# #   if(pieChart) pieChart.destroy();
# #   pieChart=new Chart(document.getElementById("pie-classes"),{
# #     type:"pie",
# #     data:{ labels, datasets:[{ data:counts, backgroundColor:COLORS }]},
# #     options:{ responsive:true, plugins:{ legend:{ position:"bottom" } } }
# #   });
# #   document.getElementById("pie-caption").textContent = `Global class edges; colors match overlay maps. Year ${year}.`;
# # }

# # function updateMap(year){
# #   const img=document.getElementById("year-map");
# #   img.src=`/map/soil_loss_on_basemap_${year}.png`;
# #   img.alt=`Soil loss on basemap — ${year}`;
# # }

# # # async function updateYear(year){
# # #   currentYear=year;
# # #   updateMap(year);
# # #   await updatePie(year);
# # # }

# # async function updateYear(year){
# #   currentYear = year;
# #   updateMap(year);
# #   await updatePie(year);
# #   fillStatsTable(year);   // <-- NEW LINE
# # }


# # function showAllYears(){
# #   if(YEARS.length) updateYear(YEARS[YEARS.length-1]);
# # }

# # (async function boot(){
# #   YEARS = await getJSON("/api/years");
# #   STATS = await getJSON("/api/stats");
# #   buildYearButtons();
# #   drawTrends();

# #   // define default year BEFORE using it
# #   const defY = YEARS[YEARS.length-1] || 2025;

# #   // fill table only for default year
# #   fillStatsTable(defY);

# #   // load map + pie for default year
# #   updateYear(defY);
# # })();
# # </script>
# # </body>
# # </html>
# #     """
# #     return render_template_string(html)

# # @app.route("/api/years")
# # def api_years():
# #     return jsonify(YEARS)

# # @app.route("/api/stats")
# # def api_stats():
# #     if len(MASTER_STATS) == 0:
# #         rows = []
# #         trend = {"years": [], "mean": [], "median": []}
# #         return jsonify({"rows": rows, "trend": trend})
# #     rows = MASTER_STATS.to_dict(orient="records")
# #     trend = {
# #         "years": [int(x) for x in MASTER_STATS["year"].tolist()],
# #         "mean":  [float(x) for x in MASTER_STATS["mean"].tolist()],
# #         "median":[float(x) for x in MASTER_STATS["median"].tolist()],
# #     }
# #     return jsonify({"rows": rows, "trend": trend})

# # @app.route("/api/classes/<int:year>")
# # def api_classes(year):
# #     r = _read_a(year)
# #     if not r:
# #         return jsonify({"edges": GLOBAL_EDGES.tolist(), "counts": [0,0,0,0,0]})
# #     a, nod = r
# #     m = (a != nod) & (a >= 0)
# #     bins = GLOBAL_EDGES
# #     cls = np.digitize(a[m], bins, right=False) - 1  # 0..4
# #     counts = [int((cls == i).sum()) for i in range(5)]
# #     return jsonify({"edges": [float(x) for x in bins], "counts": counts})

# # @app.route("/map/<path:filename>")
# # def serve_map(filename):
# #     return send_from_directory(MAP_DIR, filename)

# # @app.route("/api/maps")
# # def api_maps():
# #     files = sorted(glob.glob(str(MAP_DIR / "soil_loss_on_basemap_*.png")))
# #     return jsonify(files)

# # # --------------------------------------------------------------------------------------
# # # Main
# # # --------------------------------------------------------------------------------------
# # if __name__ == "__main__":
# #     # Run: python scripts/09_dashboard_web.py
# #     # Requires: pip install flask pandas numpy rasterio
# #     app.run(host="127.0.0.1", port=5001, debug=True)

# # scripts/09_dashboard_web.py
# # Browser-based RUSLE Dashboard (single file)
# # Uses your overlay maps in outputs/maps/ and A-factor in temp/erosion/
# # Author: Bhavya (integrated by GPT)

# from pathlib import Path
# import glob
# import numpy as np
# import pandas as pd
# from flask import Flask, jsonify, send_from_directory, render_template_string
# import rasterio

# # --------------------------------------------------------------------------------------
# # Paths / config
# # --------------------------------------------------------------------------------------
# BASE = Path(__file__).resolve().parents[1]           # project root
# MAP_DIR   = BASE / "outputs" / "maps"                # soil_loss_on_basemap_<year>.png
# EROS_DIR  = BASE / "temp" / "erosion"                # a_factor_<year>.tif
# STATS_DIR = BASE / "outputs" / "statistics" / "erosion"
# NODATA = -9999.0

# app = Flask(__name__)

# # --------------------------------------------------------------------------------------
# # Helpers
# # --------------------------------------------------------------------------------------
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
#     # fallback: parse names
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
#     """Quantile-based 5-bin edges across all years; matches map classification spirit."""
#     samples = []
#     for y in range(2016, 2026):
#         r = _read_a(y)
#         if not r:
#             continue
#         a, nod = r
#         v = a[(a != nod) & (a >= 0)]
#         if v.size == 0:
#             continue
#         if v.size > 800_000:
#             idx = np.random.choice(v.size, 800_000, replace=False)
#             v = v[idx]
#         samples.append(v)
#     if not samples:
#         # Safe default bands (won't crash)
#         return np.array([0.0, 0.05, 0.20, 0.80, 3.20, 1e9], dtype=np.float64)
#     allv = np.concatenate(samples)
#     q = np.quantile(allv, [0.50, 0.75, 0.90, 0.97])  # 50/75/90/97 percentiles -> 5 classes
#     hi = float(np.nanmax(allv)) + 1e-6
#     edges = np.array([0.0, q[0], q[1], q[2], q[3], hi], dtype=np.float64)
#     return edges

# MASTER_STATS = _load_master_stats()
# GLOBAL_EDGES = _compute_global_edges()
# YEARS = _years_with_maps() or (MASTER_STATS["year"].tolist() if len(MASTER_STATS) else list(range(2016, 2026)))
# YEARS = sorted(set(YEARS))

# # --------------------------------------------------------------------------------------
# # Routes
# # --------------------------------------------------------------------------------------
# @app.route("/")
# def index():
#     # Inline Bootstrap + Chart.js + minimal CSS to keep it single-file.
#     # Soil Degradation palette (Very Low→Very High): Green→Red
#     html = r"""
# <!doctype html>
# <html lang="en">
# <head>
#   <meta charset="utf-8"/>
#   <title>RUSLE Soil Erosion Dashboard — Mula-Mutha (2016–2025)</title>
#   <meta name="viewport" content="width=device-width, initial-scale=1"/>
#   <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet"/>
#   <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3"></script>
#   <style>
#     body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial; }
#     header { background: #1f2937; }
#     header h2 { color: #fff; }
#     header .sub { color: #cbd5e1; }
#     #map-wrap img { object-fit: contain; background: #dfe6e9; }
#     .table td, .table th { vertical-align: middle; }
#     .btn-year { font-weight: 700 !important; }
#   </style>
# </head>
# <body class="bg-light">
#   <header class="py-3 mb-3 border-bottom">
#     <div class="container">
#       <h2 class="mb-0 fw-bold">🌍 RUSLE Soil Erosion Analysis Dashboard</h2>
#       <div class="sub small">Mula-Mutha River Catchment, Pune | 2016–2025 | MSc Geoinformatics Project</div>
#     </div>
#   </header>

#   <main class="container">
#     <!-- Year selector -->
#     <section class="mb-3 p-3 bg-white rounded-3 shadow-sm">
#       <div class="d-flex align-items-center flex-wrap gap-2">
#         <span class="fw-bold me-2">Select Year:</span>
#         <div id="year-buttons" class="d-flex flex-wrap gap-2"></div>
#         <button id="btn-all" class="btn btn-sm btn-danger fw-bold ms-2">ALL YEARS</button>
#       </div>
#     </section>

#     <!-- Stats table -->
#     <section class="mb-3 p-3 bg-white rounded-3 shadow-sm">
#       <h6 class="fw-bold mb-2">📊 Annual Statistics Summary</h6>
#       <div class="table-responsive">
#         <table class="table table-sm table-hover align-middle mb-0" id="stats-table">
#           <thead class="table-light">
#             <tr>
#               <th>Year</th>
#               <th>Mean (t/ha/yr)</th>
#               <th>Median (t/ha/yr)</th>
#               <th>Max (t/ha/yr)</th>
#               <th>Coverage (%)</th>
#               <th>Valid Pixels</th>
#             </tr>
#           </thead>
#           <tbody></tbody>
#         </table>
#       </div>
#     </section>

#     <!-- Big Map -->
#     <section class="mb-3 p-3 bg-white rounded-3 shadow-sm">
#       <h6 class="fw-bold mb-2">🗺️ Soil Loss (A) on Colored Basemap</h6>
#       <div class="ratio ratio-16x9 border rounded-3 bg-dark-subtle" id="map-wrap">
#         <img id="year-map" alt="Map" class="w-100 h-100"/>
#       </div>
#       <div id="map-caption" class="small text-muted mt-1">
#         Basemap: Esri WorldTopoMap with expanded extent; AOI overlay uses the Soil Degradation palette.
#       </div>
#     </section>

#     <!-- Charts -->
#     <section class="row g-3">
#       <div class="col-lg-4">
#         <div class="p-3 bg-white rounded-3 shadow-sm h-100">
#           <h6 class="fw-bold mb-2">📈 Erosion Class Distribution</h6>
#           <canvas id="pie-classes"></canvas>
#           <div class="small mt-2 text-muted" id="pie-caption"></div>
#         </div>
#       </div>
#       <div class="col-lg-4">
#         <div class="p-3 bg-white rounded-3 shadow-sm h-100">
#           <h6 class="fw-bold mb-2">📊 Mean Erosion Trend</h6>
#           <canvas id="mean-trend"></canvas>
#         </div>
#       </div>
#       <div class="col-lg-4">
#         <div class="p-3 bg-white rounded-3 shadow-sm h-100">
#           <h6 class="fw-bold mb-2">📊 Median Erosion Trend</h6>
#           <canvas id="median-trend"></canvas>
#         </div>
#       </div>
#     </section>

#     <div class="my-4"></div>
#   </main>

# <script>
# let YEARS = [];
# let STATS = { rows: [], trend: { years: [], mean: [], median: [] } };
# let currentYear = null;

# let pieChart = null;
# let meanChart = null;
# let medianChart = null;

# // Soil Degradation palette (Very Low→Very High)
# const COLORS = ["#006837","#7CB342","#FFEB3B","#FF9800","#D32F2F"];

# async function getJSON(url){ const r=await fetch(url); if(!r.ok) throw new Error("HTTP "+r.status); return r.json(); }
# function fmt(n,d=2){ return (n===null||n===undefined||Number.isNaN(n)) ? "—" : Number(n).toFixed(d); }

# function buildYearButtons(){
#   const wrap=document.getElementById("year-buttons"); wrap.innerHTML="";
#   YEARS.forEach(y=>{
#     const b=document.createElement("button");
#     b.className="btn btn-sm btn-primary btn-year";
#     b.textContent=y;
#     b.onclick=()=>updateYear(y);
#     wrap.appendChild(b);
#   });
#   document.getElementById("btn-all").onclick=showAllYears;
# }

# // Fill the stats table.
# // - If selectedYear is a Number -> show only that year row
# // - If selectedYear is null/undefined -> show ALL rows
# function fillStatsTable(selectedYear = undefined){
#   const body = document.querySelector("#stats-table tbody");
#   body.innerHTML = "";

#   // Defensive: make sure STATS.rows exists
#   const rows = (STATS && Array.isArray(STATS.rows)) ? STATS.rows : [];

#   if(rows.length === 0){
#     body.innerHTML = '<tr><td colspan="6" class="text-muted">No statistics available</td></tr>';
#     return;
#   }

#   // Show all years if selectedYear is null/undefined
#   if (selectedYear === null || selectedYear === undefined) {
#     rows.forEach(r=>{
#       const tr=document.createElement("tr");
#       tr.innerHTML = `
#         <td class="fw-bold">${r.year}</td>
#         <td>${fmt(r.mean)}</td>
#         <td>${fmt(r.median)}</td>
#         <td>${fmt(r.max)}</td>
#         <td>${fmt(r.coverage_pct)}</td>
#         <td>${r.valid_count}</td>`;
#       tr.onclick = () => updateYear(Number(r.year));
#       body.appendChild(tr);
#     });
#     return;
#   }

#   // Otherwise show only the requested year (tolerant about string/number)
#   const target = Number(selectedYear);
#   const row = rows.find(r => Number(r.year) === target);

#   if (!row) {
#     body.innerHTML = `<tr><td colspan="6" class="text-muted">No data for year ${selectedYear}</td></tr>`;
#     return;
#   }

#   const tr=document.createElement("tr");
#   tr.innerHTML = `
#     <td class="fw-bold">${row.year}</td>
#     <td>${fmt(row.mean)}</td>
#     <td>${fmt(row.median)}</td>
#     <td>${fmt(row.max)}</td>
#     <td>${fmt(row.coverage_pct)}</td>
#     <td>${row.valid_count}</td>`;
#   tr.onclick = () => updateYear(Number(row.year));
#   body.appendChild(tr);
# }

# function drawTrends(){
#   const yrs = (STATS && STATS.trend && Array.isArray(STATS.trend.years)) ? STATS.trend.years : [];
#   const means = (STATS && STATS.trend && Array.isArray(STATS.trend.mean)) ? STATS.trend.mean : [];
#   const med = (STATS && STATS.trend && Array.isArray(STATS.trend.median)) ? STATS.trend.median : [];

#   if(meanChart) meanChart.destroy();
#   meanChart=new Chart(document.getElementById("mean-trend"),{
#     type:"bar",
#     data:{ labels:yrs, datasets:[{ label:"Mean (t/ha/yr)", data:means }]},
#     options:{ responsive:true, scales:{y:{beginAtZero:true}}, plugins:{legend:{display:false}}}
#   });

#   if(medianChart) medianChart.destroy();
#   medianChart=new Chart(document.getElementById("median-trend"),{
#     type:"line",
#     data:{ labels:yrs, datasets:[{ label:"Median (t/ha/yr)", data:med, tension:0.25, fill:true }]},
#     options:{ responsive:true, scales:{y:{beginAtZero:true}}, plugins:{legend:{display:false}}}
#   });
# }

# async function updatePie(year){
#   const res=await getJSON(`/api/classes/${year}`);
#   const e=res.edges, counts=res.counts;
#   const labels=[
#     `${e[0].toFixed(2)}–${e[1].toFixed(02)}`.replace('02','2'),
#     `${e[1].toFixed(2)}–${e[2].toFixed(2)}`,
#     `${e[2].toFixed(2)}–${e[3].toFixed(2)}`,
#     `${e[3].toFixed(2)}–${e[4].toFixed(2)}`,
#     `>${e[4].toFixed(2)}`
#   ];
#   if(pieChart) pieChart.destroy();
#   pieChart=new Chart(document.getElementById("pie-classes"),{
#     type:"pie",
#     data:{ labels, datasets:[{ data:counts, backgroundColor:COLORS }]},
#     options:{ responsive:true, plugins:{ legend:{ position:"bottom" } } }
#   });
#   document.getElementById("pie-caption").textContent = `Global class edges; colors match overlay maps. Year ${year}.`;
# }

# function updateMap(year){
#   const img=document.getElementById("year-map");
#   img.src=`/map/soil_loss_on_basemap_${year}.png`;
#   img.alt=`Soil loss on basemap — ${year}`;
# }

# async function updateYear(year){
#   currentYear = year;
#   updateMap(year);
#   await updatePie(year);
#   // Show just that year's row (Option A behavior on load too)
#   fillStatsTable(year);
# }

# function showAllYears(){
#   // Keep map/pie showing the latest year, but display the full table.
#   const latest = YEARS.length ? YEARS[YEARS.length - 1] : null;
#   if (latest !== null) {
#     updateYear(latest);   // updates map + pie + sets currentYear + fills single-row table
#   }
#   // Now overwrite table to show ALL rows
#   fillStatsTable(null);   // show all rows
# }

# (async function boot(){
#   YEARS = await getJSON("/api/years");
#   STATS = await getJSON("/api/stats");
#   buildYearButtons();
#   drawTrends();

#   // Option A: show only the latest year's row on load
#   const defY = (YEARS && YEARS.length) ? YEARS[YEARS.length - 1] : 2025;

#   // load map + pie + show single row for default year
#   await updateYear(defY);
# })();
# </script>
# </body>
# </html>
#     """
#     return render_template_string(html)

# @app.route("/api/years")
# def api_years():
#     return jsonify(YEARS)

# @app.route("/api/stats")
# def api_stats():
#     if len(MASTER_STATS) == 0:
#         rows = []
#         trend = {"years": [], "mean": [], "median": []}
#         return jsonify({"rows": rows, "trend": trend})
#     rows = MASTER_STATS.to_dict(orient="records")
#     trend = {
#         "years": [int(x) for x in MASTER_STATS["year"].tolist()],
#         "mean":  [float(x) for x in MASTER_STATS["mean"].tolist()],
#         "median":[float(x) for x in MASTER_STATS["median"].tolist()],
#     }
#     return jsonify({"rows": rows, "trend": trend})

# @app.route("/api/classes/<int:year>")
# def api_classes(year):
#     r = _read_a(year)
#     if not r:
#         return jsonify({"edges": GLOBAL_EDGES.tolist(), "counts": [0,0,0,0,0]})
#     a, nod = r
#     m = (a != nod) & (a >= 0)
#     bins = GLOBAL_EDGES
#     cls = np.digitize(a[m], bins, right=False) - 1  # 0..4
#     counts = [int((cls == i).sum()) for i in range(5)]
#     return jsonify({"edges": [float(x) for x in bins], "counts": counts})

# @app.route("/map/<path:filename>")
# def serve_map(filename):
#     return send_from_directory(MAP_DIR, filename)

# @app.route("/api/maps")
# def api_maps():
#     files = sorted(glob.glob(str(MAP_DIR / "soil_loss_on_basemap_*.png")))
#     return jsonify(files)

# # --------------------------------------------------------------------------------------
# # Main
# # --------------------------------------------------------------------------------------
# if __name__ == "__main__":
#     # Run: python scripts/09_dashboard_web.py
#     # Requires: pip install flask pandas numpy rasterio
#     app.run(host="127.0.0.1", port=5001, debug=True)




# scripts/09_dashboard_web.py
# Browser-based RUSLE Dashboard (single file)
# Uses overlay maps in outputs/maps/ and A-factor in temp/erosion/
# Updated version with smaller charts and optimized layout

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

.map-col { width:60%; float:left; padding-right:10px; }
.chart-col { width:40%; float:right; display:flex; flex-direction:column; gap:10px; }

.chart-card {
    background:white;
    border-radius:8px;
    min-height: 300px !important;
    padding:10px !important;
    box-shadow:0 1px 3px rgba(0,0,0,0.15);
}

#map-wrap img { object-fit:contain; width:100%; height:600px; }

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

<section class="mb-3 p-3 bg-white rounded-3 shadow-sm">
  <span class="fw-bold me-2">Select Year:</span>
  <div id="year-buttons" class="d-flex flex-wrap gap-2 d-inline-block"></div>
  <button id="btn-all" class="btn btn-sm btn-danger fw-bold ms-2">ALL YEARS</button>
</section>

<section class="mb-3 p-3 bg-white rounded-3 shadow-sm">
<h6 class="fw-bold mb-2">Annual Statistics</h6>
<div class="table-responsive">
<table class="table table-sm table-hover align-middle mb-0" id="stats-table">
<thead class="table-light">
<tr>
<th>Year</th>
<th>Mean</th>
<th>Median</th>
<th>Max</th>
<th>Valid Pixels</th>
</tr>
</thead>
<tbody></tbody>
</table>
</div>
</section>

<div class="map-col">
<section class="p-3 bg-white rounded-3 shadow-sm">
<h6 class="fw-bold mb-2">Soil Loss Map</h6>
<div id="map-wrap">
<img id="year-map"/>
</div>
<div id="map-caption" class="small text-muted mt-1"></div>
</section>
</div>

<div class="chart-col">

<div class="chart-card">
<h6 class="fw-bold mb-1" style="font-size:13px;">Erosion Class Distribution</h6>
<canvas id="pie-classes" width="640" height="260"></canvas>
<div id="pie-caption" class="small text-muted"></div>
</div>

<div class="chart-card">
<h6 class="fw-bold mb-1" style="font-size:13px;">Mean Trend</h6>
<canvas id="mean-trend" width="640" height="260"></canvas>
</div>

<div class="chart-card">
<h6 class="fw-bold mb-1" style="font-size:13px;">Median Trend</h6>
<canvas id="median-trend" width="640" height="260"></canvas>
</div>

</div>

</div> <!-- container-fluid -->

<script>
let YEARS = [];
let STATS = { rows:[], trend:{years:[],mean:[],median:[]} };
let currentYear = null;

let pieChart=null, meanChart=null, medianChart=null;

const COLORS = ["#006837","#7CB342","#FFEB3B","#FF9800","#D32F2F"];

async function getJSON(url){
  const r = await fetch(url);
  return r.json();
}

function fmt(n,d=2){ return (n===null||n===undefined||isNaN(n)?"—":Number(n).toFixed(d)); }

function buildYearButtons(){
  const wrap=document.getElementById("year-buttons");
  wrap.innerHTML="";
  YEARS.forEach(y=>{
    let b=document.createElement("button");
    b.className="btn btn-sm btn-primary btn-year";
    b.textContent=y;
    b.onclick=()=>updateYear(y);
    wrap.appendChild(b);
  });
  document.getElementById("btn-all").onclick=showAllYears;
}

function fillStatsTable(year=null){
  const body=document.querySelector("#stats-table tbody");
  body.innerHTML="";
  if(year===null){
    STATS.rows.forEach(r=>{
      let tr=document.createElement("tr");
      tr.innerHTML=`<td>${r.year}</td><td>${fmt(r.mean)}</td><td>${fmt(r.median)}</td><td>${fmt(r.max)}</td><td>${r.valid_count}</td>`;
      tr.onclick=()=>updateYear(r.year);
      body.appendChild(tr);
    });
    return;
  }
  let r=STATS.rows.find(x=>x.year===year);
  if(!r) return;
  let tr=document.createElement("tr");
  tr.innerHTML=`<td>${r.year}</td><td>${fmt(r.mean)}</td><td>${fmt(r.median)}</td><td>${fmt(r.max)}</td><td>${r.valid_count}</td>`;
  body.appendChild(tr);
}

function drawTrends(){
  const yrs=STATS.trend.years;
  const m=STATS.trend.mean;
  const md=STATS.trend.median;

  if(meanChart) meanChart.destroy();
  meanChart=new Chart(document.getElementById("mean-trend"),{
    type:"bar",
    data:{ labels:yrs, datasets:[{data:m}] },
    options:{
      responsive:false, maintainAspectRatio:false,
      scales:{ y:{beginAtZero:true}},
      plugins:{ legend:{display:false}}
    }
  });

  if(medianChart) medianChart.destroy();
  medianChart=new Chart(document.getElementById("median-trend"),{
    type:"line",
    data:{ labels:yrs, datasets:[{data:md, tension:0.25}] },
    options:{
      responsive:false, maintainAspectRatio:false,
      scales:{ y:{beginAtZero:true}},
      plugins:{ legend:{display:false}}
    }
  });
}

async function updatePie(year){
  const r=await getJSON(`/api/classes/${year}`);
  const e=r.edges, c=r.counts;
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
    data:{ labels:labels, datasets:[{data:c, backgroundColor:COLORS}] },
    options:{
      responsive:false, maintainAspectRatio:false,
      plugins:{ legend:{position:"bottom", labels:{font:{size:9}}}}
    }
  });
  document.getElementById("pie-caption").textContent = `Year ${year}`;
}

function updateMap(year){
  const img=document.getElementById("year-map");
  if(year===null){
    img.src="";
    return;
  }
  img.src=`/map/soil_loss_on_basemap_${year}.png`;
  img.alt=`Map ${year}`;
  document.getElementById("map-caption").textContent=`Soil loss map for ${year}`;
}

async function updateYear(y){
  currentYear=y;
  updateMap(y);
  fillStatsTable(y);
  await updatePie(y);
}

function showAllYears(){
  fillStatsTable(null);
  updateMap(null);
  if(pieChart) pieChart.destroy();
  document.getElementById("pie-caption").textContent="All Years Overview";
}

(async function boot(){
  YEARS = await getJSON("/api/years");
  STATS = await getJSON("/api/stats");
  buildYearButtons();
  drawTrends();
  const defY = YEARS[YEARS.length-1] || 2025;
  fillStatsTable(defY);
  updateYear(defY);
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
    return jsonify({"rows":rows, "trend":trend})

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

@app.route("/map/<path:filename>")
def serve_map(filename):
    return send_from_directory(MAP_DIR, filename)

# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
