"""
Conselho de Criação: deliberação em 4 painéis (Arquiteto, Cronista, NPCs, Tático & Caos)
e consolidação final pelo Juiz Supremo. Prompts em locale/<idioma>/prompts/conselho_*.md.

O "conselho-mor": antes de deliberar, o Conselho reúne o que as outras perspectivas já
disseram sobre o arquivo e dá prioridade a isso em vez de inventar do zero:
  - Depoimentos do Roleplay (dentro da história) -> a Voz dos NPCs usa as falas reais
  - Notas de Silent e do Mestre (fora da história) -> orientam o Arquiteto e o Cronista
  - Conversas recentes de Roleplay com personagens citados (ainda não salvas como nota)
"""
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

import core.ai_utils as au
import core.eventos as ev
import engine.expander as ex
import engine.historico as hist
import engine.notas as notas
import engine.persona_engine as pe
import engine.project_utils as pu
from core.i18n import t, tc
from core.prompts import carregar_prompt

CONVERSAS_POR_PERSONA = 6


# --- SCHEMAS PYDANTIC ---
class FalaNPC(BaseModel):
    nome_npc: str = Field(description="Nome do NPC citado no documento")
    reacao_primeira_pessoa: str = Field(description="Fala e reação em 1ª pessoa do NPC sobre os acontecimentos propostos")


class RespostaEspecialistas(BaseModel):
    arquiteto: str = Field(description="Proposta de expansão estrutural, novos fatos, locais ou ganchos")
    cronista: str = Field(description="Auditoria contra o cache do mundo: consistência com datas, deuses, facções e furos de lore")
    falas_npcs: List[FalaNPC] = Field(description="Reações de cada NPC citado no texto ou afetado pelo assunto")
    tatico_e_caos: str = Field(description="Mecânicas de jogo (CDs de perícia D&D, perigos) somadas a dilemas dramáticos e tensões")


class DocumentoFinalConsolidado(BaseModel):
    resumo_decisao_juiz: str = Field(description="Breve nota de como o Juiz Supremo resolveu os conflitos dos painéis")
    conteudo_markdown: str = Field(description="Texto final canônico completo formatado em Markdown com Callouts e Wikilinks")


def _personas_citadas(conteudo: str) -> list:
    return [nome for nome in pe.listar_personas_disponiveis() if nome.lower() in conteudo.lower()]


def _resumo_personas(conteudo_atual: str) -> str:
    """Personas já criadas que aparecem no arquivo, para enriquecer as falas dos NPCs."""
    linhas = []
    for nome in _personas_citadas(conteudo_atual):
        dados, _ = pe.carregar_persona(nome)
        if dados:
            linhas.append(tc("conselho.linha_persona", nome=dados.get("nome"), ocupacao=dados.get("ocupacao_ou_papel"),
                             alinhamento=dados.get("alinhamento_moral"), bordao=dados.get("bordao_ou_frase_marcante")))
    return "\n".join(linhas) or tc("conselho.sem_personas")


def reunir_insumos(caminho_arquivo) -> dict:
    """
    O que Roleplay, Silent e o Mestre já disseram sobre o arquivo:
    {'depoimentos': [(titulo, texto)], 'notas': [(titulo, texto)], 'conversas': [(persona, texto)]}.
    """
    caminho = Path(caminho_arquivo)
    corpo = notas.separar(caminho.read_text(encoding="utf-8", errors="ignore"))[0]
    lista = notas.listar_notas(caminho)
    depoimentos = [(n["titulo"], n["texto"]) for n in lista if n["depoimento"]]
    outras = [(n["titulo"], n["texto"]) for n in lista if not n["depoimento"]]
    conversas = []
    for nome in _personas_citadas(corpo):
        dados, historico = pe.carregar_persona(nome)
        trecho = historico[-CONVERSAS_POR_PERSONA * 2:]
        if trecho:
            fala = "\n".join(f"{tc('conselho.mestre_no_roleplay') if m.get('autor') == pe.AUTOR_INTERLOCUTOR else m.get('autor')}: "
                             f"{m.get('texto', '')}" for m in trecho)
            conversas.append((dados.get("nome", nome) if dados else nome, fala))
    return {"depoimentos": depoimentos, "notas": outras, "conversas": conversas}


def _bloco_insumos(insumos: dict) -> str:
    partes = []
    if insumos["depoimentos"]:
        partes.append(tc("conselho.insumo_depoimentos") + "\n" + "\n\n".join(f"[{tit}]\n{txt}" for tit, txt in insumos["depoimentos"]))
    if insumos["notas"]:
        partes.append(tc("conselho.insumo_notas") + "\n" + "\n\n".join(f"[{tit}]\n{txt}" for tit, txt in insumos["notas"]))
    if insumos["conversas"]:
        partes.append(tc("conselho.insumo_conversas") + "\n" + "\n\n".join(f"[{nome}]\n{txt}" for nome, txt in insumos["conversas"]))
    return ("\n" + "\n\n".join(partes) + "\n") if partes else ""


