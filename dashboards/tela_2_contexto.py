import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboards.comum import (
    NAVY,
    TEAL,
    carregar_peers,
    carregar_simulacao,
    format_level,
    format_number,
    nivel_atual,
    slider_nivel,
)

METRICS = {
    "Prédios afetados": {"column": "affected_buildings", "axis": "Prédios afetados", "format": "number"},
    "População afetada": {"column": "affected_population", "axis": "Pessoas afetadas", "format": "number"},
    "Percentual de prédios": {"column": "percentage", "axis": "Prédios afetados (%)", "format": "percent"},
}


def make_exposure_chart(current_level: pd.DataFrame, metric: dict, selected_metric: str) -> go.Figure:
    column = metric["column"]
    top = current_level.nlargest(10, column).sort_values(column)
    figure = px.bar(
        top, x=column, y="neighborhood", orientation="h", text=column,
        color_discrete_sequence=[TEAL],
    )
    text_template = "%{x:.1f}%" if metric["format"] == "percent" else "%{x:,.0f}"
    figure.update_traces(
        texttemplate=text_template, textposition="outside", cliponaxis=False,
        textfont=dict(size=12, color=NAVY),
        hovertemplate="%{y}<br>" + metric["axis"] + ": %{x:,.1f}<extra></extra>",
    )
    figure.update_layout(
        template="plotly_white", separators=",.", height=380,
        margin=dict(l=4, r=48, t=56, b=8), yaxis_title=None, showlegend=False,
        font=dict(color=NAVY, family="Arial, sans-serif", size=13),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#dce4ee", zeroline=False,
                   tickfont=dict(size=12, color=NAVY),
                   title=dict(text=metric["axis"], font=dict(size=12, color=NAVY))),
        yaxis=dict(showgrid=False, automargin=True, tickfont=dict(size=12, color=NAVY)),
        title=dict(text=f"10 bairros com maior {selected_metric.lower()}",
                   font=dict(size=15, color=NAVY), x=0, xanchor="left", y=0.97, yanchor="top"),
    )
    if metric["format"] == "percent":
        figure.update_xaxes(ticksuffix="%")
    return figure


def make_evolution_chart(simulation: pd.DataFrame, metric: dict, selected_metric: str,
                         current_level: float) -> go.Figure:
    column = metric["column"]
    by_level = simulation.groupby("level_m", as_index=False).agg(
        affected_value=(column, "sum"),
        affected_buildings=("affected_buildings", "sum"),
        total_buildings=("total_buildings", "sum"),
        affected_neighborhoods=("affected_buildings", lambda v: (v > 0).sum()),
    )
    if metric["format"] == "percent":
        by_level["affected_value"] = by_level["affected_buildings"] / by_level["total_buildings"] * 100

    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(
        go.Scatter(x=by_level["level_m"], y=by_level["affected_value"], mode="lines",
                   name=selected_metric, line=dict(color=TEAL, width=3), fill="tozeroy",
                   fillcolor="rgba(21, 154, 156, 0.12)",
                   hovertemplate="Nível %{x:.1f} m<br>%{y:,.0f}<extra></extra>"),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(x=by_level["level_m"], y=by_level["affected_neighborhoods"], mode="lines",
                   name="Bairros atingidos", line=dict(color="#b96b00", width=2, dash="dot"),
                   hovertemplate="Nível %{x:.1f} m<br>%{y} bairros<extra></extra>"),
        secondary_y=True,
    )
    figure.add_vline(x=current_level, line_dash="dash", line_color="#e66f62")
    figure.update_layout(
        template="plotly_white", separators=",.", height=380,
        margin=dict(l=8, r=8, t=56, b=8),
        legend=dict(orientation="h", y=-0.22, yanchor="top", x=0.5, xanchor="center",
                    font=dict(size=12, color=NAVY)),
        font=dict(color=NAVY, family="Arial, sans-serif", size=13),
        plot_bgcolor="white", paper_bgcolor="white",
        title=dict(text=f"Evolução: {selected_metric.lower()} e bairros atingidos",
                   font=dict(size=15, color=NAVY), x=0, xanchor="left", y=0.97, yanchor="top"),
    )
    figure.update_xaxes(title=dict(text="Nível do Guaíba (m)", font=dict(size=12, color=NAVY)),
                        gridcolor="#dce4ee", tickfont=dict(size=12, color=NAVY))
    figure.update_yaxes(title=dict(text=metric["axis"], font=dict(size=12, color=NAVY)),
                        secondary_y=False, gridcolor="#dce4ee", tickfont=dict(size=12, color=NAVY))
    figure.update_yaxes(title=dict(text="Bairros", font=dict(size=12, color=NAVY)),
                        secondary_y=True, showgrid=False, tickformat=".0f",
                        tickfont=dict(size=12, color=NAVY))
    return figure


