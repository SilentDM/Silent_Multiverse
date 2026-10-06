"""
Notas do Mestre: uma seção secreta no fim de cada arquivo.

Guarda o que veio de outras ferramentas para influenciar as próximas criações:
  - notas de Silent (observador externo, brainstorming no chat)
  - depoimentos do Roleplay (a versão de um personagem — pode mentir ou estar enganado)
  - notas escritas pelo próprio Mestre

O título da seção leva o marcador de segredo, então os jogadores nunca a veem. As ferramentas
de IA recebem as notas no pedido e a seção é preservada quando o arquivo é reescrito.
"""
import re
from datetime import datetime
from pathlib import Path

import core.eventos as ev
import core.i18n as i18n
import engine.historico as hist
import engine.project_utils as pu
from core.i18n import t, tc

ORIGENS = ("silent", "roleplay", "mestre")


class ErroNotas(Exception):
    """Falha esperada (arquivo travado pela IA, arquivo inexistente) com mensagem pronta."""


def _titulos_conhecidos() -> list:
    """Nomes da seção nos dois idiomas, para reconhecer arquivos escritos em qualquer um deles."""
    nomes = []
    for idioma in i18n.IDIOMAS:
        titulo = i18n.traduzir("notas.titulo", idioma, "")
        nome = re.sub(r"\[[^\]]*\]", "", titulo).replace("#", "").replace("🤫", "").strip()
        if nome:
            nomes.append(nome.lower())
    return nomes


def _eh_titulo_da_secao(linha: str) -> bool:
    if not linha.startswith("## "):
        return False
    texto = linha[3:].lower()
    return any(nome in texto for nome in _titulos_conhecidos())


def separar(texto: str) -> tuple:
    """(conteúdo sem a seção de notas, seção de notas ou '')."""
    linhas = (texto or "").splitlines()
    inicio = next((i for i, linha in enumerate(linhas) if _eh_titulo_da_secao(linha)), None)
    if inicio is None:
        return texto or "", ""
    fim = next((i for i in range(inicio + 1, len(linhas)) if re.match(r"^#{1,2} ", linhas[i])), len(linhas))
    corpo = linhas[:inicio] + linhas[fim:]
    return "\n".join(corpo).rstrip() + "\n", "\n".join(linhas[inicio:fim]).strip() + "\n"


def reanexar(corpo: str, secao: str) -> str:
    """Devolve o texto com a seção de notas no fim (tira uma eventual cópia que a IA tenha devolvido)."""
    corpo = separar(corpo)[0].rstrip()
    if not secao.strip():
        return corpo + "\n"
    return corpo + "\n\n" + secao.strip() + "\n"


def secao_do_arquivo(caminho) -> str:
    try:
        return separar(Path(caminho).read_text(encoding="utf-8", errors="ignore"))[1]
    except OSError:
        return ""


def rotulo_origem(origem: str, autor: str = "") -> str:
    if origem == "roleplay":
        return tc("notas.origem.roleplay", nome=autor or "?")
    return tc(f"notas.origem.{origem if origem in ORIGENS else 'mestre'}")


def adicionar_nota(caminho, texto: str, origem: str = "mestre", autor: str = "") -> str:
    """Acrescenta uma nota à seção secreta do arquivo (criando a seção se preciso). A versão anterior vai ao histórico."""
    import engine.expander as ex
    caminho = Path(caminho)
    texto = (texto or "").strip()
    if not caminho.is_file():
        raise ErroNotas(t("notas.erro_arquivo", nome=caminho.name))
    if not texto:
        raise ErroNotas(t("notas.erro_vazia"))
    if ex.esta_em_processamento(caminho):
        raise ErroNotas(t("notas.erro_travado", nome=caminho.name))

    original = caminho.read_text(encoding="utf-8", errors="ignore")
    corpo, secao = separar(original)
    if not secao:
        secao = tc("notas.titulo") + "\n> " + tc("notas.explicacao") + "\n"
    data = datetime.now().strftime(t("historico.formato_data"))
    citacao = "\n".join(f"> {linha}" if linha.strip() else ">" for linha in texto.splitlines())
    entrada = f"### {rotulo_origem(origem, autor)} — {data}\n{citacao}\n"
    hist.arquivar_versao_para_historico(caminho)
    pu.gravar_markdown(caminho, reanexar(corpo, secao.rstrip() + "\n\n" + entrada))
    ev.log(t("notas.log_adicionada", nome=caminho.name, origem=rotulo_origem(origem, autor)))
    return str(caminho)


def listar_notas(caminho) -> list:
    """[{'titulo': str, 'texto': str, 'depoimento': bool}] da seção de notas do arquivo."""
    secao = secao_do_arquivo(caminho)
    marca_depoimento = [re.sub(r"\{nome\}.*", "", i18n.traduzir("notas.origem.roleplay", idioma, "")).strip().lower()
                        for idioma in i18n.IDIOMAS]
    notas, atual = [], None
    for linha in secao.splitlines()[1:]:
        if linha.startswith("### "):
            titulo = linha[4:].strip()
            atual = {"titulo": titulo, "texto": "",
                     "depoimento": any(m and titulo.lower().startswith(m) for m in marca_depoimento)}
            notas.append(atual)
        elif atual is not None:
            atual["texto"] += re.sub(r"^>\s?", "", linha) + "\n"
    for nota in notas:
        nota["texto"] = nota["texto"].strip()
    return notas


def bloco_para_prompt(caminho, secao: str = None) -> str:
    """Notas do arquivo prontas para entrar num pedido à IA ('' se não houver)."""
    secao = secao if secao is not None else secao_do_arquivo(caminho)
    if not secao.strip():
        return ""
    return "\n" + tc("notas.bloco_prompt") + "\n" + secao.strip() + "\n"


def sugerir_destinos(texto: str, arquivo_atual: str = None, nomes=()) -> list:
    """
    Arquivos sugeridos para guardar a nota: o arquivo do personagem (nomes), o aberto no Editor
    e os citados no texto como [[link]], sem repetir.
    """
    import engine.arquivos as arq
    destinos = []
    for nome in nomes:
        caminho = arq.resolver_wikilink(nome) if nome else None
        if caminho:
            destinos.append(str(Path(caminho).resolve()))
    if arquivo_atual and Path(arquivo_atual).is_file() and str(Path(arquivo_atual).resolve()) not in destinos:
        destinos.append(str(Path(arquivo_atual).resolve()))
    for alvo in re.findall(r"(?<!!)\[\[([^\]]+)\]\]", texto or ""):
        caminho = arq.resolver_wikilink(alvo)
        if caminho and str(Path(caminho).resolve()) not in destinos:
            destinos.append(str(Path(caminho).resolve()))
    return destinos
