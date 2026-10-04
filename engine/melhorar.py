"""
Nível médio: Melhorar Arquivo — a IA reescreve um arquivo inteiro seguindo um objetivo.

Usado pelo menu do Editor e pelo WorldBuilder (que passa o Cânone da campanha para
manter nomes e fatos consistentes). A versão anterior vai para o histórico.
Prompts em locale/<idioma>/prompts/melhorar_*.md.
"""
from pathlib import Path

import core.ai_utils as au
import core.eventos as ev
import engine.expander as ex
import engine.historico as hist
from core.i18n import t, tc
from core.prompts import carregar_prompt


def melhorar_arquivo(caminho, objetivo: str = None, canon: str = None) -> bool:
    """Reescreve o arquivo inteiro com a IA. Devolve True se gravou a nova versão."""
    arquivo = Path(caminho)
    objetivo = objetivo or tc("acoes.padrao_melhorar")
    ev.log(t("wb.log_melhorar", caminho=arquivo, motivo=objetivo))
    if not arquivo.is_file():
        ev.log(t("wb.log_arquivo_invalido", caminho=arquivo))
        return False

    ex.marcar_processamento(arquivo, True)
    try:
        conteudo = arquivo.read_text(encoding="utf-8", errors="ignore")
        bloco_canon = carregar_prompt("melhorar_canon", canon=canon) if canon else ""
        texto = au.ask_ai(
            contents=carregar_prompt("melhorar_usuario", objetivo=objetivo, conteudo=conteudo, canon=bloco_canon),
            system_instruction=carregar_prompt("melhorar_sistema", arquivo=arquivo.name, objetivo=objetivo,
                                               estilo=ex.carregar_diretrizes_estilo()),
            temperature=0.4)
        if not texto or not str(texto).strip():
            ev.log(t("wb.log_retorno_vazio", nome=arquivo.name))
            return False
        hist.arquivar_versao_para_historico(arquivo)
        arquivo.write_text(ex.remover_markdown_fences(str(texto)), encoding="utf-8")
        ev.log(t("wb.log_melhorado", nome=arquivo.name))
        return True
    except Exception as e:
        ev.log(t("wb.log_erro_melhorar", nome=arquivo.name, erro=e))
        return False
    finally:
        ex.marcar_processamento(arquivo, False)
