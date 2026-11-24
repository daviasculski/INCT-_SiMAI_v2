from pathlib import Path
import json

import ipywidgets as widgets
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from IPython.display import HTML, clear_output, display

pio.templates.default = "plotly_white"

pastas = [Path.cwd().resolve(), *Path.cwd().resolve().parents]
candidatos = []
for pasta in pastas:
    candidatos.extend(
        [
            pasta / "dados" / "processados" / "data_atualizado.json",
            pasta / "INCT-_SiMAI_v2" / "dados" / "processados" / "data_atualizado.json",
        ]
    )
caminho_dados = next((caminho for caminho in candidatos if caminho.is_file()), None)
if caminho_dados is None:
    raise FileNotFoundError(
        "Não encontrei dados/processados/data_atualizado.json. "
        "Abra o notebook dentro do projeto INCT-_SiMAI_v2."
    )

with caminho_dados.open(encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

df = pd.DataFrame(
    [
        {
            "nivel_m": float(nivel.removesuffix("m").replace("_", ".")),
            "bairro": bairro,
            **valores,
        }
        for nivel, bairros in dados.items()
        for bairro, valores in bairros.items()
    ]
)

niveis_esperados = np.round(np.arange(3.0, 10.0 + 0.1, 0.1), 1)
niveis_disponiveis = np.sort(df["nivel_m"].unique())
if not np.array_equal(np.round(niveis_disponiveis, 1), niveis_esperados):
    raise ValueError("A base não contém todos os níveis de 3,0 m a 10,0 m em passos de 0,1 m.")

populacao_por_nivel = (
    df.groupby("nivel_m", as_index=False)["affected_population"]
    .sum()
    .sort_values("nivel_m")
)

estilo = """
<style>
.dashboard-titulo { color: #172b45; font-size: 23px; font-weight: 700; margin: 4px 0; }
.dashboard-subtitulo { color: #65758b; margin: 0 0 14px; }
.metricas { display: flex; gap: 12px; margin: 8px 0 14px; flex-wrap: wrap; }
.metrica { background: #fff; border: 1px solid #dce5ef; border-radius: 10px; padding: 14px 18px; flex: 1; min-width: 180px; }
.metrica-label { color: #78889d; font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.metrica-valor { color: #203047; font-size: 25px; font-weight: 700; margin-top: 5px; }
.dashboard-aviso { background: #fff8e8; border-left: 4px solid #e6a23c; border-radius: 4px; color: #664d18; padding: 10px 14px; margin: 10px 0 14px; }
</style>
<div class="dashboard-titulo">Monitoramento de cheias — Porto Alegre</div>
<div class="dashboard-subtitulo">Simulação de impactos por nível do Guaíba | Dados INCT/SIMAI</div>
<div class="dashboard-aviso"><b>Importante:</b> valores estimados a partir da base processada; não são dados em tempo real nem alerta oficial.</div>
"""

controle_nivel = widgets.FloatSlider(
    value=5.3,
    min=3.0,
    max=10.0,
    step=0.1,
    description="Nível do Guaíba:",
    readout_format=".1f",
    continuous_update=False,
    style={"description_width": "initial"},
    layout=widgets.Layout(width="99%"),
)
legenda_nivel = widgets.HTML(
    "<div style='display:flex;justify-content:space-between;color:#718096;font-size:12px'>"
    "<span>3,0 m</span><span style='color:#c0392b'>Recorde de maio/2024: 5,35 m</span>"
    "<span>10,0 m</span></div>"
)
saida_metricas = widgets.Output()
saida_percentual = widgets.Output(layout=widgets.Layout(width="50%"))
saida_ranking = widgets.Output(layout=widgets.Layout(width="50%"))
saida_populacao = widgets.Output()


def formatar_numero(valor):
    return f"{int(valor):,}".replace(",", ".")


def atualizar_dashboard(nivel_escolhido):
    nivel_escolhido = round(float(nivel_escolhido), 1)
    dados_nivel = df.loc[np.isclose(df["nivel_m"], nivel_escolhido)].copy()
    if dados_nivel.empty:
        raise ValueError(f"Não há dados para o nível de {nivel_escolhido:.1f} m.")

    bairros_atingidos = dados_nivel.loc[dados_nivel["affected_buildings"] > 0].copy()
    pessoas = int(dados_nivel["affected_population"].sum())
    predios = int(dados_nivel["affected_buildings"].sum())
    qtd_bairros = int(bairros_atingidos["bairro"].nunique())

    with saida_metricas:
        clear_output(wait=True)
        display(
            HTML(
                f"""
                <div class="metricas">
                  <div class="metrica"><div class="metrica-label">Pessoas afetadas</div><div class="metrica-valor">{formatar_numero(pessoas)}</div></div>
                  <div class="metrica"><div class="metrica-label">Prédios afetados</div><div class="metrica-valor">{formatar_numero(predios)}</div></div>
                  <div class="metrica"><div class="metrica-label">Bairros atingidos</div><div class="metrica-valor">{formatar_numero(qtd_bairros)}</div></div>
                </div>
                """
            )
        )

    fig_percentual = px.bar(
        bairros_atingidos.sort_values("percentage", ascending=True),
        x="percentage",
        y="bairro",
        orientation="h",
        color="percentage",
        color_continuous_scale=[[0, "#d9f0ee"], [1, "#079c99"]],
        range_color=(0, 100),
        hover_data={
            "affected_buildings": True,
            "total_buildings": True,
            "percentage": ":.1f",
        },
        labels={
            "percentage": "% de prédios afetados",
            "bairro": "Bairro",
            "affected_buildings": "Prédios afetados",
            "total_buildings": "Prédios na base",
        },
        title=f"Prédios afetados por bairro — nível {nivel_escolhido:.1f} m",
    )
    fig_percentual.update_layout(
        height=max(360, 24 * len(bairros_atingidos) + 100),
        coloraxis_showscale=False,
        margin={"l": 10, "r": 15, "t": 55, "b": 35},
        xaxis={"range": [0, 100], "ticksuffix": "%"},
    )

    ranking = (
        bairros_atingidos.sort_values("affected_buildings", ascending=False)
        .head(10)
        .sort_values("affected_buildings", ascending=True)
    )
    fig_ranking = px.bar(
        ranking,
        x="affected_buildings",
        y="bairro",
        orientation="h",
        color="affected_buildings",
        color_continuous_scale=[[0, "#cfe8e7"], [1, "#087f8c"]],
        labels={"affected_buildings": "Prédios afetados", "bairro": "Bairro"},
        title=f"Top 10 bairros mais afetados — nível {nivel_escolhido:.1f} m",
    )
    fig_ranking.update_layout(
        height=430,
        coloraxis_showscale=False,
        margin={"l": 10, "r": 15, "t": 55, "b": 35},
    )

    valor_populacao = int(
        populacao_por_nivel.loc[
            np.isclose(populacao_por_nivel["nivel_m"], nivel_escolhido),
            "affected_population",
        ].iloc[0]
    )
    fig_populacao = px.line(
        populacao_por_nivel,
        x="nivel_m",
        y="affected_population",
        markers=True,
        labels={
            "nivel_m": "Nível do rio (m)",
            "affected_population": "População afetada estimada",
        },
        title="População afetada estimada por nível do Guaíba",
    )
    fig_populacao.update_traces(line_color="#087f8c", name="População estimada")
    fig_populacao.add_vline(
        x=5.35,
        line_dash="dash",
        line_color="#d64b45",
        annotation_text="Recorde maio/2024 — 5,35 m",
        annotation_position="top right",
    )
    fig_populacao.add_trace(
        go.Scatter(
            x=[nivel_escolhido],
            y=[valor_populacao],
            mode="markers",
            name=f"Nível selecionado: {nivel_escolhido:.1f} m",
            marker={
                "size": 13,
                "color": "#f0a43c",
                "line": {"color": "white", "width": 2},
            },
            hovertemplate=(
                "Nível selecionado: %{x:.1f} m<br>"
                "População estimada: %{y:,.0f}<extra></extra>"
            ),
        )
    )
    fig_populacao.update_layout(
        height=380,
        margin={"l": 15, "r": 20, "t": 60, "b": 45},
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.12, "x": 1, "xanchor": "right"},
    )

    with saida_percentual:
        clear_output(wait=True)
        display(fig_percentual)
    with saida_ranking:
        clear_output(wait=True)
        display(fig_ranking)
    with saida_populacao:
        clear_output(wait=True)
        display(fig_populacao)


painel = widgets.VBox(
    [
        widgets.HTML(estilo),
        controle_nivel,
        legenda_nivel,
        saida_metricas,
        widgets.HBox(
            [saida_percentual, saida_ranking],
            layout=widgets.Layout(align_items="flex-start", width="100%"),
        ),
        saida_populacao,
    ]
)
controle_nivel.observe(
    lambda evento: atualizar_dashboard(evento["new"])
    if evento["name"] == "value"
    else None,
    names="value",
)
atualizar_dashboard(controle_nivel.value)
display(painel)
