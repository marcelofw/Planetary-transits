import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Astrologia Interativa 2026", layout="wide")

# --- FUNÇÕES DE APOIO ---
def dms_to_dec(dms_value):
    """Converte Grau.Minuto (float ou str) para Grau Decimal."""
    try:
        parts = str(dms_value).split('.')
        degrees = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0
        return degrees + (minutes / 60)
    except:
        return 0.0

def hex_to_rgba(hex_color, opacity):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

# --- INTERFACE LATERAL (INPUTS) ---
st.sidebar.header("🛡️ Configurações do Trânsito")

# 1. Seletor do Planeta que está transitando
dict_planetas = {
    "MERCÚRIO": swe.MERCURY, "SOL": swe.SUN, "LUA": swe.MOON, 
    "VÊNUS": swe.VENUS, "MARTE": swe.MARS, "JÚPITER": swe.JUPITER, 
    "SATURNO": swe.SATURN, "URANO": swe.URANUS, "NETUNO": swe.NEPTUNE, "PLUTÃO": swe.PLUTO
}
planeta_nome = st.sidebar.selectbox("Selecione o Planeta em Trânsito:", list(dict_planetas.keys()))
planeta_alvo = dict_planetas[planeta_nome]

# 2. Seletor de Ano
ano = st.sidebar.number_input("Ano da Análise:", value=2026)

st.sidebar.divider()
st.sidebar.header("📍 Seus Pontos Natais")
st.sidebar.write("Ajuste os graus (Grau.Minuto):")

# Lista de planetas para o mapa natal com cores padrão
natal_config_base = [
    {"id": "SOL", "pos": 27.00, "cor": "#FFF12E"},
    {"id": "LUA", "pos": 6.20, "cor": "#C37DEB"},
    {"id": "MERCÚRIO", "pos": 19.59, "cor": "#F3A384"},
    {"id": "VÊNUS", "pos": 5.16, "cor": "#0A8F11"},
    {"id": "MARTE", "pos": 8.48, "cor": "#F10808"},
    {"id": "JÚPITER", "pos": 8.57, "cor": "#1746C9"}
]

natal_final = []
for p in natal_config_base:
    col1, col2 = st.sidebar.columns([2, 1])
    with col1:
        novo_grau = st.text_input(f"{p['id']}:", value=str(p['pos']), key=f"deg_{p['id']}")
    with col2:
        nova_cor = st.color_picker("Cor:", value=p['cor'], key=f"col_{p['id']}", label_visibility="collapsed")
    
    natal_final.append({
        "nome": f"{p['id']} ({novo_grau}°)",
        "grau": dms_to_dec(novo_grau),
        "cor": nova_cor
    })

# --- CÁLCULOS ---
@st.cache_data
def get_data(planeta, ano_ref, pontos_natais):
    jd_start = swe.julday(ano_ref, 1, 1)
    jd_end = swe.julday(ano_ref + 1, 1, 1)
    steps = np.arange(jd_start, jd_end, 0.05)
    
    results = []
    for jd in steps:
        res, _ = swe.calc_ut(jd, planeta, swe.FLG_SWIEPH)
        deg_in_sign = res[0] % 30
        
        y, m, d, h = swe.revjul(jd)
        row = {'date': datetime(y, m, d, int(h))}
        
        for p in pontos_natais:
            dist = abs(((deg_in_sign - p["grau"] + 15) % 30) - 15)
            row[p["nome"]] = np.exp(-0.5 * (dist / 1.5)**2) if dist <= 5 else 0
        results.append(row)
    return pd.DataFrame(results)

df = get_data(planeta_alvo, ano, natal_final)

# --- GRÁFICO ---
st.title(f"📊 Trânsitos de {planeta_nome} - {ano}")
fig = go.Figure()

for p in natal_final:
    fig.add_trace(go.Scatter(
        x=df['date'], y=df[p['nome']],
        mode='lines', name=p['nome'],
        line=dict(color=p['cor'], width=2.5),
        fill='tozeroy', fillcolor=hex_to_rgba(p['cor'], 0.1),
        hovertemplate="Data: %{x}<br>Força: %{y:.2f}<extra></extra>"
    ))

    # Anotações de Picos
    peaks = df[(df[p['nome']] > 0.98) & (df[p['nome']] > df[p['nome']].shift(1)) & (df[p['nome']] > df[p['nome']].shift(-1))]
    for _, row in peaks.iterrows():
        fig.add_annotation(
            x=row['date'], y=row[p['nome']], text=row['date'].strftime('%d/%m'),
            font=dict(color=p['cor'], size=10, family="Arial Black"),
            showarrow=True, arrowhead=1, ay=-20, bgcolor="white"
        )

fig.update_layout(
    xaxis=dict(rangeslider=dict(visible=True, thickness=0.05), type='date'),
    yaxis=dict(title='Intensidade do Aspecto', range=[0, 1.3]),
    template='plotly_white', height=700, dragmode='pan', hovermode='x unified'
)

st.plotly_chart(fig, use_container_width=True)