def wrap_label(text: str, width: int = 38) -> str:
    text = text.replace(", )", ")").replace(",)", ")").rstrip(". ")
    lines, current = [], ""
    for word in text.split():
        if current and len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    lines.append(current)
    return "<br>".join(lines)


def make_occurrences_chart(occurrences: pd.DataFrame) -> go.Figure:
    ordered = occurrences.sort_values("percentage").assign(
        label=lambda f: f["label"].map(wrap_label)
    )
    figure = px.bar(ordered, x="percentage", y="label", orientation="h", text="percentage",
                    color_discrete_sequence=["#557f9d"])
    figure.update_traces(
        texttemplate="%{x:.1f}%", textposition="outside", cliponaxis=False,
        textfont=dict(size=12, color=NAVY),
        hovertemplate="%{y}<br>%{x:.1f}% dos domicílios<extra></extra>",
    )
    figure.update_layout(
        template="plotly_white", separators=",.", height=520,
        margin=dict(l=4, r=30, t=12, b=8), yaxis_title=None, showlegend=False,
        font=dict(color=NAVY, family="Arial, sans-serif", size=12),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(range=[0, 100], showgrid=True, gridcolor="#dce4ee",
                   tickfont=dict(size=12, color=NAVY), ticksuffix="%",
                   title=dict(text="Domicílios (%)", font=dict(size=12, color=NAVY))),
        yaxis=dict(showgrid=False, automargin=True, tickfont=dict(size=12, color=NAVY)),
    )
    return figure


