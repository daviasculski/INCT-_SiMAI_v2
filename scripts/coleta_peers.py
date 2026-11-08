import argparse
import csv
import hashlib
import re
import sys
import time
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib import robotparser
from urllib.parse import unquote, urljoin, urlparse

import requests

PAGINA_PEERS = (
    "https://www.ibge.gov.br/estatisticas/multidominio/meio-ambiente/"
    "47278-pesquisa-especial-sobre-as-enchentes-de-2024-no-rio-grande-do-sul.html"
)
DIRETORIO_PEERS = "https://ftp.ibge.gov.br/Meio_Ambiente/PEERS/2024/"

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "dados" / "originais" / "peers"

# User-Agent identificado evita bloqueio por bot genérico
HEADERS = {
    "User-Agent": "projeto-enchentes-pucrs/1.0 (trabalho academico; PUCRS)",
    "Accept-Language": "pt-BR,pt;q=0.9",
}
ESPERA_S = 1.5


class ExtratorLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for nome, valor in attrs:
                if nome == "href" and valor:
                    self.links.append(valor)


def permitido_por_robots(url, sessao):
    # Sem robots.txt (ou erro ao ler) assume permitido
    p = urlparse(url)
    robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
    rp = robotparser.RobotFileParser()
    try:
        r = sessao.get(robots_url, timeout=20)
        if r.status_code != 200:
            return True
        rp.parse(r.text.splitlines())
    except requests.RequestException:
        return True
    return rp.can_fetch(HEADERS["User-Agent"], url)


def listar_links(url, sessao):
    r = sessao.get(url, timeout=30)
    r.raise_for_status()
    parser = ExtratorLinks()
    parser.feed(r.text)
    return [urljoin(url, href) for href in parser.links]


def descobrir_arquivos(sessao, formatos):
    # Tenta o diretório do IBGE primeiro e depois a página da pesquisa
    padrao = re.compile(r"\.(" + "|".join(map(re.escape, formatos)) + r")$", re.I)
    for origem in (DIRETORIO_PEERS, PAGINA_PEERS):
        try:
            if not permitido_por_robots(origem, sessao):
                print(f"[aviso] robots.txt não permite acessar {origem}")
                continue
            links = listar_links(origem, sessao)
            achados = sorted({l for l in links if padrao.search(urlparse(l).path)})
            if achados:
                print(f"[ok] {len(achados)} arquivo(s) encontrados em {origem}")
                return achados
            print(f"[aviso] nenhum arquivo {sorted(formatos)} em {origem}")
        except requests.RequestException as e:
            print(f"[aviso] falha ao acessar {origem}: {e}")
        time.sleep(ESPERA_S)
    return []


def baixar(url, sessao, forcar):
    nome = unquote(Path(urlparse(url).path).name)
    destino = DESTINO / nome
    if destino.exists() and not forcar:
        print(f"[cache] {nome} já existe, pulando")
        conteudo = destino.read_bytes()
        coletado_em = datetime.fromtimestamp(destino.stat().st_mtime, tz=timezone.utc)
    else:
        if not permitido_por_robots(url, sessao):
            print(f"[pulado] robots.txt não permite {url}")
            return None
        print(f"[baixando] {url}")
        r = sessao.get(url, timeout=120)
        r.raise_for_status()
        conteudo = r.content
        destino.write_bytes(conteudo)
        coletado_em = datetime.now(timezone.utc)
        time.sleep(ESPERA_S)
    return {
        "arquivo": nome,
        "url": url,
        "pagina_fonte": PAGINA_PEERS,
        "coletado_em_utc": coletado_em.isoformat(timespec="seconds"),
        "tamanho_bytes": len(conteudo),
        "sha256": hashlib.sha256(conteudo).hexdigest(),
    }


def extrair_zip(zip_path, forcar):
    # Extrai direto em DESTINO, pulando o que já existe e caminhos suspeitos
    raiz_destino = DESTINO.resolve()
    novos = 0
    with zipfile.ZipFile(zip_path) as zf:
        for membro in zf.infolist():
            alvo = (DESTINO / membro.filename).resolve()
            if raiz_destino not in alvo.parents:
                print(f"[pulado] caminho suspeito no zip: {membro.filename}")
                continue
            if alvo.exists() and not forcar:
                continue
            zf.extract(membro, DESTINO)
            novos += 1
    print(f"[ok] {zip_path.name}: {novos} item(ns) extraído(s)")


def salvar_manifesto(registros):
    caminho = DESTINO / "manifesto.csv"
    # Mantém a data de coleta antiga quando o arquivo não mudou (mesmo hash)
    existentes = {}
    if caminho.exists():
        with caminho.open(encoding="utf-8", newline="") as f:
            existentes = {l["arquivo"]: l for l in csv.DictReader(f)}
    for reg in registros:
        antigo = existentes.get(reg["arquivo"])
        if antigo and antigo["sha256"] == reg["sha256"]:
            reg["coletado_em_utc"] = antigo["coletado_em_utc"]
        existentes[reg["arquivo"]] = reg
    campos = ["arquivo", "url", "pagina_fonte", "coletado_em_utc", "tamanho_bytes", "sha256"]
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(existentes.values())
    print(f"[ok] manifesto salvo em {caminho}")


def main():
    ap = argparse.ArgumentParser(description="Coleta das tabelas da PEERS (IBGE)")
    ap.add_argument("--formatos", nargs="+", default=["zip"], help="extensões a baixar (padrão: zip)")
    ap.add_argument("--url", nargs="*", default=[], help="URLs manuais (pula a descoberta automática)")
    ap.add_argument("--planilha", default="xlsx", help="só baixa arquivos com este texto no nome (padrão: xlsx)")
    ap.add_argument("--forcar", action="store_true", help="baixa e extrai novamente")
    args = ap.parse_args()

    DESTINO.mkdir(parents=True, exist_ok=True)
    sessao = requests.Session()
    sessao.headers.update(HEADERS)

    urls = args.url or descobrir_arquivos(sessao, {f.lower().lstrip(".") for f in args.formatos})
    if not args.url:
        # O IBGE publica a mesma tabela em xlsx e ods; filtra pelo nome do arquivo
        urls = [u for u in urls if args.planilha.lower() in unquote(Path(urlparse(u).path).name).lower()]
        print(f"[ok] {len(urls)} arquivo(s) com '{args.planilha}' no nome")
    if not urls:
        print(
            "\nNão consegui descobrir os arquivos automaticamente.\n"
            "Copie o endereço de cada .zip na página da PEERS e rode:\n"
            "  python scripts/coleta_peers.py --url <URL1> <URL2>\n"
            f"Página: {PAGINA_PEERS}"
        )
        return 1

    registros = [r for u in urls if (r := baixar(u, sessao, args.forcar))]
    for reg in registros:
        if reg["arquivo"].lower().endswith(".zip"):
            extrair_zip(DESTINO / reg["arquivo"], args.forcar)
    if registros:
        salvar_manifesto(registros)
    return 0


if __name__ == "__main__":
    sys.exit(main())