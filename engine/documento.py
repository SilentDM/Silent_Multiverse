"""
Informações sobre os documentos do projeto para o Editor (sem Tk):

  - sumario(texto)          títulos do arquivo, para o painel lateral
  - links_quebrados(texto)  [[links]] que ainda não têm arquivo (o editor os pinta de vermelho)
  - sugerir_links(prefixo)  nomes de arquivo para o autocompletar de [[
  - citado_por(caminho)     arquivos que linkam este
  - resolver_link(texto)    arquivo de um [[link]] (o chat do Silent abre links clicados)
  - resumo_pasta(caminho)   visão geral de uma pasta (árvore, totais, estados, recentes, links sem arquivo)
  - estado(caminho)         segredo / rascunho / TODO pendente / tem Notas do Mestre (ícones da árvore)
  - assinatura_projeto()    muda quando algo muda na pasta do projeto (atualização automática da árvore)

O índice de nomes e o estado de cada arquivo ficam em cache (pela data de modificação),
então nada disso relê o projeto inteiro a cada tecla.
"""
import os
import re
import threading
import time
from pathlib import Path

import core.secret_filter as sf
import engine.notas as notas
import engine.project_utils as pu

_WIKILINK = re.compile(r"(?<!!)\[\[([^\]\n]+)\]\]")
_TITULO = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
EXTENSOES_IMAGEM = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp")
INTERVALO_VERIFICACAO = 2.0       # segundos entre conferências da pasta do projeto

_lock = threading.Lock()
_indice = {"projeto": None, "assinatura": None, "nomes": {}}      # nome normalizado -> caminho
_estados = {}                                                      # caminho -> (mtime, estado)


def _normalizar(nome: str) -> str:
    return pu.normalizar_nome(re.sub(r"_v\d+$", "", nome.strip(), flags=re.IGNORECASE))


def _arquivos_md():
    raiz = Path(pu.CAMINHO_PROJETO)
    for caminho in raiz.rglob("*.md"):
        if not pu.arquivo_em_pasta_ignorada(caminho):
            yield caminho


# ----------------------------------------------------------------------
# ASSINATURA E ÍNDICE DE NOMES
# ----------------------------------------------------------------------
def assinatura_projeto() -> tuple:
    """(nº de arquivos .md, soma das datas de modificação): muda se algo for criado, apagado, movido ou salvo."""
    total, soma = 0, 0.0
    raiz = str(pu.CAMINHO_PROJETO)
    for pasta, subpastas, arquivos in os.walk(raiz):
        subpastas[:] = [s for s in subpastas if s not in pu.IGNORELIST and not s.startswith(".")]
        for nome in arquivos:
            if nome.lower().endswith(".md"):
                try:
                    soma += os.stat(os.path.join(pasta, nome)).st_mtime
                    total += 1
                except OSError:
                    pass
    return total, round(soma, 3)


def _indice_atual() -> dict:
    """Nomes normalizados -> caminho. Confere a pasta no máximo a cada INTERVALO_VERIFICACAO segundos."""
    with _lock:
        agora = time.monotonic()
        mesmo_projeto = _indice["projeto"] == pu.CAMINHO_PROJETO
        if mesmo_projeto and agora - _indice.get("verificado", 0) < INTERVALO_VERIFICACAO:
            return _indice["nomes"]
        assinatura = assinatura_projeto()
        if not mesmo_projeto or _indice["assinatura"] != assinatura:
            nomes = {}
            for caminho in _arquivos_md():
                nomes.setdefault(_normalizar(caminho.stem), str(caminho))
            _indice.update(projeto=pu.CAMINHO_PROJETO, assinatura=assinatura, nomes=nomes)
        _indice["verificado"] = agora
        return _indice["nomes"]


def invalidar():
    """Esquece o cache (após criar/renomear/mover arquivos pelo próprio programa)."""
    with _lock:
        _indice.update(projeto=None, assinatura=None, nomes={}, verificado=0)


