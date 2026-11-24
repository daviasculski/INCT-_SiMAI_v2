from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


ROOT = Path(__file__).resolve().parent
SIMULATION_FILE = ROOT / "dados" / "processados" / "data_atualizado.json"
OCCURRENCES_FILE = ROOT / "dados" / "originais" / "Tabela22.4.xlsx"
QUALITY_OF_LIFE_FILE = ROOT / "dados" / "originais" / "Tabela22.6.xlsx"
TEAL = "#159a9c"
NAVY = "#172a40"
MUTED = "#71829b"

METRICS = {
    "Prédios afetados": {
        "column": "affected_buildings",
        "axis": "Prédios afetados",
        "format": "number",
    },
    "População afetada": {
        "column": "affected_population",
        "axis": "Pessoas afetadas",
        "format": "number",
    },
    "Percentual de prédios": {
        "column": "percentage",
        "axis": "Prédios afetados (%)",
        "format": "percent",
    },
}


@st.cache_data
def load_dashboard_data():
    simulation = pd.read_json(SIMULATION_FILE)
    if simulation.empty:
        raise ValueError(f"A base de simulação está vazia: {SIMULATION_FILE}")

    simulation_rows = []
    for level, neighborhoods in simulation.to_dict().items():
        level_m = float(level.removesuffix("m").replace("_", "."))
        for neighborhood, values in neighborhoods.items():
            simulation_rows.append(
                {"level_m": level_m, "neighborhood": neighborhood, **values}
            )
    simulation_frame = pd.DataFrame(simulation_rows)

    occurrences = load_peers_section(
        OCCURRENCES_FILE, "Tipos de ocorrências causadas pelas enchentes no domicílio"
    )
    quality_of_life = load_peers_section(QUALITY_OF_LIFE_FILE, "Avaliação da vida em geral")
    return simulation_frame, occurrences, quality_of_life


def load_peers_section(path: Path, section_name: str) -> pd.DataFrame:
    source = pd.read_excel(path, skiprows=4, header=None)
    section_rows = source.iloc[:, 0].astype("string").str.strip().eq(section_name)
    matches = source.index[section_rows].tolist()
    if not matches:
        raise ValueError(f"A seção '{section_name}' não foi encontrada em {path.name}.")

    records = []
    for _, row in source.iloc[matches[0] + 1 :].iterrows():
        label = row.iloc[0]
        total = row.iloc[1]
        percentage = row.iloc[2]
        if pd.isna(label) or pd.isna(percentage):
            break
        records.append(
            {
                "label": str(label).strip(),
                "total": float(total),
                "percentage": float(percentage),
            }
        )
    if not records:
        raise ValueError(f"A seção '{section_name}' não contém dados em {path.name}.")
    return pd.DataFrame(records)


def format_number(value: float) -> str:
    return f"{value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_level(level: float) -> str:
    return f"{level:.1f}".replace(".", ",")


def make_exposure_chart(
    current_level: pd.DataFrame, metric: dict, selected_metric: str
) -> go.Figure:
    column = metric["column"]
    top_neighborhoods = current_level.nlargest(10, column).sort_values(column)
    figure = px.bar(
        top_neighborhoods,
        x=column,
        y="neighborhood",
        orientation="h",
        text=column,
        color_discrete_sequence=[TEAL],
    )
    text_template = "%{x:.1f}%" if metric["format"] == "percent" else "%{x:,.0f}"
    figure.update_traces(
        texttemplate=text_template,
        textposition="outside",
        cliponaxis=False,
        textfont=dict(size=12, color=NAVY),
        hovertemplate="%{y}<br>" + metric["axis"] + ": %{x:,.1f}<extra></extra>",
    )
    figure.update_layout(
        template="plotly_white",
        height=350,
        margin=dict(l=4, r=28, t=12, b=8),
        yaxis_title=None,
        showlegend=False,
        font=dict(color=NAVY, family="Arial, sans-serif", size=13),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            showgrid=True,
            gridcolor="#dce4ee",
            zeroline=False,
            tickfont=dict(size=12, color=NAVY),
            title=dict(text=metric["axis"], font=dict(size=12, color=NAVY)),
        ),
        yaxis=dict(
            showgrid=False,
            automargin=True,
            tickfont=dict(size=12, color=NAVY),
        ),
        title=dict(
            text=f"10 bairros com maior {selected_metric.lower()}",
            font=dict(size=16, color=NAVY),
        ),
    )
    if metric["format"] == "percent":
        figure.update_xaxes(ticksuffix="%")
    return figure


