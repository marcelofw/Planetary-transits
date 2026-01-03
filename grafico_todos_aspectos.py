import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

def dms_to_dec(dms_str):
    """Converte string 'Grau.Minuto' para Grau Decimal."""
    if isinstance(dms_str, (int, float)):
        return float(dms_str)
    parts = str(dms_str).split('.')
    degrees = float(parts[0])
    minutes = float(parts[1]) if len(parts) > 1 else 0
    return degrees + (minutes / 60)

def hex_to_rgba(hex_color, opacity):
    """Converte Hex #RRGGBB para rgba(r, g, b, a)."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

def generate_natal_aspects_chart():
    # ==========================================
    # CONFIGURAÇÕES PRINCIPAIS
    # ==========================================
    ano = 2026
    planeta_alvo = swe.MERCURY  # Altere para o planeta desejado
    mes_alvo = 1               # Usado apenas se for a LUA
    
    planetas_nomes = {
        swe.SUN: "SOL", swe.MOON: "LUA", swe.MERCURY: "MERCÚRIO",
        swe.VENUS: "VÊNUS", swe.MARS: "MARTE", swe.JUPITER: "JÚPITER",
        swe.SATURN: "SATURNO", swe.URANUS: "URANO", swe.NEPTUNE: "NETUNO",
        swe.PLUTO: "PLUTÃO"
    }
    
    nome_pt = planetas_nomes.get(planeta_alvo, "PLANETA")
    nome_arquivo = nome_pt.lower().replace("ú", "u").replace("â", "a").replace("õ", "o")

    natal_configs = [
        {"nome": "SOL", "pos": "27.0", "cor": "#FFF12E"},
        {"nome": "LUA", "pos": "6.20", "cor": "#C37DEB"},
        {"nome": "MERCÚRIO", "pos": "19.59", "cor": "#F3A384"},
        {"nome": "VÊNUS", "pos": "5.16", "cor": "#0A8F11"},
        {"nome": "MARTE", "pos": "8.48", "cor": "#F10808"},
        {"nome": "JÚPITER", "pos": "8.57", "cor": "#1746C9"}
    ]
    
    # ==========================================
    # LÓGICA DE PERÍODO E ALTA PRECISÃO GLOBAL
    # ==========================================
    # Definimos um passo de 0.01 para TODOS (Alta Precisão: ~14 minutos)
    step_size = 0.01 

    if planeta_alvo == swe.MOON:
        # A Lua continua restrita a 1 mês por performance (muitos dados)
        jd_start = swe.julday(ano, mes_alvo, 1)
        prox_mes = mes_alvo + 1 if mes_alvo < 12 else 1
        prox_ano = ano if mes_alvo < 12 else ano + 1
        jd_end = swe.julday(prox_ano, prox_mes, 1)
        periodo_txt = f"MÊS {mes_alvo}/{ano}"
    else:
        # Outros planetas: Ano completo com alta precisão
        jd_start = swe.julday(ano, 1, 1)
        jd_end = swe.julday(ano + 1, 1, 1)
        periodo_txt = str(ano)

    steps = np.arange(jd_start, jd_end, step_size)
    
    natal_points = []
    for p in natal_configs:
        natal_points.append({
            "nome": f"{p['nome']} ({p['pos']}°)", 
            "grau": dms_to_dec(p["pos"]), 
            "cor": p["cor"]
        })
    
    all_data = []
    for jd in steps:
        res, _ = swe.calc_ut(jd, planeta_alvo, swe.FLG_SWIEPH) 
        deg_in_sign = res[0] % 30
        y, m, d, h = swe.revjul(jd)
        dt = datetime(y, m, d, int(h), int((h%1)*60))
        
        row = {'date': dt}
        for p in natal_points:
            dist = abs(((deg_in_sign - p["grau"] + 15) % 30) - 15)
            row[p["nome"]] = np.exp(-0.5 * (dist / 1.5)**2) if dist <= 5 else 0
        all_data.append(row)

    df = pd.DataFrame(all_data)
    fig = go.Figure()

    for p in natal_points:
        fig.add_trace(go.Scatter(
            x=df['date'], y=df[p['nome']],
            mode='lines', name=p['nome'],
            line=dict(color=p['cor'], width=2),
            fill='tozeroy', fillcolor=hex_to_rgba(p['cor'], 0.12),
            hovertemplate="<b>%{x|%d/%m %H:%M}</b><br>Força: %{y:.3f}<extra></extra>"
        ))

    # Anotações de Picos com Hora e Minuto para todos
    for p in natal_points:
        name = p['nome']
        peak_mask = (df[name] > 0.98) & (df[name] > df[name].shift(1)) & (df[name] > df[name].shift(-1))
        picos = df[peak_mask]
        
        for _, row in picos.iterrows():
            fig.add_annotation(
                x=row['date'], y=row[name], 
                text=row['date'].strftime('%d/%m %H:%M'),
                showarrow=True, arrowhead=1, ax=0, ay=-25,
                font=dict(color=p['cor'], size=9, family="Arial Black"),
                bgcolor="rgba(255,255,255,0.85)", bordercolor=p['cor']
            )

    # LAYOUT
    fig.update_layout(
        title=dict(text=f'<b>TRÂNSITOS DE {nome_pt} - {periodo_txt}</b><br><span style="font-size:11px">Alta Precisão Temporal (Amostragem: 14 min)</span>', x=0.5), 
        xaxis=dict(
            rangeslider=dict(visible=True, thickness=0.05),
            type='date',
            tickformat='%d/%m\n%H:%M'
        ),
        yaxis=dict(title='Intensidade do Aspecto', range=[0, 1.3]),
        template='plotly_white',
        dragmode='pan',
        hovermode='x unified'
    )

    file_name = f"aspectos_{nome_arquivo}_{ano}_alta_precisao.html"
    fig.write_html(file_name)
    print(f"Sucesso! Gráfico de alta precisão para {nome_pt} gerado.")

if __name__ == "__main__":
    generate_natal_aspects_chart()