def make_quality_chart(quality_of_life: pd.DataFrame) -> go.Figure:
    colors = {
        "Pior que antes das enchentes": "#e66f62",
        "Igual a antes das enchentes": "#7890ac",
        "Melhor que antes das enchentes": TEAL,
    }
    figure = px.pie(quality_of_life, values="percentage", names="label", hole=0.62,
                    color="label", color_discrete_map=colors)
    figure.update_traces(
        textposition="inside", texttemplate="%{percent:.1%}",
        insidetextfont=dict(size=13, color="white"),
        hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
    )
    figure.update_layout(
        template="plotly_white", separators=",.", height=520,
        margin=dict(l=8, r=8, t=12, b=8), showlegend=True,
        legend=dict(orientation="h", y=-0.08, yanchor="top", x=0.5, xanchor="center",
                    font=dict(size=12, color=NAVY)),
        font=dict(color=NAVY, family="Arial, sans-serif", size=12),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return figure


def render() -> None:
    simulation = carregar_simulacao()
    occurrences, quality_of_life = carregar_peers()
    available_levels = sorted(simulation["level_m"].unique())

    st.markdown(
        "<div style='font-size:12px;letter-spacing:.16em;font-weight:700;color:#60728a;'>"
        "IMPACTOS SOCIAIS E INFRAESTRUTURA</div>",
        unsafe_allow_html=True,
    )
    heading, source = st.columns([3, 1])
    with heading:
        st.title("Análise Contextual e Externa")
        st.caption("Enchentes de maio de 2024 · Região de Porto Alegre")
    with source:
        st.markdown(
            "<div style='text-align:right;padding-top:20px;font-size:12px;color:#586b82;white-space:nowrap;'>"
            "<span style='color:#159a9c;'>●</span> &nbsp; BASES COMPLEMENTARES "
            "&nbsp; <b style='color:#34445a;'>IBGE / PEERS</b></div>",
            unsafe_allow_html=True,
        )

    controls, dimension = st.columns([1.2, 1])
    with controls:
        with st.container(border=True):
            label, value = st.columns([3, 1])
            with label:
                st.markdown("**CENÁRIO COMPARTILHADO**")
                st.markdown("**Nível do Guaíba**")
            with value:
                st.markdown(
                    "<div style='text-align:right;font-size:22px;font-weight:700;color:#159a9c;'>"
                    f"{format_level(nivel_atual())} "
                    "<span style='font-size:13px;color:#71829b;font-weight:400;'>m</span></div>",
                    unsafe_allow_html=True,
                )
            selected_level = slider_nivel("slider_tela_2", available_levels[0], available_levels[-1])
            st.markdown(
                "<div style='display:flex;justify-content:space-between;font-size:13px;"
                "color:#586b82;margin-top:-8px;'>"
                f"<span>{format_level(available_levels[0])} m</span>"
                "<span>Referência de maio/2024: 5,35 m</span>"
                f"<span>{format_level(available_levels[-1])} m</span></div>",
                unsafe_allow_html=True,
            )

    with dimension:
        with st.container(border=True):
            st.markdown("**INDICADOR DE ANÁLISE**")
            st.subheader("Dimensão observada")
            selected_metric = st.selectbox(
                "Dimensão", options=list(METRICS), index=0,
                key="dimensao_tela_2", label_visibility="collapsed",
            )
            st.caption("Indicadores calculados a partir das bases carregadas.")

    level_key = min(available_levels, key=lambda lv: abs(lv - selected_level))
    current_level = simulation[simulation["level_m"] == level_key]
    metric = METRICS[selected_metric]
    cfg = {"displayModeBar": False}

    territorial, evolution = st.columns(2)
    with territorial:
        with st.container(border=True):
            st.markdown("**VULNERABILIDADE TERRITORIAL**")
            st.markdown("Exposição por bairro")
            st.plotly_chart(make_exposure_chart(current_level, metric, selected_metric),
                            use_container_width=True, config=cfg)
    with evolution:
        with st.container(border=True):
            st.markdown("**EVOLUÇÃO DA EXPOSIÇÃO**")
            st.markdown("Bairros e prédios afetados")
            st.plotly_chart(make_evolution_chart(simulation, metric, selected_metric, level_key),
                            use_container_width=True, config=cfg)

    household_impacts, residents = st.columns(2)
    with household_impacts:
        with st.container(border=True):
            st.markdown("**IMPACTOS NOS DOMICÍLIOS · PEERS / IBGE**")
            st.markdown("Ocorrências reportadas")
            st.plotly_chart(make_occurrences_chart(occurrences),
                            use_container_width=True, config=cfg)
    with residents:
        with st.container(border=True):
            st.markdown("**PERCEPÇÃO DOS MORADORES · PEERS / IBGE**")
            st.markdown("Qualidade de vida após as enchentes")
            st.plotly_chart(make_quality_chart(quality_of_life),
                            use_container_width=True, config=cfg)

    st.markdown(
        f"""
        <div style="background:#eaf0f6;border:1px dashed #c5d1df;border-radius:10px;
        padding:14px 18px;display:flex;justify-content:space-between;align-items:center;
        color:#34445a;">
          <div><div style="font-size:12px;letter-spacing:.14em;font-weight:700;color:#60728a;">
          COBERTURA DA SIMULAÇÃO</div>
          <div style="font-weight:600;margin-top:4px;">Registros disponíveis na base INCT</div>
          <div style="font-size:13px;color:#586b82;margin-top:3px;">
          Linhas processadas para {simulation["level_m"].nunique()} níveis do rio e
          {simulation["neighborhood"].nunique()} bairros de Porto Alegre.</div></div>
          <div style="background:#fff;border:1px solid #dce4ee;border-radius:8px;
          padding:8px 18px;text-align:center;color:#159a9c;font-size:18px;font-weight:700;">
          {format_number(len(simulation))}
          <div style="font-size:11px;letter-spacing:.12em;color:#586b82;">REGISTROS</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    footer_left, footer_date, footer_page = st.columns([2, 2, 1])
    with footer_left:
        st.caption("Fontes: INCT SIMAI · IBGE — Pesquisa PEERS")
    with footer_date:
        st.caption("Data de referência: maio de 2024")
    with footer_page:
        st.markdown(
            "<div style='text-align:right;font-size:11px;color:#8294ad;padding-top:8px;'>"
            "Tela 02 / 02</div>",
            unsafe_allow_html=True,
        )