def make_evolution_chart(
    simulation: pd.DataFrame,
    metric: dict,
    selected_metric: str,
    current_level: float,
) -> go.Figure:
    column = metric["column"]
    by_level = simulation.groupby("level_m", as_index=False).agg(
        affected_value=(column, "sum"),
        affected_buildings=("affected_buildings", "sum"),
        total_buildings=("total_buildings", "sum"),
        affected_neighborhoods=("affected_buildings", lambda values: (values > 0).sum()),
    )
    if metric["format"] == "percent":
        by_level["affected_value"] = (
            by_level["affected_buildings"] / by_level["total_buildings"] * 100
        )

    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(
        go.Scatter(
            x=by_level["level_m"],
            y=by_level["affected_value"],
            mode="lines",
            name=selected_metric,
            line=dict(color=TEAL, width=3),
            fill="tozeroy",
            fillcolor="rgba(21, 154, 156, 0.12)",
            hovertemplate="Nível %{x:.1f} m<br>%{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(
            x=by_level["level_m"],
            y=by_level["affected_neighborhoods"],
            mode="lines",
            name="Bairros atingidos",
            line=dict(color="#b96b00", width=2, dash="dot"),
            hovertemplate="Nível %{x:.1f} m<br>%{y} bairros<extra></extra>",
        ),
        secondary_y=True,
    )
    figure.add_vline(x=current_level, line_dash="dash", line_color="#e66f62")
    figure.update_layout(
        template="plotly_white",
        height=350,
        margin=dict(l=8, r=8, t=12, b=8),
        legend=dict(
            orientation="h",
            y=1.15,
            x=0,
            font=dict(size=12, color=NAVY),
        ),
        font=dict(color=NAVY, family="Arial, sans-serif", size=13),
        plot_bgcolor="white",
        paper_bgcolor="white",
        title=dict(
            text=f"Evolução: {selected_metric.lower()} e bairros atingidos",
            font=dict(size=16, color=NAVY),
        ),
    )
    figure.update_xaxes(
        title=dict(text="Nível do Guaíba (m)", font=dict(size=12, color=NAVY)),
        gridcolor="#dce4ee",
        tickfont=dict(size=12, color=NAVY),
    )
    figure.update_yaxes(
        title=dict(text=metric["axis"], font=dict(size=12, color=NAVY)),
        secondary_y=False,
        gridcolor="#dce4ee",
        tickfont=dict(size=12, color=NAVY),
    )
    figure.update_yaxes(
        title=dict(text="Bairros", font=dict(size=12, color=NAVY)),
        secondary_y=True,
        showgrid=False,
        tickfont=dict(size=12, color=NAVY),
    )
    return figure


