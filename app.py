import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import io
import re

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Revolução Planetária Profissional", layout="wide")

# Silencia avisos de downcasting
pd.set_option('future.no_silent_downcasting', True)

# --- CONSTANTES E FUNÇÕES AUXILIARES ---
SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

ASPECTOS = {
    0: "Conjunção", 30: "Semi-sêxtil", 60: "Sêxtil", 90: "Quadratura", 
    120: "Trígono", 150: "Quincúncio", 180: "Oposição"
}

LISTA_PLANETAS_UI = ["Sol", "Lua", "Mercúrio", "Vênus", "Marte", "Júpiter", "Saturno", "Urano", "Netuno", "Plutão"]

def get_signo(longitude):
    return SIGNOS[int(longitude / 30) % 12]

def dms_to_dec(dms_str):
    if isinstance(dms_str, (int, float)): return float(dms_str)
    try:
        parts = str(dms_str).split('.')
        degrees = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0
        val = degrees + (minutes / 60)
        return val if 0 <= val <= 30 else None
    except:
        return None

def hex_to_rgba(hex_color, opacity):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

def calcular_aspecto(long1, long2):
    diff = abs(long1 - long2) % 360
    if diff > 180: diff = 360 - diff
    for angulo, nome in ASPECTOS.items():
        if abs(diff - angulo) <= 5:
            return nome
    return "Outro"

# --- INTERFACE LATERAL ---
st.sidebar.header("Configurações")
ano = st.sidebar.number_input("Ano da Análise", min_value=1900, max_value=2100, value=2026)
grau_input = st.sidebar.text_input("Grau Natal (0 a 30°)", value="27.0")
planeta_selecionado = st.sidebar.selectbox("Planeta Natal", options=LISTA_PLANETAS_UI, index=0)
signo_selecionado = st.sidebar.selectbox("Signo Natal", options=SIGNOS, index=9) # Default Capricórnio

incluir_lua = st.sidebar.checkbox("Analisar a Lua", value=False)
mes_selecionado = st.sidebar.slider("Mês da Lua", 1, 12, 1) if incluir_lua else None

grau_decimal = dms_to_dec(grau_input)
if grau_decimal is None:
    st.error("⚠️ Erro: Insira um valor válido (ex: 27.0).")
    st.stop()

# Título Principal
st.markdown(f"""
    <div style='text-align: left;'>
        <h1 style='font-size: 2.5rem; margin-bottom: 0;'>🔭 Revolução Planetária {ano}</h1>
        <p style='font-size: 1.2rem; color: #555;'>Ponto Natal: <b>{planeta_selecionado} a {grau_input}° de {signo_selecionado}</b></p>
    </div>
""", unsafe_allow_html=True)

# --- PROCESSAMENTO DE DADOS (LÓGICA DO SCRIPT PYTHON) ---
@st.cache_data
def get_astrological_data(ano_ref, grau_natal_val, planeta_natal_txt, signo_natal_txt, analisar_lua, mes_unico):
    idx_signo = SIGNOS.index(signo_natal_txt)
    long_natal_abs = (idx_signo * 30) + grau_natal_val
    
    planetas_cfg = [
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
    if analisar_lua: planetas_cfg.insert(1, {"id": swe.MOON, "nome": "LUA", "cor": "#A6A6A6"})

    jd_start = swe.julday(ano_ref, mes_unico if mes_unico else 1, 1)
    jd_end = swe.julday(ano_ref + (1 if not mes_unico else 0), (mes_unico + 1 if mes_unico and mes_unico < 12 else 1) if mes_unico else 1, 1)
    steps = np.arange(jd_start, jd_end, 0.05)
    
    all_rows = []
    for jd in steps:
        y, m, d, h = swe.revjul(jd)
        dt = datetime(y, m, d, int(h), int((h%1)*60))
        row = {'date': dt}
        for p in planetas_cfg:
            res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH | swe.FLG_SPEED)
            long_abs, vel = res[0], res[3]
            pos_signo = long_abs % 30
            dist = abs(((pos_signo - grau_natal_val + 15) % 30) - 15)
            
            row[p["nome"]] = np.exp(-0.5 * (dist / 1.7)**2) if dist <= 5.0 else None
            row[f"{p['nome']}_long"] = long_abs
            row[f"{p['nome']}_status"] = "Retrógrado" if vel < 0 else "Direto"
            
            intensidade = "Forte" if dist <= 1.0 else "Médio" if dist <= 2.5 else "Fraco"
            mov_abrev = " (R)" if vel < 0 else " (D)"
            row[f"{p['nome']}_info"] = f"{get_signo(long_abs)}{mov_abrev} {int(pos_signo):02d}°{int((pos_signo%1)*60):02d}' - {intensidade}"
        all_rows.append(row)
    
    df = pd.DataFrame(all_rows).infer_objects(copy=False)
    
    # Geração da Tabela de Aspectos (Igual ao Script Python)
    eventos_aspectos = []
    for p in planetas_cfg:
        nome = p["nome"]
        serie = df[nome].fillna(0).values
        for i in range(1, len(serie) - 1):
            if serie[i] > 0.98 and serie[i] > serie[i-1] and serie[i] > serie[i+1]:
                idx_ini, idx_fim = i, i
                while idx_ini > 0 and serie[idx_ini] > 0.01: idx_ini -= 1
                while idx_fim < len(serie)-1 and serie[idx_fim] > 0.01: idx_fim += 1
                
                row_pico = df.iloc[i]
                long_trans = row_pico[f"{nome}_long"]
                eventos_aspectos.append({
                    "Data e Hora Início": df.iloc[idx_ini]['date'].strftime('%d/%m/%Y %H:%M'),
                    "Data e Hora Pico": row_pico['date'].strftime('%d/%m/%Y %H:%M'),
                    "Data e Hora Término": df.iloc[idx_fim]['date'].strftime('%d/%m/%Y %H:%M'),
                    "Grau Natal": f"{grau_input}°",
                    "Planeta e Signo Natal": f"{planeta_natal_txt} em {signo_natal_txt}",
                    "Planeta e Signo em Trânsito": f"{nome.capitalize()} em {get_signo(long_trans)}",
                    "Trânsito": row_pico[f"{nome}_status"],
                    "Aspecto": calcular_aspecto(long_trans, long_natal_abs)
                })
                
    # Geração da Tabela de Movimento Anual
    mov_anuais = []
    for p in planetas_cfg:
        nome = p["nome"]
        status_at = df.iloc[0][f"{nome}_status"]
        dt_ini = df.iloc[0]['date']
        for i in range(1, len(df)):
            status_pt = df.iloc[i][f"{nome}_status"]
            if status_pt != status_at or i == len(df)-1:
                mov_anuais.append({
                    "Planeta": nome.capitalize(),
                    "Início": dt_ini.strftime('%d/%m/%Y'),
                    "Término": df.iloc[i]['date'].strftime('%d/%m/%Y'),
                    "Trânsito": status_at
                })
                status_at, dt_ini = status_pt, df.iloc[i]['date']

    return df, pd.DataFrame(eventos_aspectos), pd.DataFrame(mov_anuais), planetas_cfg

