import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboards.comum import (
    NIVEL_REFERENCIA,
    NAVY,
    TEAL,
    carregar_simulacao,
    format_level,
    format_number,
    nivel_atual,
    slider_nivel,
)

FONTE = dict(color=NAVY, family="Arial, sans-serif", size=13)


def _kpi(titulo: str, valor: int, legenda: str, icone: str, cor_fundo: str) -> str:
    return f"""
    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
      <div style="font-size:12px;letter-spacing:.12em;font-weight:700;color:#60728a;">{titulo}</div>
      <div style="background:{cor_fundo};border-radius:8px;padding:4px 8px;font-size:14px;">{icone}</div>
    </div>
    <div style="font-size:32px;font-weight:700;color:#1d2b40;margin-top:6px;">{format_number(valor)}</div>
    <div style="font-size:12px;color:#586b82;margin-top:2px;">{legenda}</div>
    """


def _fig_percentual(bairros, nivel: float):
    fig = px.bar(
        bairros.sort_values("percentage", ascending=True),
        x="percentage",
        y="neighborhood",
        orientation="h",
        color="percentage",
        color_continuous_scale=[[0, "#d9f0ee"], [1, "#079c99"]],
        range_color=(0, 100),
        hover_data={"affected_buildings": True, "total_buildings": True, "percentage": ":.1f"},
        labels={
            "percentage": "% de prédios afetados",
            "neighborhood": "Bairro",
            "affected_buildings": "Prédios afetados",
            "total_buildings": "Prédios na base",
        },
    )
    fig.update_layout(
        template="plotly_white",
        separators=",.",
        font=FONTE,
        height=max(360, 24 * len(bairros) + 60),
        coloraxis_showscale=False,
        margin=dict(l=4, r=15, t=10, b=35),
        yaxis_title=None,
        xaxis=dict(range=[0, 100], ticksuffix="%", gridcolor="#dce4ee"),
    )
    return fig


def _fig_ranking(bairros):
    ranking = bairros.nlargest(10, "affected_buildings").sort_values("affected_buildings")
    fig = px.bar(
        ranking,
        x="affected_buildings",
        y="neighborhood",
        orientation="h",
        text="affected_buildings",
        color_discrete_sequence=[TEAL],
        labels={"affected_buildings": "Prédios afetados", "neighborhood": "Bairro"},
    )
    fig.update_traces(
        texttemplate="%{x:,.0f}", textposition="outside", cliponaxis=False
    )
    fig.update_layout(
        template="plotly_white",
        separators=",.",
        font=FONTE,
        height=340,
        margin=dict(l=4, r=40, t=10, b=30),
        yaxis_title=None,
        xaxis=dict(gridcolor="#dce4ee"),
        showlegend=False,
    )
    return fig


