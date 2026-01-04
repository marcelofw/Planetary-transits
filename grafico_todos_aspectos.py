import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

def dms_to_dec(dms_str):
    if isinstance(dms_str, (int, float)):
        return float(dms_str)
    parts = str(dms_str).split('.')
    degrees = float(parts[0])
    minutes = float(parts[1]) if len(parts) > 1 else 0
    return degrees + (minutes / 60)

def hex_to_rgba(hex_color, opacity):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

def generate_degree_transit_chart():
    # ==========================================
    # 1. CONFIGURAÇÃO DO ALVO
    # ==========================================
    ano = 2026
    grau_alvo_natal = "27.0"  
    grau_decimal = dms_to_dec(grau_alvo_natal)
    
    planetas_monitorados = [
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

    # ==========================================
    # 2. PROCESSAMENTO TEMPORAL
    # ==========================================
    jd_start = swe.julday(ano, 1, 1)
    jd_end = swe.julday(ano + 1, 1, 1)
    step_size = 0.02 
    steps = np.arange(jd_start, jd_end, step_size)
    
    all_data = []
    for jd in steps:
        y, m, d, h = swe.revjul(jd)
        dt = datetime(y, m, d, int(h), int((h%1)*60))
        row = {'date': dt}
        for p in planetas_monitorados:
            res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH)
            pos_no_signo = res[0] % 30
            dist = abs(((pos_no_signo - grau_decimal + 15) % 30) - 15)
            row[p["nome"]] = np.exp(-0.5 * (dist / 1.2)**2) if dist <= 5 else 0
        all_data.append(row)

    df = pd.DataFrame(all_data)

    # ==========================================
    # 3. CONSTRUÇÃO DO GRÁFICO
    # ==========================================
    fig = go.Figure()

    # --- TRAÇO INVISÍVEL (ÂNCORA DO HOVER FLUTUANTE) ---
    fig.add_trace(go.Scatter(
        x=df['date'], 
        y=[0.65] * len(df), 
        mode='lines',
        line=dict(width=40), 
        opacity=0,           
        hoverinfo='x',       
        showlegend=False,
        name=""
    ))

    # --- CAMADAS DOS PLANETAS ---
    for p in planetas_monitorados:
        fig.add_trace(go.Scatter(
            x=df['date'], y=df[p['nome']],
            mode='lines',
            name=p['nome'],
            line=dict(color=p['cor'], width=2),
            fill='tozeroy',
            fillcolor=hex_to_rgba(p['cor'], 0.15),
            hoverinfo='skip', 
            showlegend=True 
        ))

        # Marcar picos
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
        title=dict(text=f'<b>🔭 Revolução planetária {ano}: Grau {grau_alvo_natal}°</b>', x=0.5),
        xaxis=dict(
            title='Arraste para os lados para navegar',
            rangeslider=dict(visible=True, thickness=0.08),
            type='date',
            tickformat='%d/%m\n%Y',
            hoverformat='%d/%m/%Y %H:%M',
            showspikes=True,
            spikemode='across',
            spikethickness=1,
            spikedash='solid',
            spikecolor="black" # Spike alterado para preto para melhor visibilidade
        ),
        yaxis=dict(title='Intensidade', range=[0, 1.3], fixedrange=True),
        template='plotly_white',
        hovermode='x', 
        dragmode='pan'
    )

    fig.update_layout(
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            namelength=0
        )
    )

    # --- CONFIGURAÇÃO DE NOME DE ARQUIVO DINÂMICO (INCLUINDO ANO) ---
    grau_limpo = grau_alvo_natal.replace('.', '_')
    file_name = f"revolucao_planetaria_{ano}_grau_{grau_limpo}.html"

    config = {'scrollZoom': True, 'displayModeBar': True}
    fig.write_html(file_name, config=config)
    
    print(f"Sucesso! Gráfico gerado para o grau {grau_alvo_natal} em {ano}.")
    print(f"Arquivo: {file_name}")

if __name__ == "__main__":
    generate_degree_transit_chart()