def buscar_arquivos(consulta: str, limite: int = 30) -> list:
    """[(nome, caminho relativo, caminho)] para a abertura rápida (Ctrl+P): nome começa com / contém a consulta."""
    alvo = _normalizar(consulta or "")
    raiz = Path(pu.CAMINHO_PROJETO)
    comeca, contem = [], []
    for arquivo in _arquivos_md():
        normal = _normalizar(arquivo.stem)
        item = (arquivo.stem, arquivo.relative_to(raiz).as_posix(), str(arquivo))
        if not alvo or normal.startswith(alvo):
            comeca.append(item)
        elif alvo in normal or alvo in _normalizar(item[1]):
            contem.append(item)
    ordenar = lambda lista: sorted(lista, key=lambda i: i[0].lower())
    return (ordenar(comeca) + ordenar(contem))[:limite]


# ----------------------------------------------------------------------
# CONTEÚDO DO DOCUMENTO
# ----------------------------------------------------------------------
def sumario(texto: str) -> list:
    """[(nível, título, número_da_linha)] dos títulos fora de blocos de código."""
    itens, em_codigo = [], False
    for numero, linha in enumerate((texto or "").splitlines(), start=1):
        if linha.strip().startswith("```"):
            em_codigo = not em_codigo
            continue
        achado = None if em_codigo else _TITULO.match(linha)
        if achado:
            itens.append((len(achado.group(1)), achado.group(2).strip(), numero))
    return itens


def _alvo(texto_link: str) -> str:
    alvo = texto_link.split("|")[0].split("#")[0].strip()
    return alvo.replace("\\", "/").rstrip("/").split("/")[-1].strip()


def links_quebrados(texto: str) -> list:
    """[(inicio, fim)] dos [[links]] (não imagens) cujo arquivo não existe no projeto."""
    nomes = _indice_atual()
    quebrados = []
    for achado in _WIKILINK.finditer(texto or ""):
        alvo = _alvo(achado.group(1))
        if not alvo or alvo.lower().endswith(EXTENSOES_IMAGEM):
            continue
        if _normalizar(alvo) not in nomes:
            quebrados.append((achado.start(), achado.end()))
    return quebrados


def sugerir_links(prefixo: str, limite: int = 8) -> list:
    """Nomes de arquivo (sem .md) para o autocompletar: primeiro os que começam com o prefixo, depois os que contêm."""
    alvo = _normalizar(prefixo or "")
    comeca, contem = [], []
    for normal, caminho in _indice_atual().items():
        nome = re.sub(r"_v\d+$", "", Path(caminho).stem, flags=re.IGNORECASE)
        if not alvo or normal.startswith(alvo):
            comeca.append(nome)
        elif alvo in normal:
            contem.append(nome)
    return (sorted(set(comeca), key=str.lower) + sorted(set(contem), key=str.lower))[:limite]


def resolver_link(texto_link: str):
    """Caminho do arquivo de um [[link]] (aceita 'Nome|apelido' e 'Nome#seção'), ou None se não existe."""
    alvo = _alvo(texto_link or "")
    return _indice_atual().get(_normalizar(alvo)) if alvo else None


def citado_por(caminho) -> list:
    """Arquivos do projeto que têm um [[link]] para este (em ordem alfabética)."""
    alvo = Path(caminho).resolve()
    nome_alvo = _normalizar(alvo.stem)
    resultado = []
    for arquivo in _arquivos_md():
        if arquivo.resolve() == alvo:
            continue
        texto = pu.ler_markdown(arquivo) or ""
        if "[[" in texto and any(_normalizar(_alvo(m.group(1))) == nome_alvo for m in _WIKILINK.finditer(texto)):
            resultado.append(str(arquivo))
    return sorted(resultado, key=lambda c: Path(c).stem.lower())


# ----------------------------------------------------------------------
# VISÃO GERAL DE UMA PASTA (o Editor mostra quando uma pasta é selecionada)
# ----------------------------------------------------------------------
CHARS_POR_TOKEN = 3.5


def _visivel(item: Path) -> bool:
    return not item.name.startswith(".") and item.name not in pu.IGNORELIST


