import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import io
import re

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Revolução Planetária", layout="wide")

# Silencia avisos de downcasting
pd.set_option('future.no_silent_downcasting', True)

# --- CONSTANTES E FUNÇÕES AUXILIARES ---
SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

LISTA_PLANETAS_UI = ["Sol", "Lua", "Mercúrio", "Vênus", "Marte", "Júpiter", "Saturno", "Urano", "Netuno", "Plutão"]

ASPECTOS = {
    0: ("Conjunção", "☌"), 
    30: ("Semi-sêxtil", "⚺"), 
    60: ("Sêxtil", "✶"), 
    90: ("Quadratura", "□"), 
    120: ("Trígono", "△"), 
    150: ("Quincúncio", "⚻"), 
    180: ("Oposição", "☍")
}

def get_signo(longitude):
    return SIGNOS[int(longitude / 30) % 12]

def dms_to_dec(dms_str):
    if isinstance(dms_str, (int, float)): return float(dms_str)
    try:
        if not re.match(r"^\d+(\.\d+)?$", str(dms_str)): return None
        parts = str(dms_str).split('.')
        degrees = float(parts[0])
        if len(parts) > 1:
            minutos_raw = parts[1]
            minutos = float(minutos_raw)
            if minutos >= 60: return "ERRO_MINUTOS"
        else:
            minutos = 0
        val = degrees + (minutos / 60)
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
    for angulo, (nome, simbolo) in ASPECTOS.items():
        if abs(diff - angulo) <= 5:
            return nome
    return "Outro"

def obter_simbolo_aspecto(long1, long2):
    diff = abs(long1 - long2) % 360
    if diff > 180: diff = 360 - diff
    for angulo, (nome, simbolo) in ASPECTOS.items():
        if abs(diff - angulo) <= 5:
            return simbolo
    return ""

# --- INTERFACE LATERAL ---
st.sidebar.header("Configurações")
ano = st.sidebar.number_input("Ano da Análise", min_value=1900, max_value=2100, value=2026)
grau_input = st.sidebar.text_input("Grau Natal (0 a 30°)", value="27.0")

planeta_selecionado = st.sidebar.selectbox("Planeta", options=["Escolha um planeta"] + LISTA_PLANETAS_UI, index=0)
signo_selecionado = st.sidebar.selectbox("Signo do Zodíaco", options=["Escolha um signo"] + SIGNOS, index=0)

grau_decimal = dms_to_dec(grau_input)
incluir_lua = st.sidebar.checkbox("Quero analisar a Lua", value=False)
mes_selecionado = st.sidebar.slider("Mês da Lua", 1, 12, 1) if incluir_lua else None

if grau_decimal == "ERRO_MINUTOS":
    st.error("⚠️ Erro nos minutos.")
    st.stop()
elif grau_decimal is None:
    st.error("⚠️ Erro no valor.")
    st.stop()

long_natal_absoluta_calc = 0
if planeta_selecionado != "Escolha um planeta" and signo_selecionado != "Escolha um signo":
    idx_s = SIGNOS.index(signo_selecionado)
    long_natal_absoluta_calc = (idx_s * 30) + grau_decimal

st.markdown(f"<h1>🔭 Revolução Planetária {ano}</h1>", unsafe_allow_html=True)

