"""
Conselho de Criação: deliberação em 4 painéis (Arquiteto, Cronista, NPCs, Tático & Caos)
e consolidação final pelo Juiz Supremo. Prompts em locale/<idioma>/prompts/conselho_*.md.
"""
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

import core.ai_utils as au
import core.eventos as ev
import engine.expander as ex
import engine.persona_engine as pe
import engine.project_utils as pu
from core.i18n import t, tc
from core.prompts import carregar_prompt


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


def _resumo_personas(conteudo_atual: str) -> str:
    """Personas já criadas que aparecem no arquivo, para enriquecer as falas dos NPCs."""
    linhas = []
    for nome in pe.listar_personas_disponiveis():
        if nome.lower() in conteudo_atual.lower():
            dados, _ = pe.carregar_persona(nome)
            if dados:
                linhas.append(tc("conselho.linha_persona", nome=dados.get("nome"), ocupacao=dados.get("ocupacao_ou_papel"),
                                 alinhamento=dados.get("alinhamento_moral"), bordao=dados.get("bordao_ou_frase_marcante")))
    return "\n".join(linhas) or tc("conselho.sem_personas")


# --- FASE 1: DELIBERAÇÃO ---
def executar_deliberacao_paineis(caminho_arquivo: Path, diretriz_mestre: str) -> dict:
    caminho = Path(caminho_arquivo)
    conteudo_atual = caminho.read_text(encoding="utf-8", errors="ignore")

    resposta = au.ask_ai(
        contents=carregar_prompt("conselho_deliberacao_usuario", projeto=pu.PASTA_PROJETO, arquivo=caminho.name,
                                 diretriz=diretriz_mestre, conteudo=conteudo_atual,
                                 personas=_resumo_personas(conteudo_atual), estilo=ex.carregar_diretrizes_estilo()),
        system_instruction=carregar_prompt("conselho_deliberacao_sistema"),
        temperature=0.6, response_schema=RespostaEspecialistas, use_world_context=True)
    obj = RespostaEspecialistas.model_validate_json(ex.remover_markdown_fences(str(resposta)))

    falas = [tc("conselho.fala_npc", nome=npc.nome_npc, fala=npc.reacao_primeira_pessoa) for npc in obj.falas_npcs]
    return {
        "arquiteto": obj.arquiteto.strip(),
        "cronista": obj.cronista.strip(),
        "npcs": "\n".join(falas).strip() or tc("conselho.sem_npcs"),
        "tatico_caos": obj.tatico_e_caos.strip(),
    }


# --- FASE 2: CONSOLIDAÇÃO ---
def sintetizar_e_salvar_arquivo_canonica(caminho_arquivo: Path, texto_arquiteto: str, texto_cronista: str,
                                         texto_npcs: str, texto_tatico_caos: str, diretriz_original: str) -> bool:
    """Gera o Markdown final via Juiz Supremo, arquiva a versão anterior e grava a nova no mesmo arquivo."""
    caminho = Path(caminho_arquivo)
    original = caminho.read_text(encoding="utf-8", errors="ignore")

    resposta = au.ask_ai(
        contents=carregar_prompt("conselho_juiz_usuario", projeto=pu.PASTA_PROJETO, arquivo=caminho.name,
                                 diretriz=diretriz_original, arquiteto=texto_arquiteto, cronista=texto_cronista,
                                 npcs=texto_npcs, tatico=texto_tatico_caos, original=original),
        system_instruction=carregar_prompt("conselho_juiz_sistema"),
        temperature=0.4, response_schema=DocumentoFinalConsolidado, use_world_context=True)
    decisao = DocumentoFinalConsolidado.model_validate_json(ex.remover_markdown_fences(str(resposta)))

    ex.arquivar_versao_para_historico(caminho)
    caminho.write_text(decisao.conteudo_markdown.strip() + "\n", encoding="utf-8")
    ev.log(t("conselho.log_consolidado", nome=caminho.name))
    ev.log(t("conselho.log_nota_juiz", nota=decisao.resumo_decisao_juiz))
    return True


def diretriz_padrao(nome_arquivo: str) -> str:
    """Sugestão de diretriz exibida ao carregar um arquivo no Conselho (idioma ativo)."""
    return tc("conselho.diretriz_sugerida", nome=nome_arquivo)


def diretriz_vazia() -> str:
    return tc("conselho.diretriz_vazia")
