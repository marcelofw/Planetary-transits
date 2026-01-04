import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Scanner de Graus Zodiacais", layout="wide")

# --- FUNÇÕES DE APOIO ---
def dms_to_dec(dms_str):
    if isinstance(dms_str, (int, float)):
        return float(dms_str)
    try:
        parts = str(dms_str).split('.')
        degrees = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0
        return degrees + (minutes / 60)
    except:
        return None

def hex_to_rgba(hex_color, opacity):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

# --- INTERFACE LATERAL ---
st.sidebar.header("🎯 Alvo Zodiacal")
grau_raw = st.sidebar.text_input("Digite o Grau (0 a 30):", value="27.0")
ano = st.sidebar.number_input("Ano da Análise:", value=2026)

# Validação do Grau
grau_decimal = dms_to_dec(grau_raw)
if grau_decimal is None or grau_decimal < 0 or grau_decimal > 30:
    st.error("❌ Erro: Por favor, insira um valor de grau válido entre 0 e 30.")
    st.stop()

st.sidebar.divider()

# Controle de estado para a Lua
if 'analisar_lua' not in st.session_state:
    st.session_state.analisar_lua = False

if st.sidebar.button("🌙 Quero analisar a Lua"):
    st.session_state.analisar_lua = True

mes_selecionado = None
if st.session_state.analisar_lua:
    mes_selecionado = st.sidebar.select_slider(
        "Selecione o mês para a Lua:",
        options=list(range(1, 13)),
        format_func=lambda x: [
            "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", 
            "Jul", "Ago", "Set", "Out", "Nov", "Dez"
        ][x-1]
    )
    if st.sidebar.button("Recolher Análise da Lua"):
        st.session_state.analisar_lua = False
        st.rerun()

# --- CÁLCULO DE EFEMÉRIDES ---
@st.cache_data
def get_transit_data(grau_val, ano_ref, analisar_lua, mes_lua):
    planetas_base = [
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
    
    if analisar_lua and mes_lua:
        planetas_base.insert(1, {"id": swe.MOON, "nome": "LUA", "cor": "#C37DEB"})
        jd_start = swe.julday(ano_ref, mes_lua, 1)
        if mes_lua == 12:
            jd_end = swe.julday(ano_ref + 1, 1, 1)
        else:
            jd_end = swe.julday(ano_ref, mes_lua + 1, 1)
    else:
        jd_start = swe.julday(ano_ref, 1, 1)
        jd_end = swe.julday(ano_ref + 1, 1, 1)

    step_size = 0.005 
    steps = np.arange(jd_start, jd_end, step_size)
    
    results = []
    for jd in steps:
        y, m, d, h = swe.revjul(jd)
        dt = datetime(y, m, d, int(h), int((h%1)*60))
        row = {'date': dt}
        
        for p in planetas_base:
            res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH)
            pos_no_signo = res[0] % 30
            dist = abs(((pos_no_signo - grau_val + 15) % 30) - 15)
            
            if dist <= 5:
                row[p["nome"]] = np.exp(-0.5 * (dist / 1.2)**2)
            else:
                row[p["nome"]] = 0
        results.append(row)
    
    return pd.DataFrame(results), planetas_base

df, infos_planetas = get_transit_data(grau_decimal, ano, st.session_state.analisar_lua, mes_selecionado)

# --- CONSTRUÇÃO DO GRÁFICO ---
st.title(f"🔭 Revolução planetária: Grau {grau_raw}°")

fig = go.Figure()

for p in infos_planetas:
    if p["nome"] in df.columns:
        fig.add_trace(go.Scatter(
            x=df['date'], y=df[p['nome']],
            mode='lines',
            name=p['nome'],
            line=dict(color=p['cor'], width=2),
            fill='tozeroy',
            fillcolor=hex_to_rgba(p['cor'], 0.12),
            # O SEGREDO: Template vazio oculta o nome do planeta e a linha colorida no hover
            hovertemplate="",
            showlegend=True 
        ))

        peak_mask = (df[p['nome']] > 0.98) & (df[df.columns.intersection([p['nome']])].squeeze() > df[df.columns.intersection([p['nome']])].squeeze().shift(1)) & (df[df.columns.intersection([p['nome']])].squeeze() > df[df.columns.intersection([p['nome']])].squeeze().shift(-1))
        picos = df[peak_mask]
        
        for _, row in picos.iterrows():
            fig.add_annotation(
                x=row['date'], y=row[p['nome']],
                text=row['date'].strftime('%d/%m'),
                font=dict(color=p['cor'], size=10, family="Arial Black"),
                showarrow=True, arrowhead=1, ax=0, ay=-30,
                bgcolor="rgba(255,255,255,0.85)", bordercolor=p['cor']
            )

fig.update_layout(
    xaxis=dict(
        title="Deslize lateralmente para navegar",
        rangeslider=dict(visible=True, thickness=0.05),
        type='date',
        tickformat='%d/%m\n%Y',
        # Formato da data e hora que aparecerá SOZINHO no hover
        hoverformat='%d/%m/%Y %H:%M'
    ),
    yaxis=dict(title="Proximidade do Grau", range=[0, 1.35], fixedrange=True),
    template='plotly_white',
    dragmode='pan',
    hovermode='x unified',
    height=700,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

# Estilização extra para garantir que a caixa do hover seja minimalista
fig.update_layout(hoverlabel=dict(bgcolor="white", font_size=12))

st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

# Download
html_string = fig.to_html(include_plotlyjs='cdn')
st.download_button(
    label="📥 Baixar Gráfico Interativo",
    data=html_string,
    file_name=f"scanner_grau_{grau_raw.replace('.','_')}_{ano}.html",
    mime="text/html"
)