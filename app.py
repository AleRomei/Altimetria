import streamlit as st
import re
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Configurazione pagina Streamlit
st.set_page_config(page_title="Generatore Profilo Altimetrico", layout="wide")

st.title("🏔️ Generatore di Profili Altimetrici con Pendenze")
st.write("Carica il tuo file GPX, scegli un titolo e genera il tuo grafico!")

# Elementi dell'interfaccia utente
titolo_utente = st.text_input("Inserisci il titolo del grafico:", "Il mio percorso")
file_caricato = st.file_uploader("Scegli un file .gpx", type=["gpx"])

# Funzione nativa per calcolare la distanza tra due coordinate (Formula dell'Aversine)
def calcola_distanza_haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0  # Raggio della Terra in metri
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

if file_caricato is not None:
    # Lettura del file GPX caricato
    contenuto_testo = file_caricato.getvalue().decode('utf-8', errors='ignore')
    
    # Estrazione dati con RegEx (immuni a errori XML)
    trkpt_blocks = re.findall(r'<trkpt(.*?)</trkpt>', contenuto_testo, re.DOTALL)
    
    points = []
    for block in trkpt_blocks:
        lat_match = re.search(r'lat=["\']([\d\.-]+)["\']', block)
        lon_match = re.search(r'lon=["\']([\d\.-]+)["\']', block)
        ele_match = re.search(r'<ele>([\d\.-]+)</ele>', block)
        
        if lat_match and lon_match:
            lat = float(lat_match.group(1))
            lon = float(lon_match.group(1))
            ele = float(ele_match.group(1)) if ele_match else 0.0
            points.append((lat, lon, ele))
            
    if not points:
        st.error("Errore: Non è stato possibile estrarre i dati dal file GPX. Controlla che il file contenga punti di traccia.")
    else:
        # Calcoli di distanza e pendenze
        distances = [0.0]
        elevations = [points[0][2]]
        slopes = [0.0]
        
        for i in range(1, len(points)):
            lat1, lon1, ele1 = points[i-1]
            lat2, lon2, ele2 = points[i]
            
            # Uso della nostra funzione matematica nativa
            dist = calcola_distanza_haversine(lat1, lon1, lat2, lon2)
            
            distances.append(distances[-1] + dist / 1000.0)
            elevations.append(ele2)
            
            ele_diff = ele2 - ele1
            slope = (ele_diff / dist) * 100.0 if dist > 0 else 0.0
            slopes.append(slope)
            
        # Filtro per ammorbidire i picchi del GPS
        slopes_smooth = np.convolve(slopes, np.ones(9)/9, mode='same')
        
        # Generazione Grafico Matplotlib (Proporzioni allungate 24x6)
        fig, ax = plt.subplots(figsize=(24, 6), dpi=130)
        colors = ["#3498db", "#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"]
        bounds = [-10, 0, 4, 8, 15, 25]
        cmap = mcolors.BoundaryNorm(bounds, ncolors=len(colors))
        custom_cmap = mcolors.ListedColormap(colors)
        
        min_ele = min(elevations) - 15
        for i in range(len(distances) - 1):
            ax.fill_between([distances[i], distances[i+1]], [elevations[i], elevations[i+1]], min_ele, color=custom_cmap(cmap(slopes_smooth[i])), alpha=0.85)
            
        ax.plot(distances, elevations, color='#2c3e50', linewidth=2.5)
        ax.set_title(titolo_utente, fontsize=18, fontweight='bold', pad=15)
        ax.set_xlabel('Distanza (km)', fontsize=12)
        ax.set_ylabel('Altitudine (m s.l.m.)', fontsize=12)
        ax.set_xlim(0, max(distances))
        ax.set_ylim(min_ele, max(elevations) + 25)
        ax.xaxis.set_major_locator(plt.MaxNLocator(20))
        ax.grid(True, linestyle='--', alpha=0.5)
        
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#3498db', label='Discesa (< 0%)'),
            Patch(facecolor='#2ecc71', label='Pianura / Falsopiano (0% - 4%)'),
            Patch(facecolor='#f1c40f', label='Salita Leggera (4% - 8%)'),
            Patch(facecolor='#e67e22', label='Salita Impegnativa (8% - 15%)'),
            Patch(facecolor='#e74c3c', label='Muro (> 15%)')
        ]
        ax.legend(handles=legend_elements, loc='upper left', frameon=True, facecolor='white', fontsize=11)
        
        plt.tight_layout()
        
        # Mostra il grafico nell'applicazione Web
        st.pyplot(fig)
        
        # Statistiche sotto il grafico
        col1, col2, col3 = st.columns(3)
        col1.metric("Distanza Totale", f"{distances[-1]:.2f} km")
        col2.metric("Quota Massima", f"{int(max(elevations))} m")
        col3.metric("Quota Minima", f"{int(min(elevations))} m")
