import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
from datetime import date
import io
import re
import urllib.parse
import base64
import math
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Revolução Planetária", layout="wide")
st.markdown("""
    <style>
        /* Aumenta as fontes dos campos de IA */
        .stDateInput label p, .stTextInput label p {
            font-size: 1.1rem !important;
            font-weight: bold !important;
        }
        .stDateInput div div input, .stTextInput div div input {
            font-size: 1.1rem !important;
            height: 45px !important;
        }
        /* Remove o link de corrente/âncora dos títulos */
        button[data-testid="stHeaderActionElements"], 
        .aria-hidden, 
        [data-testid="stMarkdown"] svg {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)

# Silencia avisos de downcasting
pd.set_option('future.no_silent_downcasting', True)

# --- CONSTANTES E FUNÇÕES AUXILIARES ---
SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

LISTA_PLANETAS_UI = ["Sol", "Lua", "Mercúrio", "Vênus", "Marte", "Júpiter", "Saturno", "Urano", "Netuno", "Plutão"]

# Dicionário atualizado para incluir os símbolos
ASPECTOS = {
    0: ("Conjunção", "☌"), 
    30: ("Semi-sêxtil", "⚺"), 
    60: ("Sêxtil", "✶"), 
    90: ("Quadratura", "□"), 
    120: ("Trígono", "△"), 
    150: ("Quincúncio", "⚻"), 
    180: ("Oposição", "☍")
}

SIMBOLOS_PLANETAS = {
    "SOL": "☉", "LUA": "☽", "MERCÚRIO": "☿", "VÊNUS": "♀",
    "MARTE": "♂", "JÚPITER": "♃", "SATURNO": "♄", 
    "URANO": "♅", "NETUNO": "♆", "PLUTÃO": "♇"
}

def converter_svg_para_base64(caminho_arquivo):
    """Converte um arquivo SVG local em uma string Base64 para exibição universal."""
    if not os.path.exists(caminho_arquivo):
        return None
    with open(caminho_arquivo, "rb") as f:
        svg_bytes = f.read()
        encoded = base64.b64encode(svg_bytes).decode('utf-8')
        return f"data:image/svg+xml;base64,{encoded}"

def criar_mandala_astrologica(ano, mes, dia, hora_decimal, pasta_icones):
    # --- 1. CONFIGURAÇÕES E CÁLCULOS INICIAIS ---
    jd = swe.julday(ano, mes, dia, hora_decimal)
    
    NOMES_SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
                    "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]
    
    ARQUIVOS_SVG = ["aries.svg", "touro.svg", "gemeos.svg", "cancer.svg", 
                    "leao.svg", "virgem.svg", "libra.svg", "escorpiao.svg", 
                    "sagitario.svg", "capricornio.svg", "aquario.svg", "peixes.svg"]

    planetas_cfg = [
        {"id": swe.SUN, "nome": "Sol", "cor": "#FFD700", "sym": "☉"},
        {"id": swe.MOON, "nome": "Lua", "cor": "#C0C0C0", "sym": "☽"},
        {"id": swe.MERCURY, "nome": "Mercúrio", "cor": "#F3A384", "sym": "☿"},
        {"id": swe.VENUS, "nome": "Vênus", "cor": "#0A8F11", "sym": "♀"},
        {"id": swe.MARS, "nome": "Marte", "cor": "#F10808", "sym": "♂"},
        {"id": swe.JUPITER, "nome": "Júpiter", "cor": "#1746C9", "sym": "♃"},
        {"id": swe.SATURN, "nome": "Saturno", "cor": "#381094", "sym": "♄"},
        {"id": swe.URANUS, "nome": "Urano", "cor": "#FF00FF", "sym": "♅"},
        {"id": swe.NEPTUNE, "nome": "Netuno", "cor": "#1EFF00", "sym": "♆"},
        {"id": swe.PLUTO, "nome": "Plutão", "cor": "#14F1F1", "sym": "♇"}
    ]

    fig = go.Figure()
    raio_interno = 4.0
    
    # --- 2. POSIÇÕES E LÓGICA ANTI-SOBREPOSIÇÃO ---
    posicoes = []
    for p in planetas_cfg:
        res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH)
        long_abs = res[0]
        id_signo = int(long_abs / 30)
        grau_no_signo = long_abs % 30
        min_f, gr_i = math.modf(grau_no_signo)
        min_i = int(round(min_f * 60))
        if min_i == 60: min_i = 0; gr_i += 1
        
        posicoes.append({
            "nome": p["nome"], "long": long_abs, "cor": p["cor"], 
            "sym": p["sym"], "grau_int": int(gr_i), "min_int": min_i,
            "signo": NOMES_SIGNOS[id_signo % 12], "long_visual": long_abs 
        })

    posicoes.sort(key=lambda x: x['long'])
    dist_min = 7.0 
    for _ in range(5): 
        for i in range(len(posicoes)):
            for j in range(i + 1, len(posicoes)):
                d = (posicoes[j]['long_visual'] - posicoes[i]['long_visual']) % 360
                if d < dist_min:
                    posicoes[j]['long_visual'] = (posicoes[i]['long_visual'] + dist_min) % 360

    # --- 3. CÍRCULO INTERIOR (CENTRAL) ---
    fig.add_trace(go.Scatterpolar(r=[raio_interno] * 361, theta=list(range(361)), fill='toself', 
        fillcolor="rgba(245, 245, 245, 0.2)", line=dict(color="black", width=1.5), showlegend=False, hoverinfo='skip'))

    # --- 4. LINHAS DE ASPECTO COM SÍMBOLOS ---
    CORES_ASPECTOS = {"☌": "green", "☍": "red", "□": "red", "△": "blue", "✶": "blue", "⚼": "orange", "∠": "orange"}
    for i in range(len(posicoes)):
        for j in range(i + 1, len(posicoes)):
            p1, p2 = posicoes[i], posicoes[j]
            simbolo_asp = obter_simbolo_aspecto(p1['long'], p2['long'])
            
            if simbolo_asp:
                cor_asp = CORES_ASPECTOS.get(simbolo_asp, "gray")
                fig.add_trace(go.Scatterpolar(r=[raio_interno, raio_interno], theta=[p1['long'], p2['long']],
                    mode='lines', line=dict(color=cor_asp, width=1.3), opacity=0.3, showlegend=False, hoverinfo='skip'))
                
                a1, a2 = np.radians(p1['long']), np.radians(p2['long'])
                x = (np.cos(a1) + np.cos(a2)) / 2
                y = (np.sin(a1) + np.sin(a2)) / 2
                mid_theta = np.degrees(np.arctan2(y, x))
                dist_ang = abs(p1['long'] - p2['long'])
                if dist_ang > 180: dist_ang = 360 - dist_ang
                mid_r = raio_interno * np.cos(np.radians(dist_ang / 2))
                
                fig.add_trace(go.Scatterpolar(
                    r=[mid_r], theta=[mid_theta],
                    mode='text', text=[simbolo_asp],
                    textfont=dict(size=16, color=cor_asp, family="Arial Black"),
                    showlegend=False, hoverinfo='skip'
                ))

    # --- 5. SIGNOS E RÉGUA ---
    for i, nome_arq in enumerate(ARQUIVOS_SVG):
        centro_polar = i * 30 + 15
        fig.add_trace(go.Barpolar(r=[2], theta=[centro_polar], width=[30], base=8, 
                                  marker_color="white", marker_line_color="black", marker_line_width=1, showlegend=False, hoverinfo='skip'))
        
        img_data = converter_svg_para_base64(os.path.join(pasta_icones, nome_arq))
        if img_data:
            rad = np.radians(180 + centro_polar)
            raio_pos = 0.46
            fig.add_layout_image(dict(
                source=img_data, xref="paper", yref="paper",
                x=0.5 + (raio_pos * np.cos(rad)), y=0.5 + (raio_pos * np.sin(rad)),
                sizex=0.05, sizey=0.05, xanchor="center", yanchor="middle", layer="above"
            ))
        for g in range(30):
            raio_p = 8.6 if g % 10 == 0 else 8.3
            fig.add_trace(go.Scatterpolar(r=[8.0, raio_p], theta=[i*30+g, i*30+g], mode='lines', 
                                          line=dict(color="black", width=1), showlegend=False, hoverinfo='skip'))

    fig.add_trace(go.Scatterpolar(r=[10] * 361, theta=list(range(361)), mode='lines', 
                                  line=dict(color="black", width=2), showlegend=False, hoverinfo='skip'))

    # --- 6. PLANETAS E TEXTOS (CORREÇÃO DE TRAÇADO AQUI) ---
    for p in posicoes:
        hover_template = f"{p['nome']}<br>{p['signo']}<br>{p['grau_int']}º{p['min_int']}'<extra></extra>"
        
        fig.add_trace(go.Scatterpolar(r=[6.2], theta=[p["long_visual"]], mode='text', text=[f"{p['grau_int']}°"], 
                                      textfont=dict(size=30, color="black", family="Trebuchet MS"), 
                                      showlegend=False, hovertemplate=hover_template))
        fig.add_trace(go.Scatterpolar(r=[5.3], theta=[p["long_visual"]], mode='text', text=[f"{p['min_int']}'"], 
                                      textfont=dict(size=26, color="black", family="Trebuchet MS"), 
                                      showlegend=False, hovertemplate=hover_template))
        fig.add_trace(go.Scatterpolar(r=[raio_interno], theta=[p["long"]], mode='markers', 
                                      marker=dict(size=8, color=p["cor"], line=dict(color='black', width=0)), 
                                      showlegend=False, hovertemplate=hover_template))
        
        # AJUSTE: Símbolos dos planetas com família de fonte mais pesada para uniformizar Marte e Vênus
        fig.add_trace(go.Scatterpolar(
            r=[7.3], theta=[p["long_visual"]], 
            mode='text', 
            text=[f"<b>{p['sym']}</b>"], # Adicionado Negrito via tag HTML
            textfont=dict(size=45, color=p["cor"], family="Arial Black"), 
            showlegend=False, hovertemplate=hover_template
        ))
        
        fig.add_trace(go.Scatterpolar(r=[8.0], theta=[p["long"]], mode='markers', 
                                      marker=dict(size=10, color=p["cor"], line=dict(color='black', width=0)), 
                                      showlegend=False, hovertemplate=hover_template))

    # --- 7. LAYOUT FINAL ---
    fig.update_layout(
        width=900, height=900,
        polar=dict(
            radialaxis=dict(visible=False, range=[0, 10]),
            angularaxis=dict(direction="counterclockwise", rotation=180, showgrid=False, showticklabels=False)
        ),
        hoverlabel=dict(bgcolor="white", font_size=14, font_family="Arial"),
        showlegend=False, margin=dict(t=50, b=50, l=50, r=50), dragmode=False
    )
    return fig

def get_signo(longitude):
    return SIGNOS[int(longitude / 30) % 12]

def dms_to_dec(dms_str):
    if isinstance(dms_str, (int, float)): return float(dms_str)
    try:
        if not re.match(r"^\d+(\.\d+)?$", str(dms_str)): return None
        parts = str(dms_str).split('.')
        degrees = float(parts[0])
        
        # Validação de minutos (parte decimal)
        if len(parts) > 1:
            minutos_raw = parts[1]
            minutos = float(minutos_raw)
            
            # REGRA: Minutos não podem ser 60 ou mais
            if minutos >= 60:
                return "ERRO_MINUTOS"
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
grau_input = st.sidebar.text_input("Grau Natal (0 a 30°)", value="27.0", help="Exemplo: 27.59 (27 graus e 59 minutos)")

planeta_selecionado = st.sidebar.selectbox("Planeta", options=["Escolha um planeta"] + LISTA_PLANETAS_UI, index=1)
signo_selecionado = st.sidebar.selectbox("Signo do Zodíaco", options=["Escolha um signo"] + SIGNOS, index=6)

grau_decimal = dms_to_dec(grau_input)
incluir_lua = st.sidebar.checkbox("Quero analisar a Lua", value=False)
mes_selecionado = st.sidebar.slider("Mês da Lua", 1, 12, 1) if incluir_lua else None

# Verificação da Regra de Minutos < 60
if grau_decimal == "ERRO_MINUTOS":
    st.error("⚠️ Erro: Os minutos (parte decimal) não podem ser iguais ou maiores que 60. Use de .00 a .59.")
    st.stop()
elif grau_decimal is None:
    st.error("⚠️ Erro: Insira um valor numérico válido entre 0 e 30.")
    st.stop()

# Cálculo da longitude natal absoluta para uso na função de símbolos
long_natal_absoluta_calc = 0
if planeta_selecionado != "Escolha um planeta" and signo_selecionado != "Escolha um signo":
    idx_s = SIGNOS.index(signo_selecionado)
    long_natal_absoluta_calc = (idx_s * 30) + grau_decimal

p_texto = planeta_selecionado if planeta_selecionado != "Escolha um planeta" else "Planeta"
s_texto = signo_selecionado if signo_selecionado != "Escolha um signo" else "Signo"

st.markdown(f"""
    <div style='text-align: left;'>
        <h1 style='font-size: 2.5rem; margin-bottom: 0;'>🔭 Revolução Planetária {ano}</h1>
    </div>
""", unsafe_allow_html=True)

# --- PROCESSAMENTO ---
@st.cache_data
def get_annual_movements(ano_ref):
    planetas_cfg = [{"id": i, "nome": n} for i, n in zip([swe.SUN, swe.MERCURY, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO], ["SOL", "MERCÚRIO", "VÊNUS", "MARTE", "JÚPITER", "SATURNO", "URANO", "NETUNO", "PLUTÃO"])]
    jd_start = swe.julday(ano_ref, 1, 1)
    jd_end = swe.julday(ano_ref + 1, 1, 1)
    steps = np.arange(jd_start, jd_end, 0.5)
    movs = []
    for p in planetas_cfg:
        status_atual, data_inicio = None, None
        for jd in steps:
            res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH | swe.FLG_SPEED)
            status_ponto = "Retrógrado" if res[3] < 0 else "Direto"
            if status_atual is None:
                status_atual = status_ponto
                y, m, d, _ = swe.revjul(jd)
                data_inicio = datetime(y, m, d)
            elif status_ponto != status_atual:
                y, m, d, _ = swe.revjul(jd)
                movs.append({"Planeta": p["nome"].capitalize(), "Início": data_inicio.strftime('%d/%m/%Y'), "Término": datetime(y, m, d).strftime('%d/%m/%Y'), "Trânsito": status_atual})
                status_atual, data_inicio = status_ponto, datetime(y, m, d)
        movs.append({"Planeta": p["nome"].capitalize(), "Início": data_inicio.strftime('%d/%m/%Y'), "Término": f"31/12/{ano_ref}", "Trânsito": status_atual})
    return pd.DataFrame(movs)

@st.cache_data
def get_planetary_data(ano_ref, grau_ref_val, analisar_lua, mes_unico, long_natal_ref):
    planetas_cfg = [
        {"id": swe.SUN, "nome": "SOL", "cor": "#FFF12E"}, {"id": swe.MERCURY, "nome": "MERCÚRIO", "cor": "#F3A384"},
        {"id": swe.VENUS, "nome": "VÊNUS", "cor": "#0A8F11"}, {"id": swe.MARS, "nome": "MARTE", "cor": "#F10808"},
        {"id": swe.JUPITER, "nome": "JÚPITER", "cor": "#1746C9"}, {"id": swe.SATURN, "nome": "SATURNO", "cor": "#381094"},
        {"id": swe.URANUS, "nome": "URANO", "cor": "#FF00FF"}, {"id": swe.NEPTUNE, "nome": "NETUNO", "cor": "#1EFF00"},
        {"id": swe.PLUTO, "nome": "PLUTÃO", "cor": "#14F1F1"}
    ]
    if analisar_lua: planetas_cfg.insert(1, {"id": swe.MOON, "nome": "LUA", "cor": "#A6A6A6"})
    jd_start = swe.julday(ano_ref, mes_unico if mes_unico else 1, 1)
    jd_end = swe.julday(ano_ref + (1 if not mes_unico else 0), (mes_unico + 1 if mes_unico and mes_unico < 12 else 1) if mes_unico else 1, 1)
    steps = np.arange(jd_start, jd_end, 0.005 if analisar_lua and mes_unico else 0.05)
    all_data = []
    for jd in steps:
        y, m, d, h = swe.revjul(jd)
        dt = datetime(y, m, d, int(h), int((h%1)*60))
        row = {'date': dt}
        for p in planetas_cfg:
            res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH | swe.FLG_SPEED)
            pos = res[0] % 30
            dist = abs(((pos - grau_ref_val + 15) % 30) - 15)
            
            simbolo = obter_simbolo_aspecto(res[0], long_natal_ref) if long_natal_ref > 0 else ""
            simbolo_html = f"<span style='font-size: 16px; line-height: 0; vertical-align: baseline;'><b>{simbolo}</b></span>" if simbolo else ""
            
            row[p["nome"]] = np.exp(-0.5 * (dist / 1.7)**2) if dist <= 5.0 else 0
            row[f"{p['nome']}_long"] = res[0]
            row[f"{p['nome']}_status"] = "Retrógrado" if res[3] < 0 else "Direto"
            row[f"{p['nome']}_info"] = f"{get_signo(res[0])} {'(R)' if res[3]<0 else '(D)'} {int(pos):02d}°{int((pos%1)*60):02d}' - {'Forte' if dist <= 1.0 else 'Médio' if dist <= 2.5 else 'Fraco'} {simbolo_html}"
        all_data.append(row)
    return pd.DataFrame(all_data).infer_objects(copy=False), planetas_cfg

df_mov_anual = get_annual_movements(ano)
df, lista_planetas = get_planetary_data(ano, grau_decimal, incluir_lua, mes_selecionado, long_natal_absoluta_calc)
grau_limpo_file = str(grau_input).replace('.', '_')

@st.fragment
def secao_previsao_ia(ano, planeta_selecionado, signo_selecionado, grau_input, long_natal_absoluta_calc):
        # --- SEÇÃO DE CONSULTA IA CENTRALIZADA (ABAIXO DO GRÁFICO) ---
    st.divider()
    col_esq, col_central, col_dir = st.columns([1, 1.5, 1])

    with col_central:
        st.markdown("<h2 style='text-align: center;'>🤖 Previsão Astrológica</h2>", unsafe_allow_html=True)
        
        sub_col1, sub_col2 = st.columns(2)
        
        with sub_col1:
            data_consulta = st.date_input(
                "Escolha a data", 
                value=date(ano, 1, 7),
                min_value=date(1900, 1, 1),
                max_value=date(2100, 12, 31),
                key="ia_data_key" 
            )
        
        with sub_col2:
            hora_input = st.text_input("Escolha a hora (HH:MM)", placeholder="12:00", key="ia_hora_key")
        
        btn_gerar = st.button("Preparar Análise para o Gemini", use_container_width=True)

    if btn_gerar:
        # --- VALIDAÇÃO DE SELEÇÃO ---
        if planeta_selecionado == "Escolha um planeta" or signo_selecionado == "Escolha um signo":
            st.error("⚠️ Erro: Selecione o Planeta e o Signo na barra lateral antes de gerar a previsão.")
        else:
            hora_valida = "12:00"
            if hora_input.strip():
                if re.match(r"^([0-9]|0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$", hora_input.strip()):
                    hora_valida = hora_input.strip()
                else:
                    st.warning("Formato de hora inválido. Usando 12:00 por padrão.")

            h_str, m_str = hora_valida.split(":")
            hora_decimal = int(h_str) + (int(m_str) / 60.0)
            
            jd_ia = swe.julday(data_consulta.year, data_consulta.month, data_consulta.day, hora_decimal)
            
            ativos_ia = []
            planetas_ia = [
                {"id": swe.SUN, "nome": "Sol"}, {"id": swe.MOON, "nome": "Lua"},
                {"id": swe.MERCURY, "nome": "Mercúrio"}, {"id": swe.VENUS, "nome": "Vênus"},
                {"id": swe.MARS, "nome": "Marte"}, {"id": swe.JUPITER, "nome": "Júpiter"},
                {"id": swe.SATURN, "nome": "Saturno"}, {"id": swe.URANUS, "nome": "Urano"},
                {"id": swe.NEPTUNE, "nome": "Netuno"}, {"id": swe.PLUTO, "nome": "Plutão"}
            ]

            for p in planetas_ia:
                res, _ = swe.calc_ut(jd_ia, p["id"], swe.FLG_SWIEPH | swe.FLG_SPEED)
                long_transito = res[0]
                pos_no_signo = long_transito % 30
                
                diff = abs(long_transito - long_natal_absoluta_calc) % 360
                if diff > 180: diff = 360 - diff
                
                aspecto_nome = "Nenhum"
                menor_orbe = 999
                
                for angulo, (nome, simbolo) in ASPECTOS.items():
                    orbe_atual = abs(diff - angulo)
                    if orbe_atual <= 5.0:
                        aspecto_nome = nome
                        menor_orbe = orbe_atual
                        break
                
                if aspecto_nome != "Nenhum":
                    status = "Retrógrado" if res[3] < 0 else "Direto"
                    forca = "Forte" if menor_orbe <= 1.0 else "Médio" if menor_orbe <= 2.5 else "Fraco"
                    ativos_ia.append(f"{p['nome']} em {get_signo(long_transito)} ({status}) {int(pos_no_signo):02d}°{int((pos_no_signo%1)*60):02d}' fazendo {aspecto_nome} - {forca}")

            with col_central:
                if ativos_ia:
                    data_hora_str = f"{data_consulta.strftime('%d/%m/%Y')} às {hora_valida}"
                    prompt_final = f"""Você é um astrólogo profissional. Interprete o momento: {data_hora_str}.
    Ponto Natal: {planeta_selecionado} a {grau_input}° de {signo_selecionado}.
    Trânsitos ativos para este ponto: {'; '.join(ativos_ia)}.
    Explique como esses trânsitos afetam esse ponto natal específico."""

                    st.write("### 📝 Seu Prompt está pronto!")
                    st.text_area("Texto do Prompt:", value=prompt_final, height=200)
                    
                    query_codificada = urllib.parse.quote(prompt_final)
                    link_gemini = f"https://gemini.google.com/app?prompt={query_codificada}"
                    st.markdown(f'''
            <a href="{link_gemini}" target="_blank" style="text-decoration: none; color: white !important;">
                <div style="background-color: #4285F4; color: white; text-align: center; padding: 15px; border-radius: 8px; font-weight: bold; font-size: 1.1rem;">
                    🚀 Abrir Gemini e Analisar Agora
                </div>
            </a>
        ''', unsafe_allow_html=True)
                else:
                    st.info("Não há aspectos significativos para este momento.")

# --- GRÁFICO ---
st.title(f"Revolução Planetária: {ano}")
aba_grafico, aba_mandala = st.tabs(["Gráfico de Trânsitos", "Manda Astrológica"])

with aba_grafico:
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
                                    textposition="top center", marker=dict(symbol="triangle-down", color=p['cor'], size=8), showlegend=False, hoverinfo='skip'))

    fig.update_layout(title=dict(text=f'<b>Ponto Natal: {p_texto} a {grau_input}° de {s_texto}</b>', x=0.5, xanchor = 'center', font = dict(size = 28)),
                    height=700,
                    xaxis=dict(rangeslider=dict(visible=True, thickness=0.08), type='date', tickformat='%d/%m\n%Y', hoverformat='%d/%m/%Y %H:%M'),
                    yaxis=dict(title='Intensidade', range=[0, 1.3], fixedrange=True), template='plotly_white', hovermode='x unified', dragmode='pan')
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

    # Chamada da função da seção de IA
    secao_previsao_ia(ano, planeta_selecionado, signo_selecionado, grau_input, long_natal_absoluta_calc)

    # --- LÓGICA DA TABELA DE ASPECTOS ---
    eventos_aspectos = []
    if planeta_selecionado != "Escolha um planeta" and signo_selecionado != "Escolha um signo":
        idx_signo_natal = SIGNOS.index(signo_selecionado)
        long_natal_absoluta = (idx_signo_natal * 30) + grau_decimal
        
        for p in lista_planetas:
            nome_p = p["nome"]
            serie_tabela = df[nome_p].fillna(0).values
            for i in range(1, len(serie_tabela) - 1):
                if serie_tabela[i] > 0.98 and serie_tabela[i] > serie_tabela[i-1] and serie_tabela[i] > serie_tabela[i+1]:
                    idx_ini = i
                    while idx_ini > 0 and serie_tabela[idx_ini] > 0.01: idx_ini -= 1
                    idx_fim = i
                    while idx_fim < len(serie_tabela) - 1 and serie_tabela[idx_fim] > 0.01: idx_fim += 1
                    
                    row_pico = df.iloc[i]
                    long_trans = row_pico[f"{nome_p}_long"]
                    
                    eventos_aspectos.append({
                        "Início": df.iloc[idx_ini]['date'].strftime('%d/%m/%Y %H:%M'),
                        "Pico": row_pico['date'].strftime('%d/%m/%Y %H:%M'),
                        "Término": df.iloc[idx_fim]['date'].strftime('%d/%m/%Y %H:%M'),
                        "Planeta e Signo Natal": f"{planeta_selecionado} em {signo_selecionado}",
                        "Planeta e Signo em Trânsito": f"{nome_p.capitalize()} em {get_signo(long_trans)}",
                        "Trânsito": row_pico[f"{nome_p}_status"],
                        "Aspecto": calcular_aspecto(long_trans, long_natal_absoluta)
                    })

    # --- EXIBIÇÃO DAS TABELAS ---
    st.divider()
    st.markdown("<h3 style='text-align: center;'>📅 Tabela de Trânsitos e Aspectos (Ponto Natal)</h3>", unsafe_allow_html=True)
    col_a1, col_a2, col_a3 = st.columns([0.05, 0.9, 0.05])
    with col_a2:
        if eventos_aspectos:
            st.dataframe(pd.DataFrame(eventos_aspectos), use_container_width=True, hide_index=True, height=(len(eventos_aspectos) + 1) * 35 + 3)

    st.markdown(f"<h3 style='text-align: center;'>🔄 Movimento Anual dos Planetas em {ano}</h3>", unsafe_allow_html=True)
    col_m1, col_m2, col_m3 = st.columns([1, 2, 1])
    with col_m2:
        st.dataframe(df_mov_anual, use_container_width=True, hide_index=True, height=(len(df_mov_anual) + 1) * 35 + 3)

    # --- DOWNLOADS ---
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        buf = io.StringIO()
        fig.write_html(buf, config={'scrollZoom': True})
        st.download_button("📥 Baixar Gráfico Interativo (HTML)", buf.getvalue(), f"revolucao_planetaria_{ano}_{planeta_selecionado}_em_{signo_selecionado}_grau_{grau_limpo_file}.html", "text/html")
    with c2:
        if eventos_aspectos:
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine='openpyxl') as w: pd.DataFrame(eventos_aspectos).to_excel(w, index=False)
            st.download_button("📂 Baixar Tabela Aspectos (Excel)", out.getvalue(), f"aspectos_{ano}_{planeta_selecionado}_em_{signo_selecionado}_grau_{grau_limpo_file}.xlsx")
        else:
            st.button("📂 Baixar Tabela Aspectos (Excel)", disabled=True)
    with c3:
        out_m = io.BytesIO()
        with pd.ExcelWriter(out_m, engine='openpyxl') as w: df_mov_anual.to_excel(w, index=False)
        st.download_button("🔄 Baixar Movimento Anual (Excel)", out_m.getvalue(), f"movimento_planetas_{ano}.xlsx")

with aba_mandala:
    st.markdown("<h2 style='text-align: center;'>🎡 Mandala do Céu</h2>", unsafe_allow_html=True)
    col_m1, col_m2, col_m3 = st.columns([1, 2, 1])
    with col_m1:
        data_m = st.date_input("Data", value=date(ano, 1, 1), key="m_data")
        hora_m = st.time_input("Hora", value=datetime.now().time(), key="m_hora")
        h_dec_m = hora_m.hour + (hora_m.minute / 60.0)
    with col_m2:
        # Certifique-se que a pasta 'icones' existe com seus arquivos .svg
        fig_mandala = criar_mandala_astrologica(data_m.year, data_m.month, data_m.day, h_dec_m, "icones")
        st.plotly_chart(fig_mandala, use_container_width=True, config={'displayModeBar': False})