df, df_aspectos, df_mov_anual, planetas_cfg = get_astrological_data(ano, grau_decimal, planeta_selecionado, signo_selecionado, incluir_lua, mes_selecionado)

# --- GRÁFICO ---
fig = go.Figure()
for p in planetas_cfg:
    fig.add_trace(go.Scatter(x=df['date'], y=df[p['nome']], name=p['nome'], mode='lines', line=dict(color=p['cor'], width=2.5),
                             fill='tozeroy', fillcolor=hex_to_rgba(p['cor'], 0.15), customdata=df[f"{p['nome']}_info"],
                             hovertemplate="<b>%{customdata}</b><extra></extra>", connectgaps=False))
    
    serie = df[p['nome']].fillna(0)
    picos = df[(serie > 0.98) & (serie > serie.shift(1)) & (serie > serie.shift(-1))]
    if not picos.empty:
        fig.add_trace(go.Scatter(x=picos['date'], y=picos[p['nome']]+0.04, mode='markers+text', text=picos['date'].dt.strftime('%d/%m'),
                                 textposition="top center", marker=dict(symbol="triangle-down", color=p['cor'], size=8), showlegend=False, hoverinfo='skip'))

fig.update_layout(height=600, xaxis=dict(rangeslider=dict(visible=True, thickness=0.08), type='date', tickformat='%d/%m\n%Y'),
                  yaxis=dict(title='Intensidade', range=[0, 1.3], fixedrange=True), template='plotly_white', hovermode='x unified')
st.plotly_chart(fig, use_container_width=True)

# --- TABELAS CENTRALIZADAS ---
st.markdown("<h3 style='text-align: center;'>📅 Tabela de Trânsitos e Aspectos (Ponto Natal)</h3>", unsafe_allow_html=True)
col_a1, col_a2, col_a3 = st.columns([0.05, 0.9, 0.05])
with col_a2:
    st.dataframe(df_aspectos, use_container_width=True, height='content', hide_index=True)

st.markdown(f"<h3 style='text-align: center;'>🔄 Movimento Anual dos Planetas em {ano}</h3>", unsafe_allow_html=True)
col_m1, col_m2, col_m3 = st.columns([1, 2, 1])
with col_m2:
    st.dataframe(df_mov_anual, use_container_width=True, height='content', hide_index=True)

# --- DOWNLOADS ---
st.divider()
c1, c2, c3 = st.columns(3)
grau_limpo = str(grau_input).replace('.', '_')
with c1:
    buf = io.StringIO()
    fig.write_html(buf)
    st.download_button("📥 Gráfico (HTML)", buf.getvalue(), f"revolucao_{ano}.html", "text/html")
with c2:
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as w: df_aspectos.to_excel(w, index=False)
    st.download_button("📂 Tabela Aspectos (Excel)", out.getvalue(), f"aspectos_{ano}.xlsx")
with c3:
    out_m = io.BytesIO()
    with pd.ExcelWriter(out_m, engine='openpyxl') as w: df_mov_anual.to_excel(w, index=False)
    st.download_button("🔄 Movimento Anual (Excel)", out_m.getvalue(), f"movimento_{ano}.xlsx")