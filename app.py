import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Astrologia de Precisão", layout="wide")

# --- FUNÇÕES DE APOIO ---
def dms_to_dec(dms_value):
    try:
        parts = str(dms_value).split('.')
        degrees = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0
        return degrees + (minutes / 60)
    except: return 0.0

def hex_to_rgba(hex_color, opacity):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

# --- INTERFACE LATERAL ---
st.sidebar.header("🛡️ Configurações do Trânsito")

dict_planetas = {
    "SOL": swe.SUN, "LUA": swe.MOON, "MERCÚRIO": swe.MERCURY, 
    "VÊNUS": swe.VENUS, "MARTE": swe.MARS, "JÚPITER": swe.JUPITER, 
    "SATURNO": swe.SATURN, "URANO": swe.URANUS, "NETUNO": swe.NEPTUNE, "PLUTÃO": swe.PLUTO
}

planeta_nome = st.sidebar.selectbox("Planeta em Trânsito:", list(dict_planetas.keys()))
planeta_alvo = dict_planetas[planeta_nome]
ano = st.sidebar.number_input("Ano da Análise:", value=2026)

meses_nomes = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL",
    5: "MAIO", 6: "JUNHO", 7: "JULHO", 8: "AGOSTO",
    9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
}

mes_alvo = 1
if planeta_nome == "LUA":
    mes_alvo = st.sidebar.select_slider("Selecione o Mês:", options=list(meses_nomes.keys()), format_func=lambda x: meses_nomes[x])

st.sidebar.divider()
st.sidebar.header("📍 Seus Pontos Natais")

# Lista expandida de planetas conforme seu script
natal_config_base = [
    {"id": "SOL", "pos": "27.00", "cor": "#FFF12E"},
    {"id": "LUA", "pos": "6.20", "cor": "#C37DEB"},
    {"id": "MERCÚRIO", "pos": "19.59", "cor": "#F3A384"},
    {"id": "VÊNUS", "pos": "5.16", "cor": "#0A8F11"},
    {"id": "MARTE", "pos": "8.48", "cor": "#F10808"},
    {"id": "JÚPITER", "pos": "8.57", "cor": "#1746C9"},
    {"id": "SATURNO", "pos": "20.53", "cor": "#381094"},
    {"id": "URANO", "pos": "26.37", "cor": "#FF00FF"},
    {"id": "NETUNO", "pos": "22.50", "cor": "#1EFF00"},
    {"id": "PLUTÃO", "pos": "28.19", "cor": "#14F1F1"}
]

natal_final = []
for p in natal_config_base:
    col1, col2 = st.sidebar.columns([2, 1])
    with col1:
        val = st.text_input(f"{p['id']}:", value=p['pos'], key=f"deg_{p['id']}")
    with col2:
        cor = st.color_picker("Cor:", value=p['cor'], key=f"col_{p['id']}", label_visibility="collapsed")
    natal_final.append({"nome": f"{p['id']} ({val}°)", "grau": dms_to_dec(val), "cor": cor})

# --- CÁLCULOS DE ALTA PRECISÃO (0.01 = 14 min) ---
@st.cache_data
def get_data(planeta, ano_ref, mes_ref, pontos_natais):
    step_size = 0.01 
    if planeta == swe.MOON:
        jd_start = swe.julday(ano_ref, mes_ref, 1)
        prox_mes = mes_ref + 1 if mes_ref < 12 else 1
        prox_ano = ano_ref if mes_ref < 12 else ano_ref + 1
        jd_end = swe.julday(prox_ano, prox_mes, 1)
    else:
        jd_start = swe.julday(ano_ref, 1, 1)
        jd_end = swe.julday(ano_ref + 1, 1, 1)
    
    steps = np.arange(jd_start, jd_end, step_size)
    results = []
    for jd in steps:
        res, _ = swe.calc_ut(jd, planeta, swe.FLG_SWIEPH)
        deg = res[0] % 30
        y, m, d, h = swe.revjul(jd)
        dt = datetime(y, m, d, int(h), int((h%1)*60))
        row = {'date': dt}
        for p in pontos_natais:
            dist = abs(((deg - p["grau"] + 15) % 30) - 15)
            row[p["nome"]] = np.exp(-0.5 * (dist / 1.5)**2) if dist <= 5 else 0
        results.append(row)
    return pd.DataFrame(results)

df = get_data(planeta_alvo, ano, mes_alvo, natal_final)

# --- GRÁFICO ---
periodo_txt = f"{meses_nomes[mes_alvo]} de {ano}" if planeta_nome == "LUA" else str(ano)
st.title(f"📊 Trânsitos de {planeta_nome} - {periodo_txt}")

fig = go.Figure()
for p in natal_final:
    fig.add_trace(go.Scatter(
        x=df['date'], y=df[p['nome']], name=p['nome'],
        mode='lines', line=dict(color=p['cor'], width=2),
        fill='tozeroy', fillcolor=hex_to_rgba(p['cor'], 0.12),
        hovertemplate="<b>%{x|%d/%m %H:%M}</b><br>Força: %{y:.3f}<extra></extra>"
    ))

    # Anotações de Picos com Seta para Baixo (Vertical)
    peaks = df[(df[p['nome']] > 0.98) & (df[p['nome']] > df[p['nome']].shift(1)) & (df[p['nome']] > df[p['nome']].shift(-1))]
    for _, row in peaks.iterrows():
        fig.add_annotation(
            x=row['date'], y=row[p['nome']], 
            text=row['date'].strftime('%d/%m %H:%M'),
            font=dict(color=p['cor'], size=9, family="Arial Black"),
            showarrow=True, 
            arrowhead=1, 
            ax=0,     # Seta perfeitamente vertical
            ay=-30,   # Distância acima do ponto
            bgcolor="rgba(255,255,255,0.85)", 
            bordercolor=p['cor']
        )

fig.update_layout(
    xaxis=dict(rangeslider=dict(visible=True, thickness=0.05), type='date', tickformat='%d/%m\n%H:%M'),
    yaxis=dict(title='Intensidade do Aspecto', range=[0, 1.35]),
    template='plotly_white', height=700, hovermode='x unified', dragmode='pan'
)

# Download
html_string = fig.to_html(include_plotlyjs='cdn')
st.download_button(
    label="📥 Baixar Gráfico Interativo (.html)",
    data=html_string,
    file_name=f"transitos_{planeta_nome.lower()}_{periodo_txt.replace(' ', '_').lower()}.html",
    mime="text/html"
)

st.plotly_chart(fig, use_container_width=True)