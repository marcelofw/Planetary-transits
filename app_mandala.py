import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
from datetime import datetime, timedelta, timezone, date
from geopy.geocoders import Nominatim

if 'data_ref' not in st.session_state:
    agora_ut = datetime.now()
    st.session_state.data_ref = agora_ut - timedelta(hours=3)

def on_button_click(delta_type, value):
    if delta_type == 'minutes':
        nova_data = st.session_state.data_ref + relativedelta(minutes=value)
    elif delta_type == 'hours':
        nova_data = st.session_state.data_ref + timedelta(hours=value)
    elif delta_type == 'days':
        nova_data = st.session_state.data_ref + timedelta(days=value)
    elif delta_type == 'weeks':
        nova_data = st.session_state.data_ref + relativedelta(weeks=value)
    elif delta_type == 'months':
        nova_data = st.session_state.data_ref + relativedelta(months=value)
    elif delta_type == 'years':
        nova_data = st.session_state.data_ref + relativedelta(years=value)
    else:
        nova_data = st.session_state.data_ref

    st.session_state.data_ref = nova_data
    st.session_state.data_widget = nova_data.date()
    st.session_state.hora_widget = nova_data.time()

@st.cache_data
def buscar_coordenadas(cidade):
    try:
        geolocator = Nominatim(user_agent="meu_app_astrologico_v1")
        location = geolocator.geocode(cidade, timeout=10)
        if location:
            return location.latitude, location.longitude, location.address
        return None, None, None
    except:
        return None, None, None
    
# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Mandala Astrológica Interativa", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DejaVu+Sans&display=swap');
    
    /* Garante que o Plotly tente usar a fonte injetada */
    .main {
        font-family: 'DejaVu Sans', sans-serif;
    }
    /* Trava o fundo da área do gráfico para não piscar branco */
    .stPlotlyChart {
        background-color: black !important;
        border-radius: 50%; /* Ajuda a focar na mandala */
    }
    /* Esconde o efeito de carregamento visual do Streamlit */
    .stBlock[data-testid="stVerticalBlock"] > div:nth-child(1) > div {
        transition: none !important;
    }
            /* Remove o efeito de esmaecimento (fade) ao atualizar */
    [data-testid="stBlock"] {
        opacity: 1 !important;
    }

    /* Remove a animação de pulso/fade especificamente dos gráficos Plotly */
    .stPlotlyChart {
        opacity: 1 !important;
        transition: none !important;
    }

    /* Garante que a tabela também não mude de opacidade */
    .stTable, [data-testid="stDataFrame"] {
        opacity: 1 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES ---
SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

SIMBOLOS_SIGNOS_UNICODE = [
    "♈", "♉", "♊", "♋", "♌", "♍", 
    "♎", "♏", "♐", "♑", "♒", "♓"
]

CORES_SIGNOS = {
    "♈": "red", "♌": "red", "♐": "red",          
    "♉": "brown", "♑": "brown", "♍": "brown",    
    "♋": "#0533FF", "♏": "#0533FF", "♓": "#0533FF",     
    "♊": "#FFD700", "♎": "#FFD700", "♒": "#FFD700" 
}

ASPECTOS = {
    0: ("Conjunção", "☌"), 
    60: ("Sêxtil", "✶"), 
    90: ("Quadratura", "□"), 
    120: ("Trígono", "△"), 
    180: ("Oposição", "☍")
}

SIMBOLOS_PLANETAS = {
    "SOL": "☉", "LUA": "☽", "MERCÚRIO": "☿", "VÊNUS": "♀", 
    "MARTE": "♂", "JÚPITER": "♃", "SATURNO": "♄", "URANO": "♅", 
    "NETUNO": "♆", "PLUTÃO": "♇"
}

# --- INTERFACE STREAMLIT ---
st.sidebar.title("🪐 Configurações")

# Inputs manuais (Sincronizados com o session_state)
d_input = st.sidebar.date_input("Data", value=st.session_state.data_ref.date(), key="data_widget", min_value = date(1900, 1, 1), max_value = date(2100, 12, 31))
t_input = st.sidebar.time_input("Hora", value=st.session_state.data_ref.time(), key="hora_widget", help="Entre com horário de Brasília.")

data_vinda_do_widget = datetime.combine(d_input, t_input)
if data_vinda_do_widget != st.session_state.data_ref:
    st.session_state.data_ref = data_vinda_do_widget

data_para_o_calculo_ut = st.session_state.data_ref + timedelta(hours=3)

col_r, col_a = st.sidebar.columns(2)
col_r.button("⬅️ -1 Minuto", on_click=on_button_click, args=['minutes', -1])
col_a.button("+1 Minuto ➡️", on_click=on_button_click, args=['minutes', 1])

col_r.button("⬅️ -1 Hora", on_click=on_button_click, args=['hours', -1])
col_a.button("+1 Hora ➡️", on_click=on_button_click, args=['hours', 1])

col_r.button("⬅️ -1 Dia", on_click=on_button_click, args=['days', -1])
col_a.button("+1 Dia ➡️", on_click=on_button_click, args=['days', 1])

col_r.button("⬅️ -1 Semana", on_click=on_button_click, args=['weeks', -1])
col_a.button("+1 Semana ➡️", on_click=on_button_click, args=['weeks', 1])

col_r.button("⬅️ -1 Mês", on_click=on_button_click, args=['months', -1])
col_a.button("+1 Mês ➡️", on_click=on_button_click, args=['months', 1])

col_r.button("⬅️ -1 Ano", on_click=on_button_click, args=['years', -1])
col_a.button("+1 Ano ➡️", on_click=on_button_click, args=['years', 1])

#
incluir_ascendente = st.sidebar.checkbox("Quero incluir o Ascendente", value=False)
asc_valor = None
if incluir_ascendente:
    local_nascimento = st.stidebar.text_input("Cidade de Nascimento", "São Paulo, Brasil")

    lat, lon, endereco = buscar_coordenadas(local_nascimento)

    if lat:
        # Cálculo do Ascendente usando swisseph
        # data_para_o_calculo_ut deve ser a sua data já em UTC
        jd_ut = swe.julday(data_para_o_calculo_ut.year, data_para_o_calculo_ut.month, 
                        data_para_o_calculo_ut.day, data_para_o_calculo_ut.hour + data_para_o_calculo_ut.minute/60.0)
        
        # 'P' para o sistema de casas Placidus
        cuspides, ascmc = swe.houses(jd_ut, lat, lon, b'P')
        asc_valor = ascmc[0]
        
        st.sidebar.success(f"📍 Localizado!")
        st.sidebar.caption(f"{endereco}")
    else:
        st.sidebar.error("Cidade não encontrada.")

# Atualização do estado com base no que foi digitado
st.session_state.data_ref = datetime.combine(d_input, t_input)

# --- FUNÇÕES AUXILIARES ---
def obter_simbolo_aspecto(long1, long2):
    diff = abs(long1 - long2) % 360
    if diff > 180: diff = 360 - diff
    for angulo, (nome, simbolo) in ASPECTOS.items():
        if abs(diff - angulo) <= 5:  # Orbe de tolerância
            return simbolo
    return ""

def criar_mandala_astrologica(dt):
    # Cálculo do Julian Day (Apenas argumentos posicionais para evitar TypeError)
    ano, mes, dia = dt.year, dt.month, dt.day
    hora_decimal = dt.hour + (dt.minute / 60.0) + (dt.second / 3600.0)
    jd = swe.julday(ano, mes, dia, hora_decimal)
    
    planetas_cfg = [
        {"id": swe.SUN, "nome": "Sol", "cor": "#FFD700", "sym": "☉"},
        {"id": swe.MOON, "nome": "Lua", "cor": "#A6A6A6", "sym": "☽"},
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
    raio_interno = 3.5
    
    # --- POSIÇÕES ---
    posicoes = []
    for p in planetas_cfg:
        res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH)
        long_abs = res[0]
        id_signo = int(long_abs / 30)
        grau_no_signo = long_abs % 30
        min_f, gr_i = math.modf(grau_no_signo)
        min_i = int(round(min_f * 60))
        
        posicoes.append({
            "nome": p["nome"], "long": long_abs, "cor": p["cor"], 
            "sym": p["sym"], "grau_int": int(gr_i), "min_int": min_i,
            "signo": SIGNOS[id_signo % 12], "long_visual": long_abs 
        })

    # Lógica anti-sobreposição (ajuste visual dos símbolos)
# 1. Inicializa a posição visual com a posição real
# 1. Definimos a ordem real uma única vez antes do loop
    posicoes.sort(key=lambda x: x['long'])
    for i, p in enumerate(posicoes):
        p['long_visual'] = p['long']
        p['id_ordem'] = i # Identificador único de posição na fila

    dist_min = 9 # Aumentei para 10 para garantir legibilidade no celular
    
    for _ in range(20): # Mais iterações para estabilizar o bloco
        # Ordenamos visualmente para o loop de vizinhança
        posicoes.sort(key=lambda x: x['long_visual'])
        
        for i in range(len(posicoes)):
            for j in range(len(posicoes)):
                if i == j: continue
                
                p1 = posicoes[i]
                p2 = posicoes[j]
                
                # Cálculo da distância curta (mesmo do seu original)
                diff = (p2['long_visual'] - p1['long_visual'] + 180) % 360 - 180
                
                if abs(diff) < dist_min:
                    # --- A CORREÇÃO DA LÓGICA ---
                    # Checamos a distância astronômica real para saber quem deve estar na frente
                    diff_real = (p2['long'] - p1['long'] + 180) % 360 - 180
                    
                    # Se a repulsão visual (diff) está tentando colocar os planetas 
                    # em ordem oposta à real (diff_real), nós forçamos a direção correta.
                    direcao = 1 if diff_real >= 0 else -1
                    
                    # A força agora sempre atua para manter o dist_min na direção da ordem real
                    forca = (dist_min - abs(diff)) / 2
                    
                    p2['long_visual'] = (p2['long_visual'] + forca * direcao) % 360
                    p1['long_visual'] = (p1['long_visual'] - forca * direcao) % 360

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

    # --- 2. ANEL DOS SIGNOS E RÉGUA ---
    for i in range(12):        
        # RÉGUA: Adiciona 30 pontos por signo
        graus_signo = list(range(i * 30, (i + 1) * 30))
        # Criamos traços curtos para cada grau
        for g in graus_signo:
            # Traço maior para 0, 10, 20 (decanatos), menor para os outros
            tamanho_regua = 8.6 if g % 10 == 0 else 8.3
            fig.add_trace(go.Scatterpolar(
                r=[8.0, tamanho_regua], theta=[g, g],
                mode='lines', line=dict(color="black", width=1),
                showlegend=False, hoverinfo='skip'))
    
    for i, signo in enumerate(SIGNOS):
        centro_polar = i * 30 + 15
        simbolo = SIMBOLOS_SIGNOS_UNICODE[i]
        cor_do_signo = CORES_SIGNOS.get(simbolo, "black")

        fig.add_trace(go.Barpolar(r=[2], theta=[centro_polar], width=[30], base=8, 
                                  marker_color="white", marker_line_color="black", marker_line_width=1, showlegend=False, hoverinfo='skip'))

        # Símbolos dos signos
        fig.add_trace(go.Scatterpolar(
            r=[9.0], theta=[i * 30 + 15], mode='text', text=[simbolo],
            textfont=dict(size=50, color=cor_do_signo, family="DejaVu Sans"), showlegend=False, hoverinfo='none'))

    fig.add_trace(go.Scatterpolar(r=[10] * 361, theta=list(range(361)), mode='lines', 
                                  line=dict(color="black", width=2), showlegend=False, hoverinfo='skip'))

    # --- 3. PLANETAS E GRAUS ---
    for p in posicoes:
        hover_template = f"{p['nome']}<br>{p['signo']}<br>{p['grau_int']}º{p['min_int']}'<extra></extra>"
        indice_signo_planeta = int(p['long'] / 30) % 12
        simbolo_signo_planeta = SIMBOLOS_SIGNOS_UNICODE[indice_signo_planeta]
        cor_elemento = CORES_SIGNOS.get(simbolo_signo_planeta, "black")

        # Anotações Graus
        fig.add_trace(go.Scatterpolar(r=[6.3], theta=[p["long_visual"]], mode='text', text=[f"{p['grau_int']:02d}°"], 
                                    textfont=dict(size=25, color="black", family="Trebuchet MS"), 
                                    showlegend=False, hovertemplate=hover_template))
        # Anotações Minutos
        fig.add_trace(go.Scatterpolar(r=[4.1], theta=[p["long_visual"]], mode='text', text=[f"{p['min_int']:02d}'"], 
                                    textfont=dict(size=21, color="black", family="Trebuchet MS"), 
                                    showlegend=False, hovertemplate=hover_template))
        # Anotações Símbolo dos Planetas
        fig.add_trace(go.Scatterpolar(r=[5.2], theta=[p["long_visual"]], mode='text', text=[simbolo_signo_planeta], 
                                    textfont=dict(size=32, color=cor_elemento, family="DejaVu Sans"), 
                                    showlegend=False, hovertemplate=hover_template))
        # Marcadores internos
        fig.add_trace(go.Scatterpolar(r=[raio_interno], theta=[p["long"]], mode='markers', 
                                    marker=dict(size=8, color=p["cor"], line=dict(color='black', width=0)), 
                                    showlegend=False, hovertemplate=hover_template))
        # Marcadores externos
        fig.add_trace(go.Scatterpolar(r=[8.0], theta=[p["long"]], mode='markers', 
                                    marker=dict(size=8, color=p["cor"], line=dict(color='black', width=0)), 
                                    showlegend=False, hovertemplate=hover_template))
       # Planetas
        fig.add_trace(go.Scatterpolar(
            r=[7.4], theta=[p["long_visual"]], 
            mode='text', 
            text=[f"{p['sym']}"], # Adicionado Negrito via tag HTML
            textfont=dict(size=44, color=p["cor"], family="'DejaVu Sans', 'Segoe UI Symbol', 'Apple Symbols', sans-serif"), 
            showlegend=False, hovertemplate=hover_template
        ))
    
    # --- LAYOUT FINAL ---
    fig.update_layout(
            width=850, height=850, autosize=False, uirevision="constant",
            polar=dict(
                radialaxis=dict(visible=False, range=[0, 10]),
                angularaxis=dict(
                    direction="counterclockwise", 
                    rotation=180, # Áries à esquerda
                    showgrid=False, 
                    gridcolor="rgba(0,0,0,0.1)",
                    showticklabels=False
            )
        ),
        hoverlabel=dict(bgcolor="black", font_size=14, font_family="Arial"),
        showlegend=False,
        margin=dict(t=30, b=30, l=30, r=30, pad=0),
        paper_bgcolor="#0e1117",
        dragmode=False
    )
    return fig



# --- 6. CONTEÚDO PRINCIPAL ---
st.title("🔭 Mandala Astrológica Interativa")
st.subheader(f"{st.session_state.data_ref.strftime('%d/%m/%Y %H:%M')} - Horário de Brasília")

col1, col2 = st.columns([1.5, 1])

with col1:
    fig_mandala = criar_mandala_astrologica(data_para_o_calculo_ut)
    st.plotly_chart(
        fig_mandala, 
        use_container_width=False,
        key="mandala_principal",
        config={'displayModeBar':False, 'responsive':False, 'frameMargins': 0}
        )

# with col2:
    # st.write("### Posições Planetárias")
    # # Cálculos para a tabela
    # dt = data_para_o_calculo_ut
    # jd_tab = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60 + dt.second/3600)
    
    # dados_tabela = []
    # planetas_ids = [
    #     ("Sol", 0), ("Lua", 1), ("Mercúrio", 2), ("Vênus", 3), ("Marte", 4), 
    #     ("Júpiter", 5), ("Saturno", 6), ("Urano", 7), ("Netuno", 8), ("Plutão", 9)
    # ]
    
    # for nome, pid in planetas_ids:
    #     res, _ = swe.calc_ut(jd_tab, pid, swe.FLG_SWIEPH)
    #     long_abs = res[0]
    #     pos_graus = int(long_abs % 30)
    #     pos_minutos = int(round((long_abs % 1) * 60))
    #     indice_signo = int(long_abs / 30)
        
    #     if pos_minutos == 60:
    #         pos_graus += 1
    #         post_minutos = 0

    #         if pos_graus == 30:
    #             pos_graus = 0
    #             indice_signo = (indice_signo + 1) % 12

    #     dados_tabela.append({
    #         "Planeta": nome,
    #         "Signo": SIGNOS[indice_signo],
    #         "Posição": f"{pos_graus:02d}°{pos_minutos:02d}'"
    #     })
    
    # st.dataframe(pd.DataFrame(dados_tabela), hide_index=True, use_container_width=True)