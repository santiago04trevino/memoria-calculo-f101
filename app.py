import streamlit as st
import pandas as pd
import numpy as np
import math

# Configuración de la página
st.set_page_config(page_title="Diseño Mecánico F-101", page_icon="⚙️", layout="wide")

# ==============================================================================
# BASE DE DATOS DE MATERIALES Y BOQUILLAS
# ==============================================================================
base_datos_materiales = {
    "SA-240 Tipo 316L": {"E": 193000.0, "Sy": 170.0, "A_codo": 3.25e-4, "alta_aleacion": True},
    "SA-240 Tipo 304L": {"E": 193000.0, "Sy": 205.0, "A_codo": 3.63e-4, "alta_aleacion": True},
    "SA-204 Gr. A": {"E": 200000.0, "Sy": 250.0, "A_codo": 3.90e-4, "alta_aleacion": False},
    "SA-516 Gr. 70": {"E": 200000.0, "Sy": 260.0, "A_codo": 4.10e-4, "alta_aleacion": False},
    "SA-285 Gr. C": {"E": 193000.0, "Sy": 205.0, "A_codo": 3.80e-4, "alta_aleacion": False}
}

boquillas_db = {
    "N1 (Alimentación)": {"Q_m3h": 8820.96, "rho": 0.505, "mu": 1.09e-3, "Do_mm": 457.0, "t_nom": 4.78, "t_table": 8.34},
    "N2 (Vapor)": {"Q_m3h": 8817.76, "rho": 0.148, "mu": 0.008e-3, "Do_mm": 457.0, "t_nom": 4.78, "t_table": 8.34},
    "N3 (Líquido)": {"Q_m3h": 3.24, "rho": 972.79, "mu": 1.09e-3, "Do_mm": 33.4, "t_nom": 3.38, "t_table": 2.96}
}

# ==============================================================================
# INTERFAZ LATERAL (SIDEBAR)
# ==============================================================================
st.sidebar.title("⚙️ Parámetros de Diseño")
st.sidebar.markdown("### Separador Flash Vertical F-101")

D_i = st.sidebar.number_input("Diámetro Interior (mm)", value=1000.0, step=50.0)
L = st.sidebar.number_input("Longitud Cilíndrica (mm)", value=3000.0, step=100.0)
P_ext = st.sidebar.number_input("Presión Externa (MPa)", value=0.101325, format="%.6f")
c_corr = st.sidebar.number_input("Corrosión (mm)", value=1.0, step=0.5)

espesores_str = st.sidebar.text_input("Espesores a evaluar (separados por coma)", "4, 5, 6, 7, 8")
espesores = [float(x.strip()) for x in espesores_str.split(",")]

# ==============================================================================
# FUNCIONES DE CÁLCULO
# ==============================================================================
def calcular_ug28(t_eval, D_i, L, E, A_codo):
    D_o = D_i + (2.0 * t_eval)
    Do_t = D_o / t_eval
    L_Do = L / D_o

    # Ecuación analítica oficial ASME para Factor A
    A_aprox = 1.25 / ((Do_t**1.5) * (L_Do - 0.45 / np.sqrt(Do_t)))
    
    # Cálculo de B (Enfoque conservador elástico para inicio rápido)
    if A_aprox < A_codo:
        B_aprox = (A_aprox * E) / 2.0
    else:
        # Simplificación de régimen plástico para la app
        B_aprox = (A_codo * E) / 2.0 
        
    P_a = (4.0 * B_aprox) / (3.0 * Do_t)
    return D_o, Do_t, L_Do, A_aprox, B_aprox, P_a

def friccion_swamee_jain(Re, eps_D):
    # Ecuación explícita para evitar problemas de convergencia web
    if Re < 2300: return 64.0 / Re
    return 0.25 / (math.log10(eps_D/3.7 + 5.74/(Re**0.9))**2)

# ==============================================================================
# CUERPO PRINCIPAL DE LA APP
# ==============================================================================
st.title("Memoria de Cálculo Automatizada ASME BPVC VIII-1")
st.markdown("Herramienta interactiva para dimensionamiento de equipo sometido a presión externa y evaluación hidráulica de boquillas.")

tab1, tab2 = st.tabs(["🏗️ Envolvente (UG-28 & UHA-23)", "🚿 Boquillas (Hidráulica & UG-45)"])

# ----------------- PESTAÑA 1: ENVOLVENTE -----------------
with tab1:
    st.header("Análisis de Estabilidad Geométrica (Vacío)")
    
    resultados_env = []
    
    for mat, props in base_datos_materiales.items():
        for t in espesores:
            D_o, Do_t, L_Do, A, B, Pa = calcular_ug28(t, D_i, L, props["E"], props["A_codo"])
            cumple = "✅ CUMPLE" if Pa >= P_ext else "❌ NO CUMPLE"
            
            # Ajuste de corrosión si es alta aleación
            t_diseno = t + c_corr if props["alta_aleacion"] and Pa >= P_ext else t
            
            resultados_env.append({
                "Material": mat,
                "t eval (mm)": t,
                "Do/t": round(Do_t, 2),
                "Factor A": f"{A:.2e}",
                "Factor B (MPa)": round(B, 2),
                "Pa (MPa)": round(Pa, 4),
                "Dictamen": cumple,
                "t Diseño Final (mm)": t_diseno
            })
            
    df_env = pd.DataFrame(resultados_env)
    
    st.dataframe(df_env.style.map(
        lambda v: 'background-color: #d4edda; color: green;' if '✅' in str(v) else ('background-color: #f8d7da; color: red;' if '❌' in str(v) else ''),
        subset=['Dictamen']
    ), use_container_width=True)

# ----------------- PESTAÑA 2: BOQUILLAS -----------------
with tab2:
    st.header("Evaluación Hidráulica y Estándar UG-45")
    
    resultados_boq = []
    for tag, datos in boquillas_db.items():
        # Hidráulica
        Q_m3s = datos["Q_m3h"] / 3600.0
        D_i_m = (datos["Do_mm"] - 2 * datos["t_nom"]) / 1000.0
        v_real = 4 * Q_m3s / (math.pi * D_i_m**2)
        Re = datos["rho"] * v_real * D_i_m / datos["mu"]
        
        f_D = friccion_swamee_jain(Re, 0.015e-3 / D_i_m)
        dP_bar = ((f_D * (10.0 / D_i_m) + 2.0) * (datos["rho"] * v_real**2 / 2)) / 1e5
        
        # UG-45
        t_real_min = 0.875 * datos["t_nom"]
        t_req_estimado = min(datos["t_table"] + c_corr, max(1.5 + c_corr, 2.5)) # Lógica conservadora ASME simplificada
        
        cumple_ug45 = "✅ SEGURO" if t_real_min >= t_req_estimado else "⚠️ REVISAR CÉDULA"
        
        resultados_boq.append({
            "Boquilla": tag,
            "Velocidad (m/s)": round(v_real, 2),
            "Reynolds": f"{Re:.2e}",
            "ΔP (bar)": round(dP_bar, 4),
            "t mínimo fabric. (mm)": round(t_real_min, 2),
            "t requerido UG-45 (mm)": round(t_req_estimado, 2),
            "Dictamen": cumple_ug45
        })
        
    df_boq = pd.DataFrame(resultados_boq)
    st.dataframe(df_boq, use_container_width=True)
    
    st.info("💡 **Nota de Ingeniería:** La caída de presión asume una longitud equivalente de 10m y factores por accesorios genéricos (K=2).")
