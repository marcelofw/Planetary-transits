import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import io

# Configuração da página
st.set_page_config(page_title="Revolução Planetária", layout="wide")

def dms_to_dec(dms_str):
    if isinstance(dms_str, (int, float)):
        return float(dms_str)
    try:
        parts = str(dms_str).split('.')
        degrees = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0
        return degrees + (minutes / 60)
    except:
        return 0.0

def hex_to_rgba(hex_color, opacity):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

# --- INTERFACE LATERAL (Sidebar) ---
st.sidebar.header("🔭 Configurações")
ano = st.sidebar.number_input("Ano da Análise", min_value=1900, max_value=2100, value=2026)
grau_input = st.sidebar.text_input("Grau Alvo Natal (ex: 27.0)", value="27.0")
incluir_lua = st.sidebar.checkbox("Quero analisar a Lua", value=False)

# --- LÓGICA DE DADOS COM CACHE ---
@st.cache_data
def get_planetary_data(ano_ref, grau_ref_str, analisar_lua):
    grau_dec = dms_to_dec(grau_ref_str)
    
    planetas = [
        {"id": swe.SUN, "nome": "SOL", "cor": "#FFF12E"},
        {"id": swe.MERCURY, "nome": "MERCÚRIO", "cor": "#F3A384"},
        {"id": swe.VENUS, "nome": "VÊNUS", "cor": "#0A8F11"},
        {"id": swe.MARS, "nome": "MARTE", "cor": "#F10808"},
        {"id": swe.JUPITER, "nome": "JÚPITER", "cor": "#1746C9"},
        {"id": swe.SATURN, "nome": "SATURNO", "cor": "#381094"},
        {"id": swe.URANUS, "nome": "URANO", "cor": "#FF00FF"},
        {"id": swe.NEPTUNE, "nome": "NETUNO", "cor": "#1EFF00"},
        {"id": swe.PLUTO, "nome": "PLUTÃO", "cor": "#14F1F1"}
    ]
    
    if analisar_lua:
        planetas.insert(1, {"id": swe.MOON, "nome": "LUA", "cor": "#A6A6A6"})

    jd_start = swe.julday(ano_ref, 1, 1)
    jd_end = swe.julday(ano_ref + 1, 1, 1)
    
    # Ajuste de performance: se incluir a lua, o passo precisa ser menor para suavidade
    step_size = 0.01 if analisar_lua else 0.02 
    steps = np.arange(jd_start, jd_end, step_size)
    
    all_data = []
    for jd in steps:
        y, m, d, h = swe.revjul(jd)
        dt = datetime(y, m, d, int(h), int((h%1)*60))
        row = {'date': dt}
        for p in planetas:
            res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH)
            pos_no_signo = res[0] % 30
            dist = abs(((pos_no_signo - grau_dec + 15) % 30) - 15)
            row[p["nome"]] = np.exp(-0.5 * (dist / 1.2)**2) if dist <= 5 else 0
        all_data.append(row)
    
    return pd.DataFrame(all_data), planetas

# Processamento
df, lista_planetas = get_planetary_data(ano, grau_input, incluir_lua)

# --- CONSTRUÇÃO DO GRÁFICO ---
fig = go.Figure()

# Traço invisível para Hover (Data/Hora)
fig.add_trace(go.Scatter(
    x=df['date'], y=[0.65] * len(df),
    mode='lines', line=dict(width=40), opacity=0,
    hoverinfo='x', showlegend=False, name=""
))

for p in lista_planetas:
    fig.add_trace(go.Scatter(
        x=df['date'], y=df[p['nome']],
        mode='lines', name=p['nome'],
        line=dict(color=p['cor'], width=2),
        fill='tozeroy',
        fillcolor=hex_to_rgba(p['cor'], 0.15),
        hoverinfo='skip',
        showlegend=True 
    ))

    # Marcação de picos (apenas se não for a Lua para não poluir, ou todos se preferir)
    if p['nome'] != "LUA" or not incluir_lua:
        peak_mask = (df[p['nome']] > 0.98) & (df[p['nome']] > df[p['nome']].shift(1)) & (df[p['nome']] > df[p['nome']].shift(-1))
        picos = df[peak_mask]
        for _, row in picos.iterrows():
            fig.add_annotation(
                x=row['date'], y=row[p['nome']],
                text=row['date'].strftime('%d/%m'),
                showarrow=True, arrowhead=1, ax=0, ay=-30,
                font=dict(color=p['cor'], size=10, family="Arial Black"),
                bgcolor="rgba(255,255,255,0.85)", bordercolor=p['cor']
            )

fig.update_layout(
    title=dict(text=f'<b>🔭 Revolução Planetária {ano}: Grau {grau_input}°</b>', x=0.5),
    xaxis=dict(
        title='Arraste para navegar no tempo',
        rangeslider=dict(visible=True, thickness=0.08),
        type='date',
        tickformat='%d/%m\n%Y',
        hoverformat='%d/%m/%Y %H:%M',
        showspikes=True,
        spikemode='across',
        spikethickness=1,
        spikedash='solid',
        spikecolor="black"
    ),
    yaxis=dict(title='Intensidade', range=[0, 1.3], fixedrange=True),
    template='plotly_white',
    hovermode='x',
    dragmode='pan',
    height=700,
    hoverlabel=dict(bgcolor="white", font_size=13, namelength=0)
)

# --- EXIBIÇÃO ---
st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

# --- DOWNLOADS ---
st.divider()
col1, col2 = st.columns(2)

with col1:
    # Download do Gráfico HTML
    buffer_html = io.StringIO()
    fig.write_html(buffer_html, config={'scrollZoom': True})
    grau_limpo = grau_input.replace('.', '_')
    st.download_button(
        label="📥 Baixar Gráfico Interativo (HTML)",
        data=buffer_html.getvalue(),
        file_name=f"revolucao_{ano}_grau_{grau_limpo}.html",
        mime="text/html"
    )

with col2:
    # Download dos Dados CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📊 Baixar Dados da Análise (CSV)",
        data=csv,
        file_name=f"dados_{ano}_grau_{grau_limpo}.csv",
        mime="text/csv"
    )