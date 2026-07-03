"""
Application de dimensionnement radio NG-RAN 5G
------------------------------------------------
Approche : couverture (bilan de liaison + modèle de propagation) VS
capacité (Shannon pondéré), avec réconciliation et visualisation
de la zone de bascule couverture/capacité + maillage hexagonal.

Lancer avec :  streamlit run app.py
"""

import math
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon

st.set_page_config(page_title="Dimensionnement NG-RAN 5G", layout="wide")

# ----------------------------------------------------------------------
# Modèles de propagation
# ----------------------------------------------------------------------
def pathloss_to_distance_uma(mapl_db, fc_ghz, h_ue=1.5):
    """3GPP TR 38.901 - UMa NLOS simplifié.
    PL = 13.54 + 39.08*log10(d) + 20*log10(fc) - 0.6*(h_ue-1.5)
    Renvoie d en mètres."""
    log10_d = (mapl_db - 13.54 - 20 * math.log10(fc_ghz) + 0.6 * (h_ue - 1.5)) / 39.08
    return 10 ** log10_d


def pathloss_to_distance_hata(mapl_db, fc_mhz, h_b=30, h_m=1.5, environment="suburbain"):
    """Okumura-Hata (macro, zone ouverte / suburbaine / rurale).
    Renvoie d en km."""
    a_hm = (1.1 * math.log10(fc_mhz) - 0.7) * h_m - (1.56 * math.log10(fc_mhz) - 0.8)
    A = 69.55 + 26.16 * math.log10(fc_mhz) - 13.82 * math.log10(h_b) - a_hm
    B = 44.9 - 6.55 * math.log10(h_b)

    correction = 0
    if environment == "suburbain":
        correction = 2 * (math.log10(fc_mhz / 28)) ** 2 + 5.4
    elif environment == "rural":
        correction = 4.78 * (math.log10(fc_mhz)) ** 2 - 18.33 * math.log10(fc_mhz) + 40.94

    log10_d = (mapl_db - A + correction) / B
    return 10 ** log10_d


# ----------------------------------------------------------------------
# Interface
# ----------------------------------------------------------------------
st.title("📡 Dimensionnement de la partie radio NG-RAN 5G")
st.caption("Bilan de liaison → couverture → capacité → réconciliation, en temps réel.")

with st.sidebar:
    st.header("1. Scénario")
    scenario = st.selectbox("Type de zone", ["Urbain dense", "Suburbain", "Rural"])

    defaults = {
        "Urbain dense": dict(fc=3.5, bw=100, dens=8000, demand=30, act=0.20),
        "Suburbain": dict(fc=2.1, bw=40, dens=1500, demand=25, act=0.15),
        "Rural": dict(fc=0.7, bw=20, dens=150, demand=15, act=0.10),
    }[scenario]

    st.header("2. Paramètres radio")
    fc = st.slider("Fréquence porteuse (GHz)", 0.6, 4.0, defaults["fc"], 0.1)
    bw = st.slider("Bande passante (MHz)", 10, 100, defaults["bw"], 5)
    tx_power = st.slider("Puissance Tx gNB (dBm)", 40, 49, 46)
    antenna_gain = st.slider("Gain antenne gNB (dBi)", 10, 24, 18)
    ue_gain = st.slider("Gain antenne UE (dBi)", -3, 5, 0)
    noise_figure = st.slider("Facteur de bruit UE (dB)", 5, 10, 7)
    shadow_margin = st.slider("Marge de shadowing (dB)", 4, 12, 7)
    penetration_loss = st.slider("Perte de pénétration bâtiment (dB)", 0, 25, 15)
    interference_margin = st.slider("Marge d'interférence (dB)", 0, 6, 3)
    sinr_edge = st.slider("SINR cible bord de cellule (dB)", -5, 10, 1)

    st.header("3. Trafic")
    area_km2 = st.number_input("Surface à couvrir (km²)", 1, 5000, 100)
    user_density = st.slider("Densité d'utilisateurs (users/km²)", 10, 15000, defaults["dens"])
    activity_factor = st.slider("Facteur d'activité simultanée", 0.05, 0.5, defaults["act"])
    demand_per_user = st.slider("Débit moyen requis par utilisateur actif (Mbps)", 1, 100, defaults["demand"])

    st.header("4. Configuration site")
    n_sectors = st.selectbox("Nombre de secteurs par site", [1, 3, 6], index=1)
    mimo_layers = st.selectbox("Couches MIMO", [1, 2, 4, 8], index=2)
    efficiency_factor = st.slider("Facteur d'implémentation (overhead réel)", 0.4, 0.9, 0.6)

# ----------------------------------------------------------------------
# Calcul du bilan de liaison (MAPL)
# ----------------------------------------------------------------------
thermal_noise = -174 + 10 * math.log10(bw * 1e6)  # dBm, bruit thermique sur la bande
receiver_sensitivity = thermal_noise + noise_figure + sinr_edge  # dBm

mapl = (
    tx_power + antenna_gain + ue_gain
    - penetration_loss - shadow_margin - interference_margin
    - receiver_sensitivity
)

