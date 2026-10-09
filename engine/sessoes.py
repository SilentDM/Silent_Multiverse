"""
Sessões de jogo: o Mestre anota livremente durante a mesa; ao finalizar, Silent lê as anotações
contra o mundo inteiro e escreve o diário da sessão.

- As anotações da sessão em andamento ficam salvas na pasta de dados (não no cofre), para não entrarem
  no contexto da IA enquanto são rascunho e para sobreviverem a um fechamento do programa.
- O diário vai para <projeto>/Sessões/Sessão N.md, com propriedades do Obsidian (type, session, date)
  e status: segredo, porque traz conclusões e segredos de Mestre. As anotações originais vão junto, no fim.
"""
import re
from datetime import datetime
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

import core.ai_utils as au
import core.cache_gemini as cg
import core.eventos as ev
import core.propriedades as propriedades
import engine.expander as ex
import engine.project_utils as pu
from core.i18n import t, tc
from core.prompts import carregar_prompt


class ErroSessao(Exception):
    pass


# ----------------------------------------------------------------------
# DIÁRIO (resposta estruturada da IA)
# ----------------------------------------------------------------------
class CenaSessao(BaseModel):
    titulo: str = Field(description="Nome curto da cena")
    resumo: str = Field(description="O que aconteceu na cena, em poucas linhas, com [[links]] para arquivos do projeto")


class NascidoNaMesa(BaseModel):
    nome: str = Field(description="Nome do NPC, lugar, item ou fato criado na mesa")
    tipo: str = Field(description="NPC, lugar, facção, item ou fato")
    descricao: str = Field(description="O que foi dito sobre ele na sessão")


class Contradicao(BaseModel):
    dito_na_mesa: str = Field(description="O que foi dito ou decidido na sessão")
    escrito_no_mundo: str = Field(description="O que os arquivos do projeto dizem")
    arquivo: str = Field(description="O arquivo do projeto que contradiz, como [[link]]")
    sugestao: str = Field(description="Como resolver: ajustar o arquivo ou tratar como algo novo")


class SegredoEmRisco(BaseModel):
    segredo: str = Field(description="O segredo do Mestre em questão")
    arquivo: str = Field(description="O arquivo onde o segredo está, como [[link]]")
    situacao: str = Field(description="O que os jogadores descobriram ou o quão perto chegaram")


class DiarioSessao(BaseModel):
    titulo: str = Field(description="Um título curto e evocativo para a sessão")
    cenas: List[CenaSessao] = Field(description="As cenas da sessão, em ordem")
    nascidos_na_mesa: List[NascidoNaMesa] = Field(description="NPCs, lugares e fatos improvisados que ainda não têm arquivo no projeto")
    contradicoes: List[Contradicao] = Field(description="O que foi dito na mesa e contradiz o que está escrito no mundo")
    segredos_em_risco: List[SegredoEmRisco] = Field(description="Segredos que os jogadores descobriram ou dos quais chegaram perto")
    pontas_soltas: List[str] = Field(description="Ganchos abertos, promessas feitas a NPCs, perguntas sem resposta")
    conclusoes: List[str] = Field(description="O que Silent recomenda preparar para a próxima sessão")


# ----------------------------------------------------------------------
# ANOTAÇÕES DA SESSÃO EM ANDAMENTO
# ----------------------------------------------------------------------
def _pasta_dados() -> Path:
    pasta = pu.PASTA_LOGS / "sessoes" / re.sub(r'[\\/:*?"<>|]', "_", str(pu.PASTA_PROJETO))
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _arquivo_notas() -> Path:
    return _pasta_dados() / "em_andamento.md"


def carregar_notas() -> str:
    try:
        return _arquivo_notas().read_text(encoding="utf-8")
    except OSError:
        return ""


def salvar_notas(texto: str):
    _arquivo_notas().write_text(texto or "", encoding="utf-8")


# ----------------------------------------------------------------------
# DIÁRIOS NO COFRE
# ----------------------------------------------------------------------
def pasta_diarios() -> Path:
    return Path(pu.CAMINHO_PROJETO) / tc("sessoes.pasta")


def _numero_do_arquivo(caminho: Path):
    texto = caminho.read_text(encoding="utf-8", errors="ignore")[:2000]
    valor = propriedades.ler(texto).get("session")
    if isinstance(valor, str) and valor.strip().isdigit():
        return int(valor.strip())
    achado = re.search(r"(\d+)\s*$", caminho.stem)
    return int(achado.group(1)) if achado else None


def listar_diarios() -> list:
    """[(número, caminho)] dos diários já escritos, do mais recente para o mais antigo."""
    pasta = pasta_diarios()
    if not pasta.is_dir():
        return []
    diarios = []
    for caminho in pasta.glob("*.md"):
        numero = _numero_do_arquivo(caminho)
        if numero is not None:
            diarios.append((numero, str(caminho)))
    return sorted(diarios, reverse=True)


