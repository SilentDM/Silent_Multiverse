"""
Operações de arquivos e pastas do projeto (antes espalhadas pelo Explorer).

Todas as funções recebem/devolvem caminhos (str) e lançam ErroOperacao com uma
mensagem já traduzida quando algo não pode ser feito — a interface só exibe.
"""
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import engine.project_utils as pu
from core.i18n import t, tc


class ErroOperacao(Exception):
    """Erro esperado de uma operação de arquivo (mensagem pronta para o usuário)."""


# ----------------------------------------------------------------------
# ÁRVORE DO PROJETO
# ----------------------------------------------------------------------
@dataclass
class NoArvore:
    nome: str            # texto exibido (arquivos .md sem a extensão)
    caminho: str
    pasta: bool
    filhos: list = field(default_factory=list)


def montar_arvore(permitidos: set = None, max_profundidade: int = 15) -> NoArvore:
    """
    Árvore de pastas e arquivos .md do projeto, na ordem livre salva pelo usuário.
    Se 'permitidos' for informado (resultado de buscar()), mostra só esses caminhos.
    """
    raiz = str(pu.CAMINHO_PROJETO)
    os.makedirs(raiz, exist_ok=True)
    no_raiz = NoArvore(pu.PASTA_PROJETO, raiz, True)

    def preencher(no, caminho, profundidade):
        if profundidade > max_profundidade:
            return
        for item in pu.obter_itens_ordenados(caminho):
            if item in pu.IGNORELIST:
                continue
            item_path = os.path.join(caminho, item)
            if os.path.islink(item_path):
                continue
            eh_pasta = os.path.isdir(item_path)
            if permitidos is not None and os.path.abspath(item_path) not in permitidos:
                continue
            if not eh_pasta and not item.lower().endswith(".md"):
                continue
            nome = item if eh_pasta else item[:-3]
            filho = NoArvore(nome, item_path, eh_pasta)
            no.filhos.append(filho)
            if eh_pasta:
                preencher(filho, item_path, profundidade + 1)

    preencher(no_raiz, raiz, 0)
    return no_raiz


def buscar(consulta: str) -> set:
    """Caminhos (absolutos) de arquivos cujo nome ou conteúdo contém a consulta, mais suas pastas."""
    consulta = (consulta or "").strip().lower()
    encontrados = set()
    if not consulta:
        return encontrados
    for arq in Path(pu.CAMINHO_PROJETO).rglob("*.md"):
        if pu.arquivo_em_pasta_ignorada(arq):
            continue
        conteudo = (pu.ler_markdown(arq) or "").lower()
        if consulta in arq.name.lower() or consulta in conteudo:
            p = arq.resolve()
            encontrados.add(str(p))
            encontrados.update(str(pai) for pai in p.parents)
    return encontrados


def salvar_ordem(pasta: str, nomes_itens: list):
    pu.salvar_ordem_pasta(pasta, nomes_itens)


# ----------------------------------------------------------------------
# LEITURA
# ----------------------------------------------------------------------
def ler_texto(caminho: str) -> str:
    texto = pu.ler_markdown(Path(caminho))
    if texto is None:
        raise ErroOperacao(t("arquivos.erro_leitura", nome=os.path.basename(caminho)))
    return texto


# ----------------------------------------------------------------------
# CRIAR
# ----------------------------------------------------------------------
def listar_templates() -> list:
    """Nomes (minúsculos, sem .md) dos modelos em .silent_data/Templates e <projeto>/Templates."""
    encontrados = set()
    for pasta in (pu.PASTA_TEMPLATES, Path(pu.CAMINHO_PROJETO) / "Templates"):
        if pasta.is_dir():
            encontrados.update(arq.stem.lower() for arq in pasta.glob("*.md"))
    return sorted(encontrados)


def _titulo_de(nome_arquivo: str) -> str:
    return re.sub(r"\.md$", "", nome_arquivo, flags=re.IGNORECASE).replace("_", " ").title()