# --- PROCESSAMENTO ---
@st.cache_data
def get_annual_movements(ano_ref):
    planetas_cfg = [{"id": i, "nome": n} for i, n in zip([swe.SUN, swe.MERCURY, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO], ["SOL", "MERCÚRIO", "VÊNUS", "MARTE", "JÚPITER", "SATURNO", "URANO", "NETUNO", "PLUTÃO"])]
    jd_start, jd_end = swe.julday(ano_ref, 1, 1), swe.julday(ano_ref + 1, 1, 1)
    steps = np.arange(jd_start, jd_end, 0.5)
    movs = []
    for p in planetas_cfg:
        status_atual, data_inicio = None, None
        for jd in steps:
            res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH | swe.FLG_SPEED)
            status_ponto = "Retrógrado" if res[3] < 0 else "Direto"
            if status_atual is None:
                status_atual, data_inicio = status_ponto, datetime(*swe.revjul(jd)[:3])
            elif status_ponto != status_atual:
                movs.append({"Planeta": p["nome"].capitalize(), "Início": data_inicio.strftime('%d/%m/%Y'), "Término": datetime(*swe.revjul(jd)[:3]).strftime('%d/%m/%Y'), "Trânsito": status_atual})
                status_atual, data_inicio = status_ponto, datetime(*swe.revjul(jd)[:3])
        movs.append({"Planeta": p["nome"].capitalize(), "Início": data_inicio.strftime('%d/%m/%Y'), "Término": f"31/12/{ano_ref}", "Trânsito": status_atual})
    return pd.DataFrame(movs)

@st.cache_data
def get_planetary_data(ano_ref, grau_ref_val, analisar_lua, mes_unico, long_natal_ref):
    planetas_cfg = [{"id": swe.SUN, "nome": "SOL", "cor": "#FFF12E"}, {"id": swe.MERCURY, "nome": "MERCÚRIO", "cor": "#F3A384"}, {"id": swe.VENUS, "nome": "VÊNUS", "cor": "#0A8F11"}, {"id": swe.MARS, "nome": "MARTE", "cor": "#F10808"}, {"id": swe.JUPITER, "nome": "JÚPITER", "cor": "#1746C9"}, {"id": swe.SATURN, "nome": "SATURNO", "cor": "#381094"}, {"id": swe.URANUS, "nome": "URANO", "cor": "#FF00FF"}, {"id": swe.NEPTUNE, "nome": "NETUNO", "cor": "#1EFF00"}, {"id": swe.PLUTO, "nome": "PLUTÃO", "cor": "#14F1F1"}]
    if analisar_lua: planetas_cfg.insert(1, {"id": swe.MOON, "nome": "LUA", "cor": "#A6A6A6"})
    jd_start = swe.julday(ano_ref, mes_unico or 1, 1)
    jd_end = swe.julday(ano_ref + (1 if not mes_unico else 0), (mes_unico + 1 if mes_unico and mes_unico < 12 else 1) if mes_unico else 1, 1)
    steps = np.arange(jd_start, jd_end, 0.005 if analisar_lua and mes_unico else 0.05)
    all_data = []
    for jd in steps:
        y, m, d, h = swe.revjul(jd)
        row = {'date': datetime(y, m, d, int(h), int((h%1)*60))}
        for p in planetas_cfg:
            res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH | swe.FLG_SPEED)
            pos, dist = res[0] % 30, abs(((res[0] % 30 - grau_ref_val + 15) % 30) - 15)
            simbolo = obter_simbolo_aspecto(res[0], long_natal_ref) if long_natal_ref > 0 else ""
            row[p["nome"]] = np.exp(-0.5 * (dist / 1.7)**2) if dist <= 5.0 else 0
            row[f"{p['nome']}_long"], row[f"{p['nome']}_status"] = res[0], ("Retrógrado" if res[3] < 0 else "Direto")
            row[f"{p['nome']}_info"] = f"{get_signo(res[0])} {'(R)' if res[3]<0 else '(D)'} {int(pos):02d}°{int((pos%1)*60):02d}' - {'Forte' if dist <= 1.0 else 'Médio' if dist <= 2.5 else 'Fraco'} {simbolo}"
        all_data.append(row)
    return pd.DataFrame(all_data).infer_objects(copy=False), planetas_cfg

df_mov_anual = get_annual_movements(ano)
df, lista_planetas = get_planetary_data(ano, grau_decimal, incluir_lua, mes_selecionado, long_natal_absoluta_calc)
grau_limpo_file = str(grau_input).replace('.', '_')

