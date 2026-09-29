import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

def draw_diagram():
    fig, ax = plt.subplots(figsize=(28, 16))
    
    fig.patch.set_facecolor('#f0f4f8')
    ax.set_facecolor('#f0f4f8')
    ax.set_xlim(0, 140)
    ax.set_ylim(0, 90)
    ax.axis('off')
    
    # =====================================================================
    # HELPERS
    # =====================================================================
    def node(x, y, w, h, title, subtitle, color, border, icon='', fontsize_t=9, fontsize_s=7.5):
        """Draw a single node with title, subtitle, and optional icon."""
        box = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.3,rounding_size=0.6",
            facecolor=color, edgecolor=border, linewidth=1.8, zorder=3
        )
        ax.add_patch(box)
        
        if icon:
            ax.text(x + w/2, y + h - 1.2, icon, ha='center', va='center',
                    fontsize=13, zorder=4, fontfamily='Segoe UI Emoji')
            ax.text(x + w/2, y + h - 3.0, title, ha='center', va='center',
                    fontsize=fontsize_t, fontweight='bold', color='#1a1a2e', zorder=4, fontfamily='sans-serif')
        else:
            ax.text(x + w/2, y + h - 1.5, title, ha='center', va='center',
                    fontsize=fontsize_t, fontweight='bold', color='#1a1a2e', zorder=4, fontfamily='sans-serif')
        
        # Subtitle lines
        lines = subtitle.split('\n')
        start_y = y + h/2 - 1.0 if icon else y + h/2 - 0.5
        for i, line in enumerate(lines):
            ax.text(x + w/2, start_y - i * 1.5, line, ha='center', va='center',
                    fontsize=fontsize_s, color='#37474f', zorder=4, fontfamily='sans-serif', style='italic')

    def column_header(x, y, w, h, title, color):
        """Draw a column header banner."""
        box = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.2,rounding_size=0.8",
            facecolor=color, edgecolor='none', linewidth=0, zorder=2, alpha=0.9
        )
        ax.add_patch(box)
        ax.text(x + w/2, y + h/2, title, ha='center', va='center',
                fontsize=11, fontweight='bold', color='white', zorder=3, fontfamily='sans-serif')

    def column_bg(x, y, w, h, color, alpha=0.12):
        """Draw a faint column background."""
        box = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.5,rounding_size=1.5",
            facecolor=color, edgecolor=color, linewidth=1.5,
            linestyle='--', alpha=alpha, zorder=1
        )
        ax.add_patch(box)

    def arrow(start, end, color='#546e7a', rad=0.0, lw=1.5, style='-'):
        """Draw a curved arrow."""
        a = FancyArrowPatch(
            start, end,
            connectionstyle=f"arc3,rad={rad}",
            arrowstyle="->,head_width=4,head_length=4",
            color=color, lw=lw, zorder=2, linestyle=style,
            mutation_scale=10
        )
        ax.add_patch(a)
        
    def arrow_right(start, end, color='#546e7a', lw=1.5):
        """Simple straight arrow."""
        ax.annotate('', xy=end, xytext=start,
                    arrowprops=dict(arrowstyle='->', color=color, lw=lw, connectionstyle='arc3,rad=0'),
                    zorder=2)

    def arrow_curved(start, end, color='#546e7a', lw=1.5, rad=0.15):
        ax.annotate('', xy=end, xytext=start,
                    arrowprops=dict(arrowstyle='->', color=color, lw=lw, connectionstyle=f'arc3,rad={rad}'),
                    zorder=2)

    # =====================================================================
    # TITLE
    # =====================================================================
    ax.text(70, 88, "FOREBLENDCAST — TECHNICAL APPROACH", ha='center', va='center',
            fontsize=22, fontweight='bold', color='#0d1b2a', fontfamily='sans-serif', zorder=5)
    ax.text(70, 86, "End-to-End Multi-Model Forecast Blending Pipeline with Human-in-the-Loop Verification & Offline-First Last Mile",
            ha='center', va='center', fontsize=10, color='#546e7a', fontfamily='sans-serif', zorder=5)
    
    # Team badge top-left
    ax.text(3, 87.5, "SIXTH_SENSE\n_CODERS", ha='center', va='center',
            fontsize=9, fontweight='bold', color='#1565c0',
            bbox=dict(facecolor='white', edgecolor='#1565c0', boxstyle='round,pad=0.4', linewidth=2),
            fontfamily='sans-serif', zorder=5)
    
    # SIH badge top-right
    ax.text(136, 87.5, "SMART INDIA\nHACKATHON\n2026", ha='center', va='center',
            fontsize=8, fontweight='bold', color='#2e7d32',
            bbox=dict(facecolor='white', edgecolor='#2e7d32', boxstyle='round,pad=0.4', linewidth=2),
            fontfamily='sans-serif', zorder=5)

    # =====================================================================
    # COLUMN 1: EXTERNAL DATA SOURCES  (x: 1-24)
    # =====================================================================
    col1_x = 1
    column_bg(col1_x, 2, 23, 80, '#1976d2')
    column_header(col1_x + 1, 78, 21, 4, "1. EXTERNAL DATA SOURCES", '#1565c0')
    
    node(col1_x + 2, 68, 19, 8, "WEATHERBENCH2\nARCHIVE", "Google Cloud Storage\n0.25° global grid\n2018, 2020, 2022 test years", '#e3f2fd', '#1976d2', '☁️')
    node(col1_x + 2, 56, 19, 8, "MODEL INPUTS", "ECMWF IFS HRES\nIFS Ensemble (51 mbrs)\nDeepMind GraphCast\nPangu-Weather", '#e3f2fd', '#1976d2', '🌐')
    node(col1_x + 2, 44, 19, 8, "GROUND TRUTH", "ERA5 Reanalysis\nIMD Station Obs\nVGI Citizen Reports", '#e3f2fd', '#1976d2', '📡')
    node(col1_x + 2, 32, 19, 8, "STATIC ASSETS", "geoBoundaries Districts\nWorldPop 2020 Grid\nSRTM Elevation DEM\nIMD Threshold Tables", '#e3f2fd', '#1976d2', '🗺️')
    node(col1_x + 2, 18, 19, 10, "VGI CROWD-\nSOURCED DATA", "Citizen geotagged reports\nRain intensity (mm)\nWaterlog depth (cm)\nPhoto evidence upload\nNDRF field observations", '#e8eaf6', '#3949ab', '📱')

    # =====================================================================
    # COLUMN 2: INGESTION & PRE-PROCESSING  (x: 26-50)
    # =====================================================================
    col2_x = 26
    column_bg(col2_x, 2, 23, 80, '#7b1fa2')
    column_header(col2_x + 1, 78, 21, 4, "2. INGESTION & PRE-PROCESSING", '#6a1b9a')
    
    node(col2_x + 2, 65, 19, 10, "DATA INGESTION\nENGINE", "xarray · dask · gcsfs\nParallel chunk loading\nZarr/NetCDF4 decode\nAutomatic retry + caching", '#f3e5f5', '#7b1fa2', '⚙️')
    node(col2_x + 2, 50, 19, 10, "CANONICAL GRID\nALIGNER", "Bilinear interpolation to\nIMD 0.25° lat/lon grid\n03Z-03Z 24h accumulation\nTime-zone alignment (IST)", '#f3e5f5', '#7b1fa2', '📐')
    node(col2_x + 2, 35, 19, 10, "FEATURE\nENGINEERING", "Season (JJAS/OND/DJF/MAM)\nLead-time index (D+1…D+9)\nTerrain class (Ghats/NER/IGP)\nRegime tag (Active/Break)", '#f3e5f5', '#7b1fa2', '🧬')
    node(col2_x + 2, 18, 19, 12, "VGI PREPROCESSOR\n& VALIDATOR", "GPS→District resolver\nDuplicate/spam filter\nTemporal window match\nQuality score assignment\nPhoto hash dedup", '#ede7f6', '#5e35b1', '🔍')

    # =====================================================================
    # COLUMN 3: CORE SCIENCE ENGINE  (x: 51-78)
    # =====================================================================
    col3_x = 51
    column_bg(col3_x, 2, 25, 80, '#00695c')
    column_header(col3_x + 1.5, 78, 22, 4, "3. CORE SCIENCE ENGINE", '#00695c')
    
    node(col3_x + 2, 66, 21, 9, "VERIFICATION\nENGINE", "RMSE · FSS (25-250 km)\nCost-Loss REV curve\nBrier Skill Score (BSS)\nBootstrap 95% CI", '#e0f2f1', '#00897b', '📊')
    node(col3_x + 2, 53, 21, 9, "ADAPTIVE WEIGHTING\nMODULE", "LightGBM Hierarchical\nShrinkage estimator\nSkillDB historical lookup\nRegime-aware weight decay", '#e0f2f1', '#00897b', '⚖️')
    node(col3_x + 2, 40, 21, 9, "PROBABILITY-MATCHED\nBLENDING", "Quantile mapping\nPreserves extreme peaks\n735 district grid output\nCalibrated PDF ensembles", '#e0f2f1', '#00897b', '🔀')
    node(col3_x + 2, 27, 21, 9, "HAZARD\nCALIBRATION", "Isotonic Regression to\nIMD Risk Tiers (G/Y/O/R)\nHeatwave: Tmax ≥ 40°C\nWind: ≥ 45 km/h Squally", '#e0f2f1', '#00897b', '⚠️')
    node(col3_x + 2, 11, 21, 12, "VGI FEEDBACK\nCALIBRATOR", "Ground-truth vs forecast Δ\nBias correction update\nSkillDB weight adjustment\nSpatial correlation check\nContinuous learning loop", '#e8f5e9', '#2e7d32', '🔄')

    # =====================================================================
    # COLUMN 4: OUTPUT & DISTRIBUTION  (x: 79-108)
    # =====================================================================
    col4_x = 79
    column_bg(col4_x, 2, 26, 80, '#e65100')
    column_header(col4_x + 1.5, 78, 23, 4, "4. OUTPUT & DISTRIBUTION", '#e65100')
    
    node(col4_x + 2, 68, 22, 8, "STATIC JSON\nCONTRACT", "results/ directory tree\nDistrict-level JSON blobs\nHazard tier + probability\nVersion-stamped output", '#fff3e0', '#ef6c00', '📄')
    node(col4_x + 2, 56, 22, 8, "FASTAPI\nSERVER", "Forecast REST API\n/api/forecast/{district}\n/api/health endpoint\nWebSocket live updates", '#fff3e0', '#ef6c00', '🔌')
    node(col4_x + 2, 44, 22, 8, "SMS DISPATCHER", "Backend SMS queue\nMulti-language (5 langs)\nEN/HI/MR/TA/TE\nBatch + priority routing", '#fff3e0', '#ef6c00', '💬')
    node(col4_x + 2, 32, 22, 8, "CAP 1.2 XML\nGENERATOR", "WMO-standard alerts\nNDMA SACHET compliant\nEXERCISE tag for dev\nMachine-readable feed", '#fff3e0', '#ef6c00', '📋')
    node(col4_x + 2, 18, 22, 10, "FORECASTER\nCOCKPIT", "Anomaly detection alerts\nManual weight override\nSign-off & Bulletin dispatch\nIMD official stamp workflow", '#fbe9e7', '#d84315', '👨‍💼')

    # =====================================================================
    # COLUMN 5: FRONTEND, APPS & USERS  (x: 108-138)
    # =====================================================================
    col5_x = 108
    column_bg(col5_x, 2, 30, 80, '#1b5e20')
    column_header(col5_x + 2, 78, 26, 4, "5. FRONTEND, APPS & USERS", '#1b5e20')
    
    node(col5_x + 3, 68, 24, 8, "REACT 18 WEB\nDASHBOARD", "Vite + zustand state\nLeaflet.js choropleth map\n735 district interactive\nDark mode + responsive", '#e8f5e9', '#2e7d32', '🖥️')
    node(col5_x + 3, 56, 24, 8, "IMPACT-BASED\nPERSONA CARDS", "Farmer · Fisher · DM\nWorldPop exposed pop\nLocalized risk guidance\nWMO-1150 compliant", '#e8f5e9', '#2e7d32', '🎯')
    node(col5_x + 3, 44, 24, 8, "GROUNDED\nFORE-CASTER COPILOT", "Google Gemini AI\nContext-aware analysis\nExplainability narratives\nWeight attribution cards", '#e8f5e9', '#2e7d32', '🤖')
    node(col5_x + 3, 32, 24, 8, "ANDROID SMS\nGATEWAY APP", "Kotlin offline-first\nSMS queue processing\nMesh network fallback\nGPS \"Mera Sthan\" detect", '#e8f5e9', '#2e7d32', '📲')
    node(col5_x + 3, 18, 24, 10, "END USERS", "Citizens (public alerts)\nFarmers (crop advisories)\nFishers (sea-state warnings)\nDistrict Magistrates (EOC)\nNDRF Field Officers", '#c8e6c9', '#1b5e20', '👥')

    # =====================================================================
    # ARROWS — Left to Right Pipeline Flow
    # =====================================================================
    
    # Col1 -> Col2 (Data Sources -> Ingestion)
    arrow_right((22, 72), (28, 72), '#1976d2', 2)  # WeatherBench -> Ingestion Engine
    arrow_right((22, 60), (28, 68), '#1976d2', 2)  # Model Inputs -> Ingestion Engine
    arrow_right((22, 48), (28, 55), '#1976d2', 2)  # Ground Truth -> Grid Aligner
    arrow_right((22, 36), (28, 43), '#1976d2', 2)  # Static Assets -> Feature Eng
    arrow_right((22, 24), (28, 27), '#3949ab', 2)  # VGI -> VGI Preprocessor
    
    # Col2 -> Col3 (Ingestion -> Science)
    arrow_right((47, 72), (53, 72), '#7b1fa2', 2)  # Ingestion -> Verification
    arrow_right((47, 55), (53, 58), '#7b1fa2', 2)  # Grid Aligner -> Adaptive Weighting
    arrow_right((47, 40), (53, 45), '#7b1fa2', 2)  # Feature Eng -> Prob Blending
    arrow_right((47, 27), (53, 18), '#5e35b1', 2)  # VGI Preproc -> VGI Calibrator
    
    # Internal Col3 vertical flow
    arrow_right((63, 66), (63, 62), '#00897b', 1.5)  # Verification -> Adaptive
    arrow_right((63, 53), (63, 49), '#00897b', 1.5)  # Adaptive -> Blending
    arrow_right((63, 40), (63, 36), '#00897b', 1.5)  # Blending -> Hazard
    
    # Col3 -> Col4 (Science -> Output)
    arrow_right((74, 72), (81, 72), '#00695c', 2)  # Verification -> JSON
    arrow_right((74, 58), (81, 60), '#00695c', 2)  # Adaptive -> FastAPI
    arrow_right((74, 44), (81, 48), '#00695c', 2)  # Blending -> SMS
    arrow_right((74, 32), (81, 36), '#00695c', 2)  # Hazard -> CAP XML
    
    # Internal Col4 vertical flow
    arrow_right((92, 68), (92, 64), '#ef6c00', 1.5)  # JSON -> FastAPI
    arrow_right((92, 56), (92, 52), '#ef6c00', 1.5)  # FastAPI -> SMS
    arrow_right((92, 44), (92, 40), '#ef6c00', 1.5)  # SMS -> CAP XML
    arrow_right((92, 32), (92, 28), '#ef6c00', 1.5)  # CAP -> Cockpit
    
    # Col4 -> Col5 (Output -> Frontend)
    arrow_right((103, 72), (111, 72), '#e65100', 2)  # JSON -> React Dashboard
    arrow_right((103, 60), (111, 60), '#e65100', 2)  # FastAPI -> Impact Cards
    arrow_right((103, 48), (111, 48), '#e65100', 2)  # SMS -> Copilot
    arrow_right((103, 36), (111, 36), '#e65100', 2)  # CAP -> Android App
    arrow_right((103, 24), (111, 24), '#d84315', 2)  # Cockpit -> End Users
    
    # =====================================================================
    # CROSS-FUNCTIONAL FEEDBACK LOOPS (the differentiator)
    # =====================================================================
    
    # VGI Feedback Loop: End Users -> VGI Data Source (big curved arrow along bottom)
    arrow_curved((120, 18), (14, 18), '#e91e63', 2.5, -0.15)
    
    # VGI Calibrator -> SkillDB / Adaptive Weighting (upward feedback in col3)
    arrow_curved((63, 23), (63, 53), '#e91e63', 2.0, 0.3)
    
    # Cockpit sign-off -> back to Blending (human override loop)
    arrow_curved((81, 24), (74, 44), '#ff6f00', 2.0, -0.25)
    
    # Label the feedback loops
    ax.text(55, 5, "← CLOSED-LOOP VGI GROUND-TRUTH CALIBRATION →",
            ha='center', va='center', fontsize=10, fontweight='bold', color='#c2185b',
            bbox=dict(facecolor='#fce4ec', edgecolor='#e91e63', boxstyle='round,pad=0.5', linewidth=1.5),
            fontfamily='sans-serif', zorder=5, style='italic')
    
    ax.text(77, 14, "FORECASTER\nOVERRIDE LOOP",
            ha='center', va='center', fontsize=7.5, fontweight='bold', color='#e65100',
            bbox=dict(facecolor='#fff3e0', edgecolor='#ff6f00', boxstyle='round,pad=0.3', linewidth=1.5),
            fontfamily='sans-serif', zorder=5)
    
    ax.text(55, 14, "CONTINUOUS\nLEARNING",
            ha='center', va='center', fontsize=7.5, fontweight='bold', color='#2e7d32',
            bbox=dict(facecolor='#e8f5e9', edgecolor='#2e7d32', boxstyle='round,pad=0.3', linewidth=1.5),
            fontfamily='sans-serif', zorder=5)

    # =====================================================================
    # TECH STACK SIDEBAR (bottom-right corner)
    # =====================================================================
    # Small tech badges
    tech_y = 7
    ax.text(120, tech_y + 5, "TECH STACK", ha='center', va='center',
            fontsize=10, fontweight='bold', color='#263238', fontfamily='sans-serif', zorder=5)
    
    techs = [
        ("Python · xarray · dask", '#1976d2'),
        ("LightGBM · scikit-learn", '#7b1fa2'),
        ("FastAPI · WebSocket", '#e65100'),
        ("React 18 · Vite · Leaflet", '#2e7d32'),
        ("Kotlin · Android SMS", '#00695c'),
        ("Google Gemini AI", '#d32f2f'),
    ]
    for i, (tech, col) in enumerate(techs):
        ax.text(120, tech_y + 3 - i * 1.8, tech, ha='center', va='center',
                fontsize=7.5, fontweight='bold', color=col,
                bbox=dict(facecolor='white', edgecolor=col, boxstyle='round,pad=0.3', linewidth=1),
                fontfamily='sans-serif', zorder=5)

    # =====================================================================
    # SAVE
    # =====================================================================
    plt.tight_layout(pad=0.5)
    plt.savefig('e:/sihworkspace/docs/foreblendcast_architecture_v2.png', dpi=250, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print("Done! Saved to e:/sihworkspace/docs/foreblendcast_architecture_v2.png")

if __name__ == "__main__":
    draw_diagram()