def criar_arquivo(pasta: str, nome: str, template: str = None) -> str:
    """Cria um .md novo com tag TODO (e o template, se escolhido). Devolve o caminho."""
    import engine.wbuilder as wb
    nome = (nome or "").strip()
    if not nome:
        raise ErroOperacao(t("arquivos.erro_nome_vazio"))
    if not nome.lower().endswith(".md"):
        nome += ".md"
    caminho = os.path.join(pasta, nome)
    if os.path.exists(caminho):
        raise ErroOperacao(t("arquivos.erro_ja_existe_arquivo"))

    titulo = _titulo_de(nome)
    conteudo_template = wb.obter_conteudo_template(template) if template else ""
    if conteudo_template:
        conteudo = tc("arquivos.stub_com_template", titulo=titulo, marcador_rascunho=tc("marcador.rascunho")) \
            + "\n" + conteudo_template
    else:
        conteudo = tc("arquivos.stub_simples", titulo=titulo)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)
    return caminho


def criar_pasta(pasta_pai: str, nome: str) -> str:
    nome = (nome or "").strip()
    if not nome:
        raise ErroOperacao(t("arquivos.erro_nome_vazio"))
    caminho = os.path.join(pasta_pai, nome)
    if os.path.exists(caminho):
        raise ErroOperacao(t("arquivos.erro_ja_existe_pasta"))
    os.makedirs(caminho, exist_ok=True)
    return caminho


# ----------------------------------------------------------------------
# RENOMEAR / EXCLUIR / COPIAR / MOVER
# ----------------------------------------------------------------------
def nome_para_renomear(caminho: str) -> str:
    return os.path.basename(caminho)


def renomear(caminho: str, novo_nome: str) -> str:
    novo_nome = (novo_nome or "").strip()
    if not novo_nome:
        raise ErroOperacao(t("arquivos.erro_nome_vazio"))
    if os.path.isfile(caminho) and not novo_nome.lower().endswith(".md"):
        novo_nome += ".md"
    if novo_nome == os.path.basename(caminho):
        return caminho
    novo_caminho = os.path.join(os.path.dirname(caminho), novo_nome)
    if os.path.exists(novo_caminho):
        raise ErroOperacao(t("arquivos.erro_ja_existe"))
    os.rename(caminho, novo_caminho)
    return novo_caminho


def excluir(caminho: str):
    if os.path.isdir(caminho):
        shutil.rmtree(caminho)
    else:
        os.remove(caminho)


def _pasta_destino(alvo: str) -> str:
    return alvo if os.path.isdir(alvo) else os.path.dirname(alvo)


def colar(origem: str, alvo: str, recortar: bool) -> str:
    """Copia (ou move, se recortar) 'origem' para a pasta de 'alvo'. Devolve o novo caminho."""
    if not os.path.exists(origem):
        raise ErroOperacao(t("arquivos.erro_area_vazia"))
    destino = os.path.join(_pasta_destino(alvo), os.path.basename(origem))
    if os.path.abspath(origem) == os.path.abspath(destino):
        raise ErroOperacao(t("arquivos.erro_mesmo_caminho"))
    if recortar:
        shutil.move(origem, destino)
    elif os.path.isdir(origem):
        shutil.copytree(origem, destino, dirs_exist_ok=True)
    else:
        shutil.copy2(origem, destino)
    return destino


def duplicar(caminho: str) -> str:
    diretorio = os.path.dirname(caminho)
    nome, ext = os.path.splitext(os.path.basename(caminho))
    sufixo = tc("arquivos.sufixo_copia")
    novo = os.path.join(diretorio, f"{nome}_{sufixo}{ext}")
    contador = 1
    while os.path.exists(novo):
        novo = os.path.join(diretorio, f"{nome}_{sufixo}_{contador}{ext}")
        contador += 1
    if os.path.isdir(caminho):
        shutil.copytree(caminho, novo)
    else:
        shutil.copy2(caminho, novo)
    return novo


def mover_para(origem: str, alvo: str) -> str:
    """Move 'origem' para a pasta do item 'alvo' (arrastar e soltar). Devolve o novo caminho."""
    pasta = os.path.abspath(_pasta_destino(alvo))
    origem_abs = os.path.abspath(origem)
    if os.path.isdir(origem_abs) and (pasta == origem_abs or pasta.startswith(origem_abs + os.sep)):
        raise ErroOperacao(t("arquivos.erro_mover_para_si"))
    destino = os.path.join(pasta, os.path.basename(origem_abs))
    if os.path.abspath(destino) == origem_abs:
        return origem_abs
    if os.path.exists(destino):
        raise ErroOperacao(t("arquivos.erro_ja_existe"))
    shutil.move(origem_abs, destino)
    return destino


