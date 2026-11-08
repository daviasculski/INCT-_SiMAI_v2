import re
import sys
from pathlib import Path

import openpyxl
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "dados" / "originais" / "peers"
SAIDA = RAIZ / "dados" / "processados" / "peers_longo.csv"

REGEX_NOTA = re.compile(r"^(fonte|nota|\(\d+\)|\*)", re.I)
REGEX_MARCA = re.compile(r"(\s*\(\d+\))+\s*$")
REGEX_TABELA = re.compile(r"^(?:Tabela|Tab)\s*([\d.]+)_INDICADOR$")


def limpar_texto(v):
    # Normaliza espaços/quebras e remove marcas de nota: "Total (1)(2)" -> "Total"
    if v is None:
        return None
    s = re.sub(r"\s+", " ", str(v)).strip()
    s = REGEX_MARCA.sub("", s)
    s = s.replace(", )", ")").rstrip(":.").strip()
    return s or None


def e_numero(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def tipo_medida(rotulo):
    if rotulo is None:
        return None
    r = rotulo.lower()
    if "%" in r:
        return "percentual"
    if r == "total":
        return "total"
    return None


def faixa_cv(cv):
    # Faixas a partir da nota do IBGE: "faixa C, mais de 15% até 30%"
    if pd.isna(cv):
        return None
    if cv <= 15:
        return "até 15%"
    if cv <= 30:
        return "15% a 30%"
    return "acima de 30%"


def identificar_escopo(titulo):
    m = re.search(r"Regi[ãa]o [Ii]ntermedi[áa]ria de (.+?) - ", titulo)
    if m:
        return "regiao_intermediaria", m.group(1).strip()
    if "Área de abrangência" in titulo:
        return "area_total", "Área total da pesquisa (RS)"
    return "desconhecido", None


def ler_folha(ws):
    # Guarda valores e recuo (indent) da coluna A, que carrega a hierarquia das linhas
    linhas = []
    for row in ws.iter_rows():
        linhas.append(([c.value for c in row], int(row[0].alignment.indent or 0)))
    return linhas


def nivel_linha(bruto, indent):
    # O IBGE marca a hierarquia com o recuo da célula e com espaços no começo do texto
    # (1 espaço solto é ruído, então conta de 4 em 4)
    texto = str(bruto)
    espacos = len(texto) - len(texto.lstrip())
    return indent + 2 * (espacos // 4)


def alinhar_linhas(linhas, linhas_cv):
    # Pareia INDICADOR e CV pela ordem das linhas com rótulo, ignorando linhas em branco extras
    a = [i for i, (v, _) in enumerate(linhas) if v[0] is not None]
    b = [i for i, (v, _) in enumerate(linhas_cv) if v[0] is not None]
    return dict(zip(a, b))


def achar_inicio_dados(linhas):
    # Primeira linha (após o título) com número fora da coluna A; antes dela é cabeçalho
    for i in range(1, len(linhas)):
        if any(e_numero(v) for v in linhas[i][0][1:]):
            return i
    return None


def montar_colunas(cab, ncols):
    # Cabeçalho em vários níveis: repete rótulos mesclados para a direita (menos no último nível)
    niveis = []
    for k, (linha, _) in enumerate(cab):
        v = [limpar_texto(x) for x in linha] + [None] * (ncols - len(linha))
        if k < len(cab) - 1:
            for j in range(1, ncols):
                if v[j] is None and v[j - 1] is not None and j > 1:
                    v[j] = v[j - 1]
        niveis.append(v)
    colunas = {}
    for j in range(1, ncols):
        caminho = [niveis[k][j] for k in range(1, len(niveis)) if niveis[k][j]]
        medida = tipo_medida(caminho[-1]) if caminho else None
        if medida:
            caminho = caminho[:-1]
        else:
            medida = "total"  # tabelas de valor único não trazem linha de medida
        colunas[j] = (medida, " > ".join(caminho))
    return colunas


def processar_arquivo(arq, avisos):
    wb = openpyxl.load_workbook(arq, data_only=True)
    ind = [n for n in wb.sheetnames if n.endswith("_INDICADOR")]
    cvs = [n for n in wb.sheetnames if n.endswith("_CV")]
    if len(ind) != 1 or len(cvs) != 1:
        avisos.append(f"{arq.name}: abas inesperadas {wb.sheetnames}")
        return []
    tabela = REGEX_TABELA.match(ind[0])
    tabela = tabela.group(1) if tabela else arq.stem
    linhas = ler_folha(wb[ind[0]])
    linhas_cv = ler_folha(wb[cvs[0]])

    titulo = re.sub(r"\s+", " ", str(linhas[0][0][0])).strip()
    escopo_tipo, escopo = identificar_escopo(titulo)
    titulo = re.sub(r"^Tabela\s+[\d.]+a?\s*-\s*", "", titulo)

    ini = achar_inicio_dados(linhas)
    if ini is None:
        avisos.append(f"{arq.name}: sem dados numéricos")
        return []
    cab = linhas[1:ini]
    ncols = max(len(l[0]) for l in linhas)
    colunas = montar_colunas(cab, ncols)
    universo = next((limpar_texto(x) for x in cab[0][0][1:] if x), None) or limpar_texto(cab[0][0][0])

    pares = alinhar_linhas(linhas, linhas_cv)
    registros = {}
    pilha = []
    for i in range(ini, len(linhas)):
        valores, indent = linhas[i]
        bruto = valores[0]
        if bruto is None or REGEX_NOTA.match(str(bruto).strip()):
            continue
        rotulo = limpar_texto(bruto)
        tem_valor = any(e_numero(valores[j]) for j in colunas if j < len(valores))
        nivel = nivel_linha(bruto, indent)
        # Linha com valor no mesmo nível de um cabeçalho sem valor é filha dele
        while pilha and (pilha[-1][0] > nivel or (pilha[-1][0] == nivel and (pilha[-1][2] or not tem_valor))):
            pilha.pop()
        categoria = " > ".join(r for _, r, _ in pilha)
        pilha.append((nivel, rotulo, tem_valor))

        ic = pares.get(i)
        if ic is None or limpar_texto(linhas_cv[ic][0][0]) != rotulo:
            avisos.append(f"{arq.name} linha {i + 1}: rótulo difere entre INDICADOR e CV")
        for j, (medida, coluna) in colunas.items():
            v = valores[j] if j < len(valores) else None
            if not e_numero(v):
                continue
            cv = None
            if ic is not None and j < len(linhas_cv[ic][0]) and e_numero(linhas_cv[ic][0][j]):
                cv = linhas_cv[ic][0][j]
            reg = registros.setdefault((i, coluna), {
                "escopo_tipo": escopo_tipo, "escopo": escopo, "tabela": tabela, "titulo": titulo,
                "universo": universo, "categoria": categoria, "item": rotulo, "coluna": coluna,
                "arquivo": str(arq.relative_to(PASTA)),
            })
            if medida == "total":
                reg["total"], reg["cv_total"] = v, cv
            else:
                reg["percentual"], reg["cv_percentual"] = v, cv
    return list(registros.values())


def checar_percentuais(df, avisos):
    # Confere se percentual ~ total / total geral da mesma coluna (linhas aninhadas são relativas ao pai, então ficam de fora)
    ruins = 0
    for _, g in df.groupby(["arquivo", "coluna"]):
        tot = g[(g["categoria"] == "") & (g["item"] == "Total")]["total"]
        if tot.empty or pd.isna(tot.iloc[0]) or tot.iloc[0] == 0:
            continue
        g = g[~g["categoria"].fillna("").str.contains(">")]
        esperado = g["total"] / tot.iloc[0] * 100
        dif = (esperado - g["percentual"]).abs()
        fora = g[dif > 0.05]
        ruins += len(fora)
        for _, r in fora.head(3).iterrows():
            avisos.append(f"% não bate com total/total geral: {r['arquivo']} | {r['categoria']} | {r['item']}")
    return ruins


def main():
    arquivos = sorted(p for p in PASTA.rglob("*.xlsx") if not p.name.startswith("~$"))
    if not arquivos:
        print(f"Nenhum .xlsx em {PASTA}. Rode scripts/coleta_peers.py antes.")
        return 1
    avisos, registros = [], []
    for arq in arquivos:
        registros += processar_arquivo(arq, avisos)

    df = pd.DataFrame(registros)
    for c in ["total", "percentual", "cv_total", "cv_percentual"]:
        if c not in df:
            df[c] = pd.NA
    df["faixa_cv_total"] = df["cv_total"].map(faixa_cv)
    df["faixa_cv_percentual"] = df["cv_percentual"].map(faixa_cv)
    df["eh_total_geral"] = (df["categoria"] == "") & (df["item"] == "Total")
    # Ordena pelo número da tabela (ex.: 22.1, 22.2) sem perder a ordem das linhas dentro dela
    partes = df["tabela"].str.split(".", expand=True).reindex(columns=[0, 1]).fillna("0")
    df["_maior"] = pd.to_numeric(partes[0], errors="coerce").fillna(999)
    df["_menor"] = pd.to_numeric(partes[1], errors="coerce").fillna(0)
    df = df.sort_values(["escopo_tipo", "_maior", "_menor"], kind="stable").drop(columns=["_maior", "_menor"])
    # Prefixo evita que "22.1" ou "1" sejam lidos como número ao reabrir o CSV
    df["tabela"] = "Tabela " + df["tabela"]

    colunas = ["escopo_tipo", "escopo", "tabela", "titulo", "universo", "categoria", "item", "coluna",
               "total", "percentual", "cv_total", "cv_percentual", "faixa_cv_total", "faixa_cv_percentual",
               "eh_total_geral", "arquivo"]
    df = df[colunas]
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA, index=False, encoding="utf-8")

    n_ruins = checar_percentuais(df, avisos)
    print(f"[ok] {len(arquivos)} arquivos, {df['tabela'].nunique()} tabelas, {len(df)} linhas -> {SAIDA}")
    print(f"[info] {n_ruins} linha(s) com % diferente de total/total geral")
    for a in avisos:
        print(f"[aviso] {a}")
    return 0


if __name__ == "__main__":
    sys.exit(main())