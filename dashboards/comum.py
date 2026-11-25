import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
SIMULATION_FILE = ROOT / "dados" / "processados" / "data_atualizado.json"
OCCURRENCES_FILE = ROOT / "dados" / "originais" / "Tabela22.4.xlsx"
QUALITY_OF_LIFE_FILE = ROOT / "dados" / "originais" / "Tabela22.6.xlsx"

TEAL = "#159a9c"
NAVY = "#172a40"
MUTED = "#71829b"
NIVEL_REFERENCIA = 5.35
NIVEL_PADRAO = 5.3


@st.cache_data
def carregar_simulacao() -> pd.DataFrame:
    with SIMULATION_FILE.open(encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    linhas = [
        {
            "level_m": float(nivel.removesuffix("m").replace("_", ".")),
            "neighborhood": bairro,
            **valores,
        }
        for nivel, bairros in dados.items()
        for bairro, valores in bairros.items()
    ]
    frame = pd.DataFrame(linhas)
    if frame.empty:
        raise ValueError(f"A base de simulação está vazia: {SIMULATION_FILE}")
    return frame


def _carregar_secao_peers(path: Path, section_name: str) -> pd.DataFrame:
    source = pd.read_excel(path, skiprows=4, header=None)
    section_rows = source.iloc[:, 0].astype("string").str.strip().eq(section_name)
    matches = source.index[section_rows].tolist()
    if not matches:
        raise ValueError(f"A seção '{section_name}' não foi encontrada em {path.name}.")

    records = []
    for _, row in source.iloc[matches[0] + 1 :].iterrows():
        label, total, percentage = row.iloc[0], row.iloc[1], row.iloc[2]
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


@st.cache_data
def carregar_peers() -> tuple[pd.DataFrame, pd.DataFrame]:
    ocorrencias = _carregar_secao_peers(
        OCCURRENCES_FILE, "Tipos de ocorrências causadas pelas enchentes no domicílio"
    )
    qualidade = _carregar_secao_peers(QUALITY_OF_LIFE_FILE, "Avaliação da vida em geral")
    return ocorrencias, qualidade


def format_number(value: float) -> str:
    return f"{value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_level(level: float) -> str:
    return f"{level:.1f}".replace(".", ",")


def inicializar_nivel() -> None:
    if "nivel_guaiba" not in st.session_state:
        st.session_state["nivel_guaiba"] = NIVEL_PADRAO


def nivel_atual() -> float:
    return float(st.session_state["nivel_guaiba"])


def _sincronizar(chave: str) -> None:
    st.session_state["nivel_guaiba"] = round(float(st.session_state[chave]), 1)


def slider_nivel(chave: str, minimo: float, maximo: float) -> float:
    """Slider de cada tela. O valor 'oficial' fica em session_state['nivel_guaiba'],
    então trocar de tela mantém o cenário escolhido."""
    return st.slider(
        "Nível do rio (m)",
        min_value=float(minimo),
        max_value=float(maximo),
        value=nivel_atual(),
        step=0.1,
        key=chave,
        on_change=_sincronizar,
        args=(chave,),
        label_visibility="collapsed",
    )