# ----------------------------------------------------------------------
# WIKILINKS
# ----------------------------------------------------------------------
def nome_do_wikilink(texto_link: str) -> str:
    """'Pasta/Nome#Seção|Apelido' -> 'Nome' (o arquivo que o link cita, como no Obsidian)."""
    alvo = texto_link.split("|")[0].split("#")[0].strip()
    return alvo.replace("\\", "/").rstrip("/").split("/")[-1].strip()


def resolver_wikilink(nome_alvo: str):
    """Caminho do .md citado por [[nome_alvo]] (ignora acentos/separadores e prefere a maior versão _vNN)."""
    alvo_norm = pu.normalizar_nome(nome_do_wikilink(nome_alvo))
    if not alvo_norm:
        return None
    candidatos = []
    for arq in Path(pu.CAMINHO_PROJETO).rglob("*.md"):
        if pu.arquivo_em_pasta_ignorada(arq):
            continue
        if pu.normalizar_nome(arq.stem) == alvo_norm:
            candidatos.append(arq.resolve())
    if not candidatos:
        return None

    def versao(p):
        m = re.search(r"_v(\d+)$", p.stem, flags=re.IGNORECASE)
        return int(m.group(1)) if m else 0

    return str(max(candidatos, key=versao))


def criar_por_wikilink(nome_alvo: str, pasta_destino: str, nome_origem: str) -> str:
    """Cria o documento citado por um wikilink inexistente, ao lado do arquivo de origem."""
    nome_alvo = nome_do_wikilink(nome_alvo)
    if not nome_alvo:
        raise ErroOperacao(t("arquivos.erro_nome_vazio"))
    nome_md = nome_alvo if nome_alvo.lower().endswith(".md") else f"{nome_alvo}.md"
    caminho = os.path.join(pasta_destino, nome_md)
    if os.path.exists(caminho):
        return caminho
    conteudo = tc("arquivos.stub_wikilink", titulo=_titulo_de(nome_md), origem=nome_origem or "origem")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)
    return caminho


def remapear_caminho(caminho, origem, destino):
    """Se 'caminho' é 'origem' ou está dentro dela, devolve o caminho equivalente sob 'destino'."""
    if not caminho:
        return caminho
    caminho_abs, origem_abs = os.path.abspath(caminho), os.path.abspath(origem)
    if caminho_abs == origem_abs:
        return os.path.abspath(destino)
    if caminho_abs.startswith(origem_abs + os.sep):
        return os.path.join(os.path.abspath(destino), caminho_abs[len(origem_abs) + 1:])
    return caminho


def esta_dentro(item: str, caminho) -> bool:
    """True se 'caminho' é o próprio 'item' ou está dentro dele (pasta)."""
    if not caminho:
        return False
    item_abs, caminho_abs = os.path.abspath(item), os.path.abspath(caminho)
    return caminho_abs == item_abs or caminho_abs.startswith(item_abs + os.sep)


# ----------------------------------------------------------------------
# CONSULTAS SIMPLES DE CAMINHO (para a interface não lidar com o sistema de arquivos)
# ----------------------------------------------------------------------
def nome(caminho) -> str:
    return os.path.basename(str(caminho)) if caminho else ""


def pasta_de(caminho) -> str:
    return os.path.dirname(str(caminho))


def absoluto(caminho) -> str:
    return os.path.abspath(str(caminho))


def existe(caminho) -> bool:
    return bool(caminho) and os.path.exists(str(caminho))


def eh_arquivo(caminho) -> bool:
    return bool(caminho) and os.path.isfile(str(caminho))


def eh_pasta(caminho) -> bool:
    return bool(caminho) and os.path.isdir(str(caminho))


def eh_markdown(caminho) -> bool:
    return eh_arquivo(caminho) and str(caminho).lower().endswith(".md")


def mesmo_caminho(a, b) -> bool:
    return bool(a and b) and os.path.abspath(str(a)) == os.path.abspath(str(b))