def resumo_fontes(insumos: dict) -> str:
    """Texto curto para a interface mostrar de onde vieram os insumos ('' se nenhum)."""
    partes = []
    if insumos["depoimentos"]:
        partes.append(t("cons.fonte_depoimentos", total=len(insumos["depoimentos"])))
    if insumos["notas"]:
        partes.append(t("cons.fonte_notas", total=len(insumos["notas"])))
    if insumos["conversas"]:
        partes.append(t("cons.fonte_conversas", nomes=", ".join(nome for nome, _ in insumos["conversas"])))
    return " · ".join(partes)


# --- FASE 1: DELIBERAÇÃO ---
def executar_deliberacao_paineis(caminho_arquivo: Path, diretriz_mestre: str, requisicao=None) -> dict:
    caminho = Path(caminho_arquivo)
    corpo = notas.separar(caminho.read_text(encoding="utf-8", errors="ignore"))[0]
    insumos = reunir_insumos(caminho)
    escolhas = requisicao.escolhas_estilo() if requisicao else None

    resposta = au.ask_ai(
        contents=carregar_prompt("conselho_deliberacao_usuario", projeto=pu.PASTA_PROJETO, arquivo=caminho.name,
                                 diretriz=diretriz_mestre, conteudo=corpo, personas=_resumo_personas(corpo),
                                 estilo=ex.carregar_diretrizes_estilo(escolhas), insumos=_bloco_insumos(insumos),
                                 requisicao=requisicao.bloco_prompt() if requisicao else ""),
        system_instruction=carregar_prompt("conselho_deliberacao_sistema"),
        temperature=requisicao.temperatura(0.6) if requisicao else 0.6,
        response_schema=RespostaEspecialistas, use_world_context=True)
    obj = RespostaEspecialistas.model_validate_json(ex.remover_markdown_fences(str(resposta)))

    falas = [tc("conselho.fala_npc", nome=npc.nome_npc, fala=npc.reacao_primeira_pessoa) for npc in obj.falas_npcs]
    return {
        "arquiteto": obj.arquiteto.strip(),
        "cronista": obj.cronista.strip(),
        "npcs": "\n".join(falas).strip() or tc("conselho.sem_npcs"),
        "tatico_caos": obj.tatico_e_caos.strip(),
        "fontes": resumo_fontes(insumos),
    }


# --- FASE 2: CONSOLIDAÇÃO ---
def sintetizar_e_salvar_arquivo_canonica(caminho_arquivo: Path, texto_arquiteto: str, texto_cronista: str,
                                         texto_npcs: str, texto_tatico_caos: str, diretriz_original: str,
                                         requisicao=None) -> bool:
    """Gera o Markdown final via Juiz Supremo, arquiva a versão anterior e grava a nova (Notas do Mestre preservadas)."""
    caminho = Path(caminho_arquivo)
    corpo, secao_notas = notas.separar(caminho.read_text(encoding="utf-8", errors="ignore"))

    resposta = au.ask_ai(
        contents=carregar_prompt("conselho_juiz_usuario", projeto=pu.PASTA_PROJETO, arquivo=caminho.name,
                                 diretriz=diretriz_original, arquiteto=texto_arquiteto, cronista=texto_cronista,
                                 npcs=texto_npcs, tatico=texto_tatico_caos, original=corpo,
                                 requisicao=requisicao.bloco_prompt() if requisicao else "",
                                 notas=notas.bloco_para_prompt(caminho, secao_notas)),
        system_instruction=carregar_prompt("conselho_juiz_sistema"),
        temperature=requisicao.temperatura(0.4) if requisicao else 0.4,
        response_schema=DocumentoFinalConsolidado, use_world_context=True)
    decisao = DocumentoFinalConsolidado.model_validate_json(ex.remover_markdown_fences(str(resposta)))

    original = caminho.read_text(encoding="utf-8", errors="ignore")
    hist.arquivar_versao_para_historico(caminho)
    pu.gravar_markdown(caminho, notas.reanexar(decisao.conteudo_markdown.strip(), secao_notas), original=original,
                       segredo=True if requisicao and requisicao.segredo else None)
    ev.log(t("conselho.log_consolidado", nome=caminho.name))
    ev.log(t("conselho.log_nota_juiz", nota=decisao.resumo_decisao_juiz))
    return True


def diretriz_padrao(nome_arquivo: str) -> str:
    """Sugestão de diretriz exibida ao carregar um arquivo no Conselho (idioma ativo)."""
    return tc("conselho.diretriz_sugerida", nome=nome_arquivo)


def diretriz_vazia() -> str:
    return tc("conselho.diretriz_vazia")