# --- GRÁFICO ---
fig = go.Figure()
for p in lista_planetas:
    df_p = df.copy()
    df_p.loc[df_p[p['nome']] == 0, p['nome']] = None
    fig.add_trace(go.Scatter(x=df_p['date'], y=df_p[p['nome']], name=p['nome'], mode='lines', line=dict(color=p['cor'], width=2.5), fill='tozeroy', fillcolor=hex_to_rgba(p['cor'], 0.15), customdata=df[f"{p['nome']}_info"], hovertemplate="<b>%{customdata}</b><extra></extra>", connectgaps=False))
st.plotly_chart(fig, use_container_width=True)

# --- TABELAS (HTML PARA REMOVER ÍNDICE E SCROLL TOTALMENTE) ---
eventos_aspectos = []
if planeta_selecionado != "Escolha um planeta" and signo_selecionado != "Escolha um signo":
    idx_signo_natal = SIGNOS.index(signo_selecionado)
    long_natal_absoluta = (idx_signo_natal * 30) + grau_decimal
    for p in lista_planetas:
        serie = df[p["nome"]].fillna(0).values
        for i in range(1, len(serie) - 1):
            if serie[i] > 0.98 and serie[i] > serie[i-1] and serie[i] > serie[i+1]:
                idx_ini, idx_fim = i, i
                while idx_ini > 0 and serie[idx_ini] > 0.01: idx_ini -= 1
                while idx_fim < len(serie) - 1 and serie[idx_fim] > 0.01: idx_fim += 1
                row_pico = df.iloc[i]
                eventos_aspectos.append({
                    "Início": df.iloc[idx_ini]['date'].strftime('%d/%m/%Y %H:%M'),
                    "Pico": row_pico['date'].strftime('%d/%m/%Y %H:%M'),
                    "Término": df.iloc[idx_fim]['date'].strftime('%d/%m/%Y %H:%M'),
                    "Ponto Natal": f"{planeta_selecionado} ({grau_input}°) em {signo_selecionado}",
                    "Trânsito": f"{p['nome'].capitalize()} em {get_signo(row_pico[f'{p[ 'nome']}_long'])}",
                    "Aspecto": calcular_aspecto(row_pico[f"{p['nome']}_long"], long_natal_absoluta)
                })

# Função para renderizar tabela sem índice
def render_static_table(dataframe):
    html = dataframe.to_html(index=False, classes='styled-table', escape=False)
    st.markdown(f"""
        <style>
            .styled-table {{ border-collapse: collapse; margin: 25px 0; font-size: 0.9em; font-family: sans-serif; min-width: 100%; box-shadow: 0 0 20px rgba(0, 0, 0, 0.05); }}
            .styled-table thead tr {{ background-color: #f8f9fa; text-align: left; }}
            .styled-table th, .styled-table td {{ padding: 12px 15px; border-bottom: 1px solid #dddddd; }}
        </style>
        {html}
    """, unsafe_allow_html=True)

st.markdown("<h3 style='text-align: center;'>📅 Trânsitos e Aspectos</h3>", unsafe_allow_html=True)
if eventos_aspectos:
    render_static_table(pd.DataFrame(eventos_aspectos))

st.markdown(f"<h3 style='text-align: center;'>🔄 Movimento Anual {ano}</h3>", unsafe_allow_html=True)
render_static_table(df_mov_anual)

# --- DOWNLOADS ---
st.divider()
c1, c2, c3 = st.columns(3)
with c1:
    buf = io.StringIO()
    fig.write_html(buf)
    st.download_button("📥 Baixar Gráfico (HTML)", buf.getvalue(), f"revolucao_{ano}.html", "text/html")
with c2:
    if eventos_aspectos:
        out = io.BytesIO()
        with pd.ExcelWriter(out) as w: pd.DataFrame(eventos_aspectos).to_excel(w, index=False)
        st.download_button("📂 Baixar Tabela Aspectos (Excel)", out.getvalue(), "aspectos.xlsx")
with c3:
    out_m = io.BytesIO()
    with pd.ExcelWriter(out_m) as w: df_mov_anual.to_excel(w, index=False)
    st.download_button("🔄 Baixar Movimento Anual (Excel)", out_m.getvalue(), "movimento.xlsx")