# ----------------------------------------------------------------------
# Rayon de cellule (couverture)
# ----------------------------------------------------------------------
if scenario == "Urbain dense":
    R_km = pathloss_to_distance_uma(mapl, fc) / 1000
else:
    env = "suburbain" if scenario == "Suburbain" else "rural"
    R_km = pathloss_to_distance_hata(mapl, fc * 1000, environment=env)

R_km = max(R_km, 0.02)  # borne basse réaliste (20 m)
site_area_km2 = 2.6 * (R_km ** 2) * n_sectors
n_sites_coverage = math.ceil(area_km2 / site_area_km2)

# ----------------------------------------------------------------------
# Capacité
# ----------------------------------------------------------------------
sinr_linear = 10 ** (sinr_edge / 10)
spectral_eff = efficiency_factor * math.log2(1 + sinr_linear)  # bits/s/Hz
sector_throughput_mbps = (bw * 1e6 * spectral_eff * mimo_layers) / 1e6
site_throughput_mbps = sector_throughput_mbps * n_sectors

users_per_site = site_throughput_mbps / demand_per_user
total_active_users = area_km2 * user_density * activity_factor
n_sites_capacity = math.ceil(total_active_users / max(users_per_site, 0.01))

n_sites_final = max(n_sites_coverage, n_sites_capacity)
limiting_factor = "COUVERTURE" if n_sites_coverage >= n_sites_capacity else "CAPACITÉ"

# ----------------------------------------------------------------------
# Affichage résultats
# ----------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("MAPL", f"{mapl:.1f} dB")
c2.metric("Rayon de cellule", f"{R_km*1000:.0f} m")
c3.metric("Sites (couverture)", n_sites_coverage)
c4.metric("Sites (capacité)", n_sites_capacity)

st.subheader(f"✅ Nombre de sites final : {n_sites_final}  —  facteur limitant : **{limiting_factor}**")
st.progress(min(n_sites_coverage, n_sites_capacity) / n_sites_final if n_sites_final else 0)

colA, colB = st.columns(2)

# --- Graphique de sensibilité : bascule couverture / capacité ---
with colA:
    st.markdown("**Sensibilité : bascule couverture ↔ capacité selon la densité d'utilisateurs**")
    dens_range = np.linspace(10, 15000, 60)
    cov_line, cap_line = [], []
    for d in dens_range:
        active = area_km2 * d * activity_factor
        cap_line.append(math.ceil(active / max(users_per_site, 0.01)))
        cov_line.append(n_sites_coverage)  # indépendant de la densité
    fig1, ax1 = plt.subplots()
    ax1.plot(dens_range, cov_line, label="Sites requis (couverture)", linewidth=2)
    ax1.plot(dens_range, cap_line, label="Sites requis (capacité)", linewidth=2)
    ax1.axvline(user_density, color="gray", linestyle="--", label="Densité actuelle")
    ax1.set_xlabel("Densité d'utilisateurs (users/km²)")
    ax1.set_ylabel("Nombre de sites")
    ax1.legend()
    st.pyplot(fig1)

# --- Schéma du maillage hexagonal ---
with colB:
    st.markdown("**Aperçu du maillage hexagonal (échelle du rayon calculé)**")
    fig2, ax2 = plt.subplots()
    ax2.set_aspect("equal")
    rows, cols = 4, 4
    for row in range(rows):
        for col in range(cols):
            x = col * 1.5 * R_km
            y = row * math.sqrt(3) * R_km + (col % 2) * (math.sqrt(3) / 2) * R_km
            hexagon = RegularPolygon((x, y), numVertices=6, radius=R_km,
                                      orientation=math.pi / 6, edgecolor="steelblue",
                                      facecolor="lightblue", alpha=0.5)
            ax2.add_patch(hexagon)
    ax2.set_xlim(-R_km, cols * 1.5 * R_km)
    ax2.set_ylim(-R_km, rows * math.sqrt(3) * R_km)
    ax2.set_xlabel("km")
    ax2.set_ylabel("km")
    st.pyplot(fig2)

# ----------------------------------------------------------------------
# Export synthèse
# ----------------------------------------------------------------------
summary = f"""SYNTHÈSE DE DIMENSIONNEMENT NG-RAN 5G
Scénario : {scenario}
Fréquence : {fc} GHz | Bande passante : {bw} MHz
MAPL calculé : {mapl:.1f} dB
Rayon de cellule : {R_km*1000:.0f} m
Sites requis (couverture) : {n_sites_coverage}
Sites requis (capacité) : {n_sites_capacity}
Nombre de sites final : {n_sites_final}
Facteur limitant : {limiting_factor}
Débit par site : {site_throughput_mbps:.1f} Mbps
Utilisateurs actifs supportés par site : {users_per_site:.0f}
"""
st.download_button("📄 Télécharger la synthèse (pour le rapport)", summary, file_name="synthese_dimensionnement.txt")

with st.expander("Voir le détail des formules utilisées"):
    st.code(summary)