def _fig_populacao(por_nivel, nivel: float):
    valor = int(
        por_nivel.loc[np.isclose(por_nivel["level_m"], nivel), "affected_population"].iloc[0]
    )
    fig = px.line(
        por_nivel,
        x="level_m",
        y="affected_population",
        labels={"level_m": "Nível do rio (m)", "affected_population": "População afetada"},
    )
    fig.update_traces(line_color=TEAL, line_width=3, name="População estimada")
    fig.add_vline(
        x=NIVEL_REFERENCIA,
        line_dash="dash",
        line_color="#d64b45",
        annotation_text="Recorde maio/2024 — 5,35 m",
        annotation_position="top left",
    )
    fig.add_trace(
        go.Scatter(
            x=[nivel],
            y=[valor],
            mode="markers",
            name=f"Selecionado: {format_level(nivel)} m",
            marker=dict(size=13, color="#f0a43c", line=dict(color="white", width=2)),
            hovertemplate="Nível %{x:.1f} m<br>%{y:,.0f} pessoas<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_white",
        separators=",.",
        font=FONTE,
        height=340,
        margin=dict(l=8, r=8, t=30, b=30),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center"),
    )
    return fig


def render() -> None:
    simulacao = carregar_simulacao()
    niveis = sorted(simulacao["level_m"].unique())

    st.markdown(
        "<div style='font-size:12px;letter-spacing:.16em;font-weight:700;color:#60728a;'>"
        "MONITORAMENTO DE CHEIAS · PORTO ALEGRE</div>",
        unsafe_allow_html=True,
    )
    titulo, fonte = st.columns([3, 1])
    with titulo:
        st.title("Dashboard de Alagamentos")
        st.caption("Simulação de impactos por nível do Guaíba")
    with fonte:
        st.markdown(
            "<div style='text-align:right;padding-top:20px;font-size:12px;color:#586b82;white-space:nowrap;'>"
            "<span style='color:#159a9c;'>●</span> &nbsp; DADOS DE SIMULAÇÃO "
            "&nbsp; <b style='color:#34445a;'>INCT SIMAI</b></div>",
            unsafe_allow_html=True,
        )

    
    with st.container(border=True):
        rotulo, valor = st.columns([3, 1])
        with rotulo:
            st.markdown("**FILTRO PRINCIPAL**")
            st.markdown("**Nível do Guaíba**")
        with valor:
            st.markdown(
                "<div style='text-align:right;font-size:26px;font-weight:700;color:#159a9c;'>"
                f"{format_level(nivel_atual())} "
                "<span style='font-size:13px;color:#71829b;font-weight:400;'>metros</span></div>",
                unsafe_allow_html=True,
            )
        selecionado = slider_nivel("slider_tela_1", niveis[0], niveis[-1])
        st.markdown(
            "<div style='display:flex;justify-content:space-between;font-size:13px;"
            "color:#586b82;margin-top:-8px;'>"
            f"<span>{format_level(niveis[0])} m</span>"
            "<span>5,35 m · recorde de maio/2024</span>"
            f"<span>{format_level(niveis[-1])} m</span></div>",
            unsafe_allow_html=True,
        )

    nivel = min(niveis, key=lambda n: abs(n - selecionado))
    dados_nivel = simulacao[np.isclose(simulacao["level_m"], nivel)]
    atingidos = dados_nivel[dados_nivel["affected_buildings"] > 0]

    pessoas = int(dados_nivel["affected_population"].sum())
    predios = int(dados_nivel["affected_buildings"].sum())
    n_bairros = int(atingidos["neighborhood"].nunique())

    k1, k2, k3 = st.columns(3)
    with k1:
        with st.container(border=True):
            st.markdown(
                _kpi("PESSOAS AFETADAS", pessoas, "Estimativa no nível selecionado", "👤", "#fdeceb"),
                unsafe_allow_html=True,
            )
    with k2:
        with st.container(border=True):
            st.markdown(
                _kpi("PRÉDIOS AFETADOS", predios, "Estimativa no nível selecionado", "🏢", "#fff3df"),
                unsafe_allow_html=True,
            )
    with k3:
        with st.container(border=True):
            st.markdown(
                _kpi("BAIRROS ATINGIDOS", n_bairros, "Com registros de edifícios afetados", "📍", "#e8f0fc"),
                unsafe_allow_html=True,
            )

    esquerda, direita = st.columns(2)
    with esquerda:
        with st.container(border=True):
            st.markdown("**DISTRIBUIÇÃO TERRITORIAL**")
            st.markdown("Prédios afetados por bairro (%)")
            if atingidos.empty:
                st.info("Nenhum bairro com prédios afetados neste nível.")
            else:
                st.plotly_chart(
                    _fig_percentual(atingidos, nivel),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )
    with direita:
        with st.container(border=True):
            st.markdown("**MAIOR IMPACTO**")
            st.markdown("Top 10 bairros afetados (volume)")
            if atingidos.empty:
                st.info("Nenhum bairro com prédios afetados neste nível.")
            else:
                st.plotly_chart(
                    _fig_ranking(atingidos),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )
        with st.container(border=True):
            st.markdown("**EVOLUÇÃO DO IMPACTO**")
            st.markdown("População afetada por nível")
            por_nivel = (
                simulacao.groupby("level_m", as_index=False)["affected_population"].sum()
            )
            st.plotly_chart(
                _fig_populacao(por_nivel, nivel),
                use_container_width=True,
                config={"displayModeBar": False},
            )

    f1, f2 = st.columns([4, 1])
    with f1:
        st.caption(
            "Fonte: INCT SIMAI · Base tratada pela equipe. Valores estimados a partir da base "
            "processada; não são dados em tempo real nem alerta oficial."
        )
    with f2:
        st.markdown(
            "<div style='text-align:right;font-size:11px;color:#8294ad;padding-top:8px;'>"
            "Tela 01 / 02</div>",
            unsafe_allow_html=True,
        )