def proximo_numero() -> int:
    diarios = listar_diarios()
    return diarios[0][0] + 1 if diarios else 1


def caminho_diario(numero: int) -> Path:
    return pasta_diarios() / f"{tc('sessoes.nome_arquivo', numero=numero)}.md"


# ----------------------------------------------------------------------
# FINALIZAR: análise da IA e diário
# ----------------------------------------------------------------------
def _lista(itens, formatar) -> str:
    return "\n".join(formatar(i) for i in itens) if itens else tc("sessoes.md.nada")


def diario_para_markdown(diario: DiarioSessao, numero: int, notas: str, data: str) -> str:
    linhas = [
        "---",
        f"type: {tc('sessoes.tipo')}",
        f"session: {numero}",
        f"date: {data}",
        f"tags: [{tc('sessoes.tipo')}]",
        "---",
        f"# {tc('sessoes.nome_arquivo', numero=numero)}: {diario.titulo}",
        "",
        f"> {tc('sessoes.md.aviso')}",
        "",
        tc("sessoes.md.aconteceu"),
        _lista(diario.cenas, lambda c: f"- **{c.titulo}:** {c.resumo}"),
        "",
        tc("sessoes.md.nasceu"),
        _lista(diario.nascidos_na_mesa, lambda n: f"- **[[{n.nome}]]** ({n.tipo}): {n.descricao}"),
        "",
        tc("sessoes.md.contradiz"),
        _lista(diario.contradicoes, lambda c: tc("sessoes.md.contradicao", dito=c.dito_na_mesa,
                                                  escrito=c.escrito_no_mundo, arquivo=c.arquivo, sugestao=c.sugestao)),
        "",
        tc("sessoes.md.segredos"),
        _lista(diario.segredos_em_risco, lambda s: f"- **{s.segredo}** ({s.arquivo}): {s.situacao}"),
        "",
        tc("sessoes.md.pontas"),
        _lista(diario.pontas_soltas, lambda p: f"- {p}"),
        "",
        tc("sessoes.md.conclusoes"),
        _lista(diario.conclusoes, lambda c: f"- {c}"),
        "",
        tc("sessoes.md.anotacoes"),
        notas.strip(),
    ]
    return "\n".join(linhas).rstrip() + "\n"


def finalizar_sessao(notas: str, numero: int = None) -> str:
    """Analisa as anotações contra o mundo e grava o diário. Devolve o caminho do diário."""
    notas = (notas or "").strip()
    if not notas:
        raise ErroSessao(t("sessoes.erro_vazia"))
    numero = numero or proximo_numero()
    destino = caminho_diario(numero)
    if destino.exists():
        raise ErroSessao(t("sessoes.erro_existe", nome=destino.name))
    salvar_notas(notas)                                     # garante que nada se perde se a IA falhar
    ev.log(t("sessoes.log_analisando", numero=numero))
    cg.force_rebuild_world_context()                        # o diário compara com o mundo como está agora
    if pu.is_cancelled():
        return None
    resposta = au.ask_ai(
        contents=carregar_prompt("sessao_diario_usuario", numero=numero, notas=notas),
        system_instruction=carregar_prompt("sessao_diario_sistema"),
        temperature=0.3,
        response_schema=DiarioSessao,
        use_world_context=True,
    )
    diario = DiarioSessao.model_validate_json(ex.remover_markdown_fences(str(resposta)))
    destino.parent.mkdir(parents=True, exist_ok=True)
    data = datetime.now().strftime("%Y-%m-%d")
    pu.gravar_markdown(destino, diario_para_markdown(diario, numero, notas, data), segredo=True)
    (_pasta_dados() / f"sessao_{numero}_anotacoes.md").write_text(notas, encoding="utf-8")   # cópia de segurança
    salvar_notas("")                                        # a próxima sessão começa em branco
    ev.log(t("sessoes.log_pronto", nome=destino.name))
    return str(destino)


def relatorio_para_worldbuilder(caminho_diario_md: str) -> str:
    """As seções "O que nasceu na mesa" e "O que contradiz o mundo" do diário, para o plano do WorldBuilder."""
    texto = Path(caminho_diario_md).read_text(encoding="utf-8", errors="ignore")
    secoes, atual = [], None
    for linha in propriedades.corpo_limpo(texto).splitlines():
        if linha.startswith("## "):
            atual = linha if linha.strip() in (tc("sessoes.md.nasceu").strip(), tc("sessoes.md.contradiz").strip()) else None
        if atual is not None:
            secoes.append(linha)
    return tc("sessoes.relatorio_wb", nome=Path(caminho_diario_md).stem) + "\n\n" + "\n".join(secoes).strip()
