import re
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import engine.project_utils as pu
import engine.persona_engine as pe
import core.ai_utils as au
import engine.expander as ex

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


# --- ENGINE DAS ETAPAS ---

def executar_deliberacao_paineis(caminho_arquivo: Path, diretriz_mestre: str) -> dict:
    """
    Executa a Fase 1: Gera as análises dos 4 painéis (Arquiteto, Cronista, NPCs e Tático/Caos).
    """
    caminho = Path(caminho_arquivo)
    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
        conteudo_atual = f.read()

    estilo = ex.carregar_diretrizes_estilo()

    # Busca personas já conhecidas para enriquecer a voz dos NPCs
    personas_conhecidas = pe.listar_personas_disponiveis()
    resumo_personas = ""
    for p in personas_conhecidas:
        if p.lower() in conteudo_atual.lower():
            dados, _ = pe.carregar_persona(p)
            if dados:
                resumo_personas += f"\n- {dados.get('nome')}: {dados.get('ocupacao_ou_papel')}, Alinhamento: {dados.get('alinhamento_moral')}, Visão: \"{dados.get('bordao_ou_frase_marcante')}\""

    prompt_deliberacao = f"""
Você é o Conselho Central de Criação e Worldbuilding de {pu.PASTA_PROJETO}.
Analise o arquivo alvo abaixo e delibere sobre sua expansão/consolidação.

ARQUIVO: {caminho.name}
DIRETRIZ DO MESTRE: {diretriz_mestre}

CONTEÚDO ATUAL:
{conteudo_atual}

PERSONAS JÁ REGISTRADAS VINCULADAS:
{resumo_personas or "Nenhuma registrada previamente (identifique os NPCs diretamente no texto acima)."}

# DIRETRIZES DE ESTILO:
{estilo}

SUA TAREFA:
Preencha rigorosamente os 4 campos do schema:
1. 'arquiteto': A proposta rica de evolução do documento.
2. 'cronista': Verificação de continuidade e furos históricos com o universo do cache.
3. 'falas_npcs': Identifique TODOS os personagens nomeados no arquivo e forneça a reação direta em 1ª pessoa de cada um deles.
4. 'tatico_e_caos': Desafios práticos com CDs de D&D (≤5 até 25+) misturados com dilemas morais e segredos de bastidores.
"""

    resposta_raw = au.ask_ai(
        contents=prompt_deliberacao,
        system_instruction="Você orquestra um conselho deliberativo para RPG. Seja criativo, rigoroso e fiel às vozes dos personagens.",
        temperature=0.6,
        response_schema=RespostaEspecialistas,
        use_world_context=True
    )

    json_limpo = ex.remover_markdown_fences(str(resposta_raw))
    obj = RespostaEspecialistas.model_validate_json(json_limpo)

    # Formata a lista de NPCs para texto legível no Painel 3
    texto_npcs = []
    for npc in obj.falas_npcs:
        texto_npcs.append(f"🎭 [{npc.nome_npc}]:\n\"{npc.reacao_primeira_pessoa}\"\n")

    return {
        "arquiteto": obj.arquiteto.strip(),
        "cronista": obj.cronista.strip(),
        "npcs": "\n".join(texto_npcs).strip() or "Nenhum NPC específico identificado no texto.",
        "tatico_caos": obj.tatico_e_caos.strip()
    }


def sintetizar_e_salvar_arquivo_canonica(
    caminho_arquivo: Path,
    texto_arquiteto: str,
    texto_cronista: str,
    texto_npcs: str,
    texto_tatico_caos: str,
    diretriz_original: str
) -> bool:
    """
    Executa a Fase 2: Pega os textos dos 4 painéis (com edições do usuário),
    gera o Markdown final via Juiz Supremo, arquiva a versão anterior e salva a nova.
    """
    caminho = Path(caminho_arquivo)
    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
        conteudo_original = f.read()

    prompt_juiz = f"""
Você é o Juiz Supremo e Editor Canônico de {pu.PASTA_PROJETO}.
Sua missão é consolidar o documento canônico final para: {caminho.name}
Diretriz original: {diretriz_original}

O CONSELHO DELIBEROU E O MESTRE REVISOU OS PAINÉIS:

[PAINEL 1: O ARQUITETO]
{texto_arquiteto}

[PAINEL 2: O CRONISTA]
{texto_cronista}

[PAINEL 3: REAÇÃO DOS NPCS E HABITANTES]
{texto_npcs}

[PAINEL 4: TÁTICO & CAOS]
{texto_tatico_caos}

CONTEÚDO ORIGINAL DE BASE:
{conteudo_original}

INSTRUÇÕES DO JUIZ:
- Integre a proposta do Arquiteto corrigindo os alertas do Cronista.
- Incorpore as falas e posturas dos NPCs nos diálogos, citações (> [!quote]) ou boatos.
- Adicione as tabelas de perícia ou testes mecânicos do Tático.
- Use sintaxe do Obsidian com Wikilinks [[Nome]].
- O campo 'conteudo_markdown' deve conter EXCLUSIVAMENTE o texto final do artigo para ser salvo no disco.
"""

    resposta_raw = au.ask_ai(
        contents=prompt_juiz,
        system_instruction="Você é a autoridade máxima do cânone. Escreva um documento coeso, profissional e completo.",
        temperature=0.4,
        response_schema=DocumentoFinalConsolidado,
        use_world_context=True
    )

    json_limpo = ex.remover_markdown_fences(str(resposta_raw))
    decisao = DocumentoFinalConsolidado.model_validate_json(json_limpo)

    # 1. Arquiva versão no histórico com sufixo _vXX.md
    ex.arquivar_versao_para_historico(caminho)

    # 2. Grava a versão consolidada no mesmo arquivo (mantendo links do Obsidian)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(decisao.conteudo_markdown.strip() + "\n")

    print(f"✅ [CONSELHO] Arquivo consolidado com sucesso: {caminho.name}")
    print(f"   Nota do Juiz: {decisao.resumo_decisao_juiz}")
    return True