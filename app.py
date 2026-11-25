import streamlit as st

st.set_page_config(
    page_title="Monitor de Enchentes",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from dashboards import tela_1_simulacao, tela_2_contexto
from dashboards.comum import inicializar_nivel

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] { background: #f3f6fa; color: #26364a !important; }
    [data-testid="stSidebar"] { background: #172a40; }
    [data-testid="stSidebar"] * { color: #e7eef7; }
    [data-testid="stAppViewContainer"] h1,
    [data-testid="stAppViewContainer"] h2,
    [data-testid="stAppViewContainer"] h3 { color: #1d2b40 !important; }
    [data-testid="stAppViewContainer"] h1 { font-size: 2rem; letter-spacing: -0.035em; }
    [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] p {
        color: #34445a !important; font-size: 15px; }
    [data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] {
        color: #586b82 !important; font-size: 13px !important; }
    [data-testid="stAppViewContainer"] label { color: #34445a !important; font-size: 14px !important; }
    [data-testid="stAppViewContainer"] [data-baseweb="select"] > div {
        background: #ffffff !important; border-color: #bdc9d8 !important; color: #24354b !important; }
    [data-testid="stAppViewContainer"] [data-baseweb="select"] input { color: #24354b !important; }
    [data-baseweb="popover"] { background: #ffffff !important; }
    [data-baseweb="popover"] li[role="option"] { color: #24354b !important; font-size: 14px; }
    .stMainBlockContainer { max-width: 1600px; padding-top: 1.6rem; padding-bottom: 1rem; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff; border: 1px solid #dce4ee; border-radius: 12px; }
    [data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 12px; }
    [data-testid="stSlider"] [role="slider"] { background: #159a9c; }

    /* navegação da barra lateral (st.radio estilizado como menu) */
    [data-testid="stSidebar"] [role="radiogroup"] { gap: 6px; }
    [data-testid="stSidebar"] [role="radiogroup"] label {
        padding: 12px 16px; border-radius: 8px; width: 100%;
        border-left: 3px solid transparent; cursor: pointer; }
    [data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display: none; }
    [data-testid="stSidebar"] [role="radiogroup"] label p {
        font-size: 16px !important; color: #e7eef7 !important; }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
        background: #21405b; border-left-color: #20bdba; font-weight: 600; }
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

PAGINAS = {
    "▦  Simulação INCT": tela_1_simulacao.render,
    "◉  Contexto externo": tela_2_contexto.render,
}

inicializar_nivel()

with st.sidebar:
    st.markdown(
        """
        <div style="width:52px;height:52px;border-radius:14px;background:#159a9c;
        display:flex;align-items:center;justify-content:center;font-weight:700;font-size:21px;">
        ÁG</div>
        <div style="font-size:19px;font-weight:700;margin-top:14px;letter-spacing:.04em;">MONITOR</div>
        <div style="font-size:14px;font-weight:700;letter-spacing:.18em;color:#b4c3d5;">ENCHENTES</div>
        <div style="margin:38px 0 12px;font-size:13px;font-weight:700;letter-spacing:.16em;
        color:#b4c3d5;">PAINEL</div>
        """,
        unsafe_allow_html=True,
    )
    pagina = st.radio("Painel", list(PAGINAS), key="pagina", label_visibility="collapsed")
    st.markdown(
        """
        <div style="position:fixed;bottom:30px;font-size:14px;line-height:1.8;color:#b4c3d5;">
        <b style="font-size:13px;letter-spacing:.15em;">PROJETO</b><br>Projeto Extensionista<br>
        Fase 2 · Porto Alegre</div>
        """,
        unsafe_allow_html=True,
    )

PAGINAS[pagina]()