import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Mandala Astrológica AI", layout="centered")

SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

CORES_SIGNOS = [
    "#FF4B4B", "#FF9F4B", "#FFD34B", "#99FF4B", "#4BFF81", "#4BFFD3",
    "#4BAFFF", "#4B5BFF", "#814BFF", "#D34BFF", "#FF4B9F", "#FF4B4B"
]

# --- FUNÇÕES DE CÁLCULO GEOMÉTRICO ---
def get_coords(angle, radius):
    """Converte ângulo (graus) e raio em coordenadas cartesianas (x, y)"""
    rad = np.radians(angle)
    x = radius * np.cos(rad)
    y = radius * np.sin(rad)
    return x, y

def criar_mandala(dados_planetas):
    fig = go.Figure()

    # 1. Desenhar as fatias dos Signos (30 graus cada)
    for i, signo in enumerate(SIGNOS):
        angulo_inicio = i * 30
        angulo_fim = (i + 1) * 30
        
        # Criar os arcos dos signos
        angulos = np.linspace(angulo_inicio, angulo_fim, 20)
        x_arco = [get_coords(a, 10)[0] for a in angulos] + [0]
        y_arco = [get_coords(a, 10)[1] for a in angulos] + [0]
        
        fig.add_trace(go.Scatter(
            x=x_arco, y=y_arco,
            fill="toself",
            fillcolor=CORES_SIGNOS[i],
            line=dict(color="white", width=1),
            opacity=0.3,
            name=signo,
            hoverinfo="text",
            text=f"Signo: {signo}"
        ))

        # Adicionar nomes dos signos na borda
        x_txt, y_txt = get_coords(angulo_inicio + 15, 11)
        fig.add_annotation(x=x_txt, y=y_txt, text=signo[:3], showarrow=False, font=dict(size=12))

    # 2. Desenhar os Planetas
    for p in dados_planetas:
        # Converter posição (ex: Áries 10° -> 10. Touro 5° -> 35)
        long_absoluta = (SIGNOS.index(p['signo']) * 30) + p['grau']
        x_p, y_p = get_coords(long_absoluta, 7.5) # Raio menor para os planetas
        
        fig.add_trace(go.Scatter(
            x=[x_p], y=[y_p],
            mode="markers+text",
            name=p['nome'],
            marker=dict(size=15, color="black"),
            text=[p['simbolo']],
            textposition="top center",
            hoverinfo="text",
            texttemplate=f"<b>{p['simbolo']}</b>",
            hovertext=f"{p['nome']}: {p['grau']}° de {p['signo']}"
        ))

    # Configurações de Layout
    fig.update_layout(
        width=700, height=700,
        showlegend=False,
        xaxis=dict(visible=False, range=[-13, 13]),
        yaxis=dict(visible=False, range=[-13, 13]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, l=10, r=10)
    )
    
    return fig

# --- INTERFACE ---
st.title("🌌 Mandala Astrológica Interativa")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Posições")
    # Exemplo simplificado de input
    p1_signo = st.selectbox("Signo do Sol", SIGNOS, index=5)
    p1_grau = st.slider("Grau do Sol", 0, 29, 27)
    
    p2_signo = st.selectbox("Signo da Lua", SIGNOS, index=4)
    p2_grau = st.slider("Grau da Lua", 0, 29, 6)

    planetas = [
        {"nome": "Sol", "simbolo": "☉", "signo": p1_signo, "grau": p1_grau},
        {"nome": "Lua", "simbolo": "☽", "signo": p2_signo, "grau": p2_grau},
    ]

with col2:
    mandala_fig = criar_mandala(planetas)
    st.plotly_chart(mandala_fig, use_container_width=True)

st.info("Esta é uma representação visual. Integre com o `swisseph` para automatizar as posições reais.")






















































