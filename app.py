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
pd.set_option('future.no_silent_downcasting', True)

# --- CONSTANTES E FUNÇÕES AUXILIARES ---
SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

LISTA_PLANETAS_UI = ["Sol", "Lua", "Mercúrio", "Vênus", "Marte", "Júpiter", "Saturno", "Urano", "Netuno", "Plutão"]

ASPECTOS = {
    0: "Conjunção", 30: "Semi-sêxtil", 60: "Sêxtil", 90: "Quadratura", 
    120: "Trígono", 150: "Quincúncio", 180: "Oposição"
}

def get_signo(longitude):
    return SIGNOS[int(longitude / 30) % 12]

def dms_to_dec(dms_str):
    if isinstance(dms_str, (int, float)): return float(dms_str)
    try:
        parts = str(dms_str).split('.')
        return float(parts[0]) + (float(parts[1])/60 if len(parts) > 1 else 0)
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
        if abs(diff - angulo) <= 5: return nome
    return "Outro"

# --- SIDEBAR ---
st.sidebar.header("Configurações")
ano = st.sidebar.number_input("Ano da Análise", min_value=1900, max_value=2100, value=2026)
grau_input = st.sidebar.text_input("Grau Natal (0 a 30°)", value="27.0")
planeta_selecionado = st.sidebar.selectbox("Planeta", options=["Escolha um planeta"] + LISTA_PLANETAS_UI, index=1) # Default Sol
signo_selecionado = st.sidebar.selectbox("Signo do Zodíaco", options=["Escolha um signo"] + SIGNOS, index=10) # Default Capricórnio

grau_decimal = dms_to_dec(grau_input)
incluir_lua = st.sidebar.checkbox("Quero analisar a Lua", value=False)
mes_selecionado = st.sidebar.slider("Mês da Lua", 1, 12, 1) if incluir_lua else None

if grau_decimal is None:
    st.error("Grau inválido."); st.stop()

# --- CACHE DE MOVIMENTOS ANUAIS (INDICAÇÃO D/R) ---
@st.cache_data
def get_annual_movements(ano_ref):
    planetas_cfg = [{"id": i, "nome": n} for i, n in zip([swe.SUN, swe.MERCURY, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO], ["SOL", "MERCÚRIO", "VÊNUS", "MARTE", "JÚPITER", "SATURNO", "URANO", "NETUNO", "PLUTÃO"])]
    jd_start = swe.julday(ano_ref, 1, 1)
    jd_end = swe.julday(ano_ref + 1, 1, 1)
    steps = np.arange(jd_start, jd_end, 0.5)
    movs = []
    for p in planetas_cfg:
        status_atual = None
        data_inicio = None
        for jd in steps:
            res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH | swe.FLG_SPEED)
            status_ponto = "Retrógrado" if res[3] < 0 else "Direto"
            y, m, d, _ = swe.revjul(jd)
            dt = datetime(y, m, d)
            if status_atual is None:
                status_atual = status_ponto; data_inicio = dt
            elif status_ponto != status_atual:
                movs.append({"Planeta": p["nome"].capitalize(), "Início": data_inicio.strftime('%d/%m/%Y'), "Término": dt.strftime('%d/%m/%Y'), "Trânsito": status_atual})
                status_atual = status_ponto; data_inicio = dt
        movs.append({"Planeta": p["nome"].capitalize(), "Início": data_inicio.strftime('%d/%m/%Y'), "Término": f"31/12/{ano_ref}", "Trânsito": status_atual})
    return pd.DataFrame(movs)

# --- CACHE DE DADOS DO GRÁFICO E ASPECTOS ---
@st.cache_data
def get_planetary_data(ano_ref, grau_ref_val, analisar_lua, mes_unico):
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
    jd_end = swe.julday(ano_ref + (1 if not mes_unico else 0), (mes_unico+1 if mes_unico and mes_unico<12 else 1) if mes_unico else 1, 1)
    steps = np.arange(jd_start, jd_end, 0.005 if analisar_lua and mes_unico else 0.05)
    
    data = []
    for jd in steps:
        y, m, d, h = swe.revjul(jd)
        dt = datetime(y, m, d, int(h), int((h%1)*60))
        row = {'date': dt}
        for p in planetas_cfg:
            res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH | swe.FLG_SPEED)
            pos = res[0] % 30
            dist = abs(((pos - grau_ref_val + 15) % 30) - 15)
            intensidade = "Forte" if dist <= 1.0 else "Médio" if dist <= 2.5 else "Fraco"
            row[p["nome"]] = np.exp(-0.5 * (dist / 1.7)**2) if dist <= 5.0 else 0
            row[f"{p['nome']}_long"] = res[0]
            row[f"{p['nome']}_status"] = "Retrógrado" if res[3] < 0 else "Direto"
            row[f"{p['nome']}_info"] = f"{get_signo(res[0])} {'(R)' if res[3]<0 else '(D)'} {int(pos):02d}°{int((pos%1)*60):02d}' - {intensidade}"
        data.append(row)
    return pd.DataFrame(data).infer_objects(copy=False), planetas_cfg

