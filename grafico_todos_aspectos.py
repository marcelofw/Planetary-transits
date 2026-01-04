import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# Lista de Signos para conversão
SIGNOS = [
    "Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem",
    "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"
]

def get_signo(longitude):
    """Converte longitude absoluta (0-360) no nome do signo."""
    idx = int(longitude / 30)
    return SIGNOS[idx % 12]

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
    # 1. CONFIGURAÇÃO
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
    # 2. PROCESSAMENTO
    # ==========================================
    jd_start = swe.julday(ano, 1, 1)
    jd_end = swe.julday(ano + 1, 1, 1)
    step_size = 0.05 
    steps = np.arange(jd_start, jd_end, step_size)
    
    all_data = []
    for jd in steps:
        y, m, d, h = swe.revjul(jd)
        dt = datetime(y, m, d, int(h), int((h%1)*60))
        row = {'date': dt}
        for p in planetas_monitorados:
            res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH)
            long_abs = res[0]
            pos_no_signo = long_abs % 30
            
            dist = abs(((pos_no_signo - grau_decimal + 15) % 30) - 15)
            val = np.exp(-0.5 * (dist / 1.2)**2) if dist <= 5 else 0
            
            # Se a intensidade for quase zero, não incluímos no hover
            row[p["nome"]] = val if val > 0.01 else None
            row[f"{p['nome']}_signo"] = get_signo(long_abs)
            
        all_data.append(row)

    df = pd.DataFrame(all_data)

    # ==========================================
    # 3. GRÁFICO
    # ==========================================
    fig = go.Figure()

    for p in planetas_monitorados:
        fig.add_trace(go.Scatter(
            x=df['date'], 
            y=df[p['nome']],
            mode='lines',
            name=p['nome'],
            line=dict(color=p['cor'], width=2.5),
            fill='tozeroy',
            fillcolor=hex_to_rgba(p['cor'], 0.15),
            customdata=df[f"{p['nome']}_signo"],
            hovertemplate="%{customdata}<extra></extra>",
            connectgaps=False 
        ))

    fig.update_layout(
        title=dict(text=f'🔭 Revolução Planetária {ano}: Grau {grau_alvo_natal}°', x=0.5),
        xaxis=dict(
            title='Arraste para navegar no tempo',
            rangeslider=dict(visible=True, thickness=0.08),
            type='date',
            tickformat='%d/%m\n%Y',
            hoverformat='%d/%m/%Y %H:%M',
            showspikes=True,
            spikemode='across',
            spikethickness=1,
            spikecolor="black"
        ),
        yaxis=dict(title='Intensidade', range=[0, 1.3], fixedrange=True),
        template='plotly_white',
        hovermode='x unified', 
        dragmode='pan',
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_color="black",
            font_family="Arial"
        )
    )

    # ==========================================
    # 4. SALVAMENTO DINÂMICO
    # ==========================================
    grau_limpo = grau_alvo_natal.replace('.', '_')
    # Nome do arquivo agora contém o ano e o grau formatado
    file_name = f"revolucao_planetaria_{ano}_grau_{grau_limpo}.html"
    
    fig.write_html(file_name, config={'scrollZoom': True})
    
    print(f"Sucesso! Gráfico gerado para o ano {ano} e grau {grau_alvo_natal}.")
    print(f"Arquivo salvo como: {file_name}")
s
if __name__ == "__main__":
    generate_degree_transit_chart()