def resumo_pasta(caminho, max_itens: int = 400, recentes: int = 6) -> dict:
    """
    Tudo o que dá para saber de uma pasta sem abrir os arquivos um a um:
      itens       [(nível, "pasta"|"arquivo"|"vazia"|"mais", nome, caminho, estado, palavras)] em ordem de árvore
      totais      arquivos, subpastas, palavras, tokens (estimados), imagens e outros arquivos
      estados     quantos arquivos são segredo / rascunho / têm TODO / têm Notas do Mestre
      recentes    [(caminho, nome, data de modificação)] os editados por último
      sem_arquivo nomes de [[links]] citados aqui que ainda não têm arquivo no projeto
    """
    raiz = Path(caminho)
    nomes = _indice_atual()
    itens, recentes_lista, sem_arquivo = [], [], {}
    totais = {"arquivos": 0, "subpastas": 0, "palavras": 0, "tokens": 0, "imagens": 0, "outros": 0}
    estados = {"segredo": 0, "rascunho": 0, "todo": 0, "notas": 0}

    def percorrer(pasta: Path, nivel: int):
        try:
            filhos = sorted((f for f in pasta.iterdir() if _visivel(f)), key=lambda f: (f.is_file(), f.name.lower()))
        except OSError:
            return
        conteudo = [f for f in filhos if f.is_dir() or f.suffix.lower() == ".md"]
        if not conteudo and nivel:
            itens.append((nivel, "vazia", "", str(pasta), None, 0))
        for item in filhos:
            if item.is_dir():
                totais["subpastas"] += 1
                if len(itens) < max_itens:
                    itens.append((nivel, "pasta", item.name, str(item), None, 0))
                percorrer(item, nivel + 1)
                continue
            extensao = item.suffix.lower()
            if extensao != ".md":
                totais["imagens" if extensao in EXTENSOES_IMAGEM else "outros"] += 1
                continue
            texto = pu.ler_markdown(item) or ""
            palavras = len(texto.split())
            estado_arquivo = estado(item)
            totais["arquivos"] += 1
            totais["palavras"] += palavras
            totais["tokens"] += int(round(len(texto) / CHARS_POR_TOKEN))
            for chave in estados:
                estados[chave] += 1 if estado_arquivo[chave] else 0
            for achado in _WIKILINK.finditer(texto):
                alvo = _alvo(achado.group(1))
                if alvo and not alvo.lower().endswith(EXTENSOES_IMAGEM) and _normalizar(alvo) not in nomes:
                    sem_arquivo.setdefault(_normalizar(alvo), alvo)
            try:
                recentes_lista.append((item.stat().st_mtime, str(item), item.stem))
            except OSError:
                pass
            if len(itens) < max_itens:
                itens.append((nivel, "arquivo", item.stem, str(item), estado_arquivo, palavras))

    percorrer(raiz, 0)
    if len(itens) >= max_itens:
        itens.append((0, "mais", "", "", None, 0))
    recentes_lista.sort(reverse=True)
    return {
        "nome": raiz.name,
        "relativo": _relativo(raiz),
        "itens": itens,
        "totais": totais,
        "estados": estados,
        "recentes": [(c, n, m) for m, c, n in recentes_lista[:recentes]],
        "sem_arquivo": sorted(sem_arquivo.values(), key=str.lower),
    }


def _relativo(caminho: Path) -> str:
    try:
        relativo = caminho.resolve().relative_to(Path(pu.CAMINHO_PROJETO).resolve()).as_posix()
    except ValueError:
        return caminho.name
    return relativo if relativo != "." else ""


# ----------------------------------------------------------------------
# ESTADO DOS ARQUIVOS (ícones da árvore)
# ----------------------------------------------------------------------
def estado(caminho) -> dict:
    """{'segredo', 'rascunho', 'todo', 'notas'}: o que o arquivo tem, para mostrar na árvore."""
    caminho = str(caminho)
    try:
        mtime = os.stat(caminho).st_mtime
    except OSError:
        return {"segredo": False, "rascunho": False, "todo": False, "notas": False}
    with _lock:
        guardado = _estados.get(caminho)
        if guardado and guardado[0] == mtime:
            return guardado[1]
    texto = pu.ler_markdown(Path(caminho)) or ""
    inicio = texto[:1500].lower()
    corpo, secao_notas = notas.separar(texto)
    resultado = {
        "segredo": any(m in inicio for m in sf.MARCADORES_ARQUIVO_SECRETO),
        "rascunho": pu.eh_rascunho(texto[:1500]),
        "todo": any(tag in corpo for tag in pu.TAG_ALVO),
        "notas": bool(secao_notas.strip()),
    }
    with _lock:
        _estados[caminho] = (mtime, resultado)
    return resultado