def make_occurrences_chart(occurrences: pd.DataFrame) -> go.Figure:
    ordered = occurrences.sort_values("percentage")
    figure = px.bar(
        ordered,
        x="percentage",
        y="label",
        orientation="h",
        text="percentage",
        color_discrete_sequence=["#557f9d"],
    )
    figure.update_traces(
        texttemplate="%{x:.1f}%",
        textposition="outside",
        cliponaxis=False,
        textfont=dict(size=12, color=NAVY),
        hovertemplate="%{y}<br>%{x:.1f}% dos domicílios<extra></extra>",
    )
    figure.update_layout(
        template="plotly_white",
        height=340,
        margin=dict(l=4, r=30, t=12, b=8),
        yaxis_title=None,
        showlegend=False,
        font=dict(color=NAVY, family="Arial, sans-serif", size=12),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            range=[0, 100],
            showgrid=True,
            gridcolor="#dce4ee",
            tickfont=dict(size=12, color=NAVY),
            title=dict(text="Domicílios (%)", font=dict(size=12, color=NAVY)),
        ),
        yaxis=dict(
            showgrid=False,
            automargin=True,
            tickfont=dict(size=12, color=NAVY),
        ),
    )
    return figure


def make_quality_chart(quality_of_life: pd.DataFrame) -> go.Figure:
    colors = {
        "Pior que antes das enchentes": "#e66f62",
        "Igual a antes das enchentes": "#7890ac",
        "Melhor que antes das enchentes": TEAL,
    }
    figure = px.pie(
        quality_of_life,
        values="percentage",
        names="label",
        hole=0.62,
        color="label",
        color_discrete_map=colors,
    )
    figure.update_traces(
        textposition="outside",
        texttemplate="%{label}<br>%{percent:.1%}",
        textfont=dict(size=12, color=NAVY),
        hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
    )
    figure.update_layout(
        template="plotly_white",
        height=340,
        margin=dict(l=8, r=8, t=12, b=8),
        showlegend=False,
        font=dict(color=NAVY, family="Arial, sans-serif", size=12),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return figure


st.set_page_config(
    page_title="Contexto externo | Monitor de Enchentes",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background: #f3f6fa;
        color: #26364a !important;
    }
    [data-testid="stSidebar"] { background: #172a40; }
    [data-testid="stSidebar"] * { color: #e7eef7; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #b4c3d5 !important;
        font-size: 12px;
    }
    [data-testid="stAppViewContainer"] h1,
    [data-testid="stAppViewContainer"] h2,
    [data-testid="stAppViewContainer"] h3 {
        color: #1d2b40 !important;
    }
    [data-testid="stAppViewContainer"] h1 {
        font-size: 2rem;
        letter-spacing: -0.035em;
    }
    [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] p {
        color: #34445a !important;
        font-size: 15px;
    }
    [data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] {
        color: #586b82 !important;
        font-size: 13px !important;
    }
    [data-testid="stAppViewContainer"] label {
        color: #34445a !important;
        font-size: 14px !important;
    }
    [data-testid="stAppViewContainer"] [data-baseweb="select"] > div {
        background: #ffffff !important;
        border-color: #bdc9d8 !important;
        color: #24354b !important;
    }
    [data-testid="stAppViewContainer"] [data-baseweb="select"] input {
        color: #24354b !important;
    }
    [data-baseweb="popover"] {
        background: #ffffff !important;
    }
    [data-baseweb="popover"] li[role="option"] {
        color: #24354b !important;
        font-size: 14px;
    }
    .stMainBlockContainer { max-width: 1600px; padding-top: 1.6rem; padding-bottom: 1rem; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff; border: 1px solid #dce4ee; border-radius: 12px;
    }
    [data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 12px; }
    [data-testid="stMetricValue"] { color: #159a9c; }
    [data-testid="stSlider"] [role="slider"] { background: #159a9c; }
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        """
        <div style="width:40px;height:40px;border-radius:12px;background:#159a9c;
        display:flex;align-items:center;justify-content:center;font-weight:700;font-size:17px;">
        ÁG</div>
        <div style="font-size:14px;font-weight:700;margin-top:12px;letter-spacing:.04em;">
        MONITOR</div>
        <div style="font-size:11px;font-weight:700;letter-spacing:.18em;color:#b4c3d5;">
        ENCHENTES</div>
        <div style="margin-top:34px;font-size:11px;font-weight:700;letter-spacing:.16em;
        color:#b4c3d5;">PAINEL</div>
        <div style="margin-top:12px;padding:12px;border-radius:8px;background:#21405b;
        border-left:3px solid #20bdba;font-size:13px;font-weight:600;">
        ◉ &nbsp; Contexto externo</div>
        <div style="position:fixed;bottom:30px;font-size:11px;line-height:1.9;color:#b4c3d5;">
        <b style="letter-spacing:.15em;">PROJETO</b><br>Projeto Extensionista<br>
        Fase 2 · Porto Alegre</div>
        """,
        unsafe_allow_html=True,
    )

simulation, occurrences, quality_of_life = load_dashboard_data()
available_levels = sorted(simulation["level_m"].unique())

st.markdown(
    """
    <div style="font-size:12px;letter-spacing:.16em;font-weight:700;color:#60728a;">
    IMPACTOS SOCIAIS E INFRAESTRUTURA</div>
    """,
    unsafe_allow_html=True,
)
heading, source = st.columns([4, 1])
with heading:
    st.title("Análise Contextual e Externa")
    st.caption("Enchentes de maio de 2024 · Região de Porto Alegre")
with source:
    st.markdown(
        "<div style='text-align:right;padding-top:20px;font-size:12px;color:#586b82;'>"
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
                "5,3 <span style='font-size:11px;color:#71829b;font-weight:400;'>m</span></div>",
                unsafe_allow_html=True,
            )
        selected_level = st.slider(
            "Nível do rio (m)",
            min_value=float(available_levels[0]),
            max_value=float(available_levels[-1]),
            value=5.3 if 5.3 in available_levels else float(available_levels[0]),
            step=0.1,
            label_visibility="collapsed",
        )
        st.caption(
            f"{format_level(available_levels[0])} m"
            f"　　Referência de maio/2024: 5,35 m"
            f"　　{format_level(available_levels[-1])} m"
        )

with dimension:
    with st.container(border=True):
        st.markdown("**INDICADOR DE ANÁLISE**")
        st.subheader("Dimensão observada")
        selected_metric = st.selectbox(
            "Dimensão",
            options=list(METRICS),
            index=0,
            label_visibility="collapsed",
        )
        st.caption("Indicadores calculados a partir das bases carregadas.")

level_key = min(available_levels, key=lambda level: abs(level - selected_level))
current_level = simulation[simulation["level_m"] == level_key]
metric = METRICS[selected_metric]

territorial, evolution = st.columns([1, 1])
with territorial:
    with st.container(border=True):
        st.markdown("**VULNERABILIDADE TERRITORIAL**")
        st.markdown("Exposição por bairro")
        st.plotly_chart(
            make_exposure_chart(current_level, metric, selected_metric),
            use_container_width=True,
            config={"displayModeBar": False},
        )
with evolution:
    with st.container(border=True):
        st.markdown("**EVOLUÇÃO DA EXPOSIÇÃO**")
        st.markdown("Bairros e prédios afetados")
        st.plotly_chart(
            make_evolution_chart(simulation, metric, selected_metric, level_key),
            use_container_width=True,
            config={"displayModeBar": False},
        )

household_impacts, residents = st.columns([1, 1])
with household_impacts:
    with st.container(border=True):
        st.markdown("**IMPACTOS NOS DOMICÍLIOS · PEERS / IBGE**")
        st.markdown("Ocorrências reportadas")
        st.plotly_chart(
            make_occurrences_chart(occurrences),
            use_container_width=True,
            config={"displayModeBar": False},
        )
with residents:
    with st.container(border=True):
        st.markdown("**PERCEPÇÃO DOS MORADORES · PEERS / IBGE**")
        st.markdown("Qualidade de vida após as enchentes")
        st.plotly_chart(
            make_quality_chart(quality_of_life),
            use_container_width=True,
            config={"displayModeBar": False},
        )

record_count = len(simulation)
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
      {format_number(record_count)}
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