# --- PROCESSAMENTO ---
df_mov_anual = get_annual_movements(ano)
df, lista_planetas = get_planetary_data(ano, grau_decimal, incluir_lua, mes_selecionado)
grau_limpo_file = str(grau_input).replace('.', '_')

# --- GRÁFICO ---
fig = go.Figure()
for p in lista_planetas:
    df_p = df.copy()
    df_p.loc[df_p[p['nome']] == 0, p['nome']] = None
    fig.add_trace(go.Scatter(x=df_p['date'], y=df_p[p['nome']], name=p['nome'], mode='lines', line=dict(color=p['cor'], width=2.5),
                             fill='tozeroy', fillcolor=hex_to_rgba(p['cor'], 0.15), customdata=df[f"{p['nome']}_info"],
                             hovertemplate="<b>%{customdata}</b><extra></extra>", connectgaps=False))
    
    serie = df[p['nome']].fillna(0)
    picos = df[(serie > 0.98) & (serie > serie.shift(1)) & (serie > serie.shift(-1))]
    if not picos.empty:
        fig.add_trace(go.Scatter(x=picos['date'], y=picos[p['nome']]+0.04, mode='markers+text', text=picos['date'].dt.strftime('%d/%m'),
                                 textposition="top center", marker=dict(symbol="triangle-down", color=p['cor'], size=8), 
                                 showlegend=False, hoverinfo='skip', hovertemplate=""))

fig.update_layout(title=dict(text=f'Revolução Planetária {ano}: Grau {grau_input}', x=0.5), height=700,
                  xaxis=dict(rangeslider=dict(visible=True, thickness=0.08), type='date', tickformat='%d/%m\n%Y', hoverformat='%d/%m/%Y %H:%M'),
                  yaxis=dict(title='Intensidade', range=[0, 1.3], fixedrange=True), template='plotly_white', hovermode='x unified', dragmode='pan')

st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

# --- TABELAS ---
st.write("### 📅 Tabela de Trânsitos e Aspectos")
eventos_aspectos = []
if planeta_selecionado != "Escolha um planeta" and signo_selecionado != "Escolha um signo":
    long_natal_abs = (SIGNOS.index(signo_selecionado) * 30) + grau_decimal
    for p in lista_planetas:
        serie = df[p["nome"]].values
        for i in range(1, len(serie)-1):
            if serie[i] > 0.98 and serie[i] > serie[i-1] and serie[i] > serie[i+1]:
                idx_ini, idx_fim = i, i
                while idx_ini > 0 and serie[idx_ini] > 0.01: idx_ini -= 1
                while idx_fim < len(serie)-1 and serie[idx_fim] > 0.01: idx_fim += 1
                row_pico = df.iloc[i]
                eventos_aspectos.append({
                    "Data e Hora Início": df.iloc[idx_ini]['date'].strftime('%d/%m/%Y %H:%M'),
                    "Data e Hora Pico": row_pico['date'].strftime('%d/%m/%Y %H:%M'),
                    "Data e Hora Término": df.iloc[idx_fim]['date'].strftime('%d/%m/%Y %H:%M'),
                    "Grau Natal": f"{grau_input}°",
                    "Planeta e Signo Natal": f"{planeta_selecionado} em {signo_selecionado}",
                    "Planeta e Signo em Trânsito": f"{p['nome'].capitalize()} em {get_signo(row_pico[p['nome']+'_long'])}",
                    "Trânsito": row_pico[p['nome']+'_status'],
                    "Aspecto": calcular_aspecto(row_pico[p['nome']+'_long'], long_natal_abs)
                })

df_asp = pd.DataFrame(eventos_aspectos)
st.dataframe(df_asp, use_container_width=True)

st.write(f"### 🔄 Movimento Anual dos Planetas em {ano}")
st.dataframe(df_mov_anual, use_container_width=True)

# --- DOWNLOADS COM FORMATAÇÃO DO SCRIPT ORIGINAL ---
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    buf_html = io.StringIO()
    fig.write_html(buf_html, config={'scrollZoom': True})
    st.download_button("📥 Baixar Gráfico (HTML)", buf_html.getvalue(), f"revolucao_{ano}_grau_{grau_limpo_file}.html", "text/html")

with col2:
    if not df_asp.empty:
        buf_asp = io.BytesIO()
        with pd.ExcelWriter(buf_asp, engine='openpyxl') as w: df_asp.to_excel(w, index=False)
        st.download_button("📂 Baixar Tabela Aspectos (Excel)", buf_asp.getvalue(), f"tabela_transitos_{ano}_grau_{grau_limpo_file}.xlsx")

with col3:
    buf_mov = io.BytesIO()
    with pd.ExcelWriter(buf_mov, engine='openpyxl') as w: df_mov_anual.to_excel(w, index=False)
    st.download_button("🔄 Baixar Movimento Anual (Excel)", buf_mov.getvalue(), f"movimento_planetas_{ano}.xlsx")