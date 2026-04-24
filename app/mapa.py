import streamlit as st
import folium
import osmnx as ox
import numpy as np
import pandas as pd

from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import folium_static
from math import radians, sin, cos, sqrt, atan2

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(page_title="Chile GeoInsight 2026", layout="wide")

st.title("🌍 Chile GeoInsight 2026")
st.write("Dashboard GIS profesional — accesibilidad a hospitales en Santiago 🏥")

# -------------------------
# FUNCIÓN DISTANCIA REAL
# -------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# -------------------------
# DATOS OSM
# -------------------------
center = [-33.45, -70.66]
tags = {"amenity": "hospital"}

gdf = ox.features_from_point(center, tags, dist=15000)

# -------------------------
# MAPA BASE
# -------------------------
m = folium.Map(location=center, zoom_start=10)

cluster = MarkerCluster(name="Hospitales").add_to(m)
heat_data = []
hospital_points = []

# -------------------------
# HOSPITALES
# -------------------------
for _, row in gdf.iterrows():
    geom = row.geometry
    name = row.get("name", "Hospital")

    if geom.geom_type == "Point":
        lat, lon = geom.y, geom.x
    else:
        c = geom.centroid
        lat, lon = c.y, c.x

    folium.Marker(
        location=[lat, lon],
        popup=name
    ).add_to(cluster)

    heat_data.append([lat, lon])
    hospital_points.append((lat, lon))

# -------------------------
# HEATMAP
# -------------------------
HeatMap(heat_data, radius=15, name="Densidad").add_to(m)

# -------------------------
# ACCESIBILIDAD GRID
# -------------------------
lat_range = np.linspace(-33.60, -33.30, 20)
lon_range = np.linspace(-70.80, -70.50, 20)

grid_analysis = []

for lat in lat_range:
    for lon in lon_range:

        min_dist = min(
            haversine(lat, lon, h[0], h[1])
            for h in hospital_points
        )

        grid_analysis.append((lat, lon, min_dist))

        if min_dist > 3:
            color = "red"
        elif min_dist > 1.5:
            color = "orange"
        else:
            color = "green"

        folium.Circle(
            location=[lat, lon],
            radius=700,
            color=color,
            fill=True,
            fill_opacity=0.4,
            popup=f"{min_dist:.2f} km"
        ).add_to(m)

# -------------------------
# INDICADORES
# -------------------------
avg_distance = np.mean([d[2] for d in grid_analysis])
max_distance = np.max([d[2] for d in grid_analysis])
low_access = len([d for d in grid_analysis if d[2] > 3])

# -------------------------
# SIMULACIÓN COMUNAS REALES (BASE PRO)
# -------------------------
comunas = {
    "Santiago Centro": (-33.45, -70.65),
    "La Florida": (-33.52, -70.60),
    "Maipú": (-33.51, -70.75)
}

ranking = {}

for comuna, (clat, clon) in comunas.items():
    ranking[comuna] = sum(
        1 for h in hospital_points
        if haversine(clat, clon, h[0], h[1]) < 3
    )

df_rank = pd.DataFrame(
    ranking.items(),
    columns=["Comuna", "Hospitales cercanos"]
).sort_values(by="Hospitales cercanos")

# -------------------------
# SIDEBAR (CONTROL PRO)
# -------------------------
st.sidebar.header("📊 Métricas GIS")

st.sidebar.metric("🏥 Hospitales", len(hospital_points))
st.sidebar.metric("📍 Distancia promedio", f"{avg_distance:.2f} km")
st.sidebar.metric("🚨 Zonas críticas", low_access)

st.sidebar.subheader("🏙️ Ranking comunal")
st.sidebar.dataframe(df_rank)

# -------------------------
# ALERTA
# -------------------------
if low_access > len(grid_analysis) * 0.3:
    st.error("⚠️ Alta desigualdad en acceso a salud")
else:
    st.success("✅ Cobertura relativamente equilibrada")

# -------------------------
# CAPAS
# -------------------------
folium.LayerControl().add_to(m)

# -------------------------
# MAPA FINAL
# -------------------------
folium_static(m)