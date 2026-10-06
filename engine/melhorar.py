"""
Nível médio: Melhorar Arquivo — a IA reescreve (ou acrescenta a) um arquivo inteiro seguindo um objetivo.

Usado pela aba Requisições (que define estilo, referências, modo...) e pelo WorldBuilder
(que passa o Cânone da campanha). A seção "Notas do Mestre" do arquivo vai para a IA como
orientação e é preservada intacta. A versão anterior vai para o histórico.
Prompts em locale/<idioma>/prompts/melhorar_*.md.
"""
from pathlib import Path

import core.ai_utils as au
import core.eventos as ev
import core.propriedades as propriedades
import engine.esquemas as esquemas
import engine.expander as ex
import engine.historico as hist
import engine.notas as notas
import engine.project_utils as pu
from core.i18n import t, tc
from core.prompts import carregar_prompt


def melhorar_arquivo(caminho, objetivo: str = None, canon: str = None, requisicao=None, auditoria: str = None) -> bool:
    """Reescreve o arquivo com a IA (ou só acrescenta, no modo 'acrescentar'). Devolve True se gravou."""
    arquivo = Path(caminho)
    objetivo = objetivo or (requisicao.objetivo if requisicao else "") or tc("acoes.padrao_melhorar")
    ev.log(t("wb.log_melhorar", caminho=arquivo, motivo=objetivo))
    if not arquivo.is_file():
        ev.log(t("wb.log_arquivo_invalido", caminho=arquivo))
        return False

    ex.marcar_processamento(arquivo, True)
    try:
        original = arquivo.read_text(encoding="utf-8", errors="ignore")
        corpo, secao_notas = notas.separar(original)
        # Referência do WorldBuilder: o Cânone da campanha ou o relatório da Auditoria de Lore
        if canon:
            bloco_canon = carregar_prompt("melhorar_canon", canon=canon)
        elif auditoria:
            bloco_canon = carregar_prompt("melhorar_auditoria", relatorio=auditoria)
        else:
            bloco_canon = ""
        escolhas = requisicao.escolhas_estilo() if requisicao else None
        texto = au.ask_ai(
            contents=carregar_prompt("melhorar_usuario", objetivo=objetivo, conteudo=corpo, canon=bloco_canon,
                                     requisicao=requisicao.bloco_prompt() if requisicao else "",
                                     notas=notas.bloco_para_prompt(arquivo, secao_notas),
                                     propriedades=esquemas.bloco_prompt(original)),
            system_instruction=carregar_prompt("melhorar_sistema", arquivo=arquivo.name, objetivo=objetivo,
                                               estilo=ex.carregar_diretrizes_estilo(escolhas)),
            temperature=requisicao.temperatura(0.4) if requisicao else 0.4)
        if not texto or not str(texto).strip():
            ev.log(t("wb.log_retorno_vazio", nome=arquivo.name))
            return False
        bruto = ex.remover_markdown_fences(str(texto))
        resultado = notas.separar(bruto)[0]
        if requisicao and requisicao.modo == "acrescentar":
            resultado = corpo.rstrip() + "\n\n" + propriedades.separar(resultado)[1].strip() + "\n"
        hist.arquivar_versao_para_historico(arquivo)
        # Propriedades (YAML do Obsidian): as do arquivo ficam; a IA só completa as chaves vazias do esquema
        novo = esquemas.aplicar(original, notas.reanexar(resultado, secao_notas), saida_ia=bruto)
        pu.gravar_markdown(arquivo, novo, segredo=True if requisicao and requisicao.segredo else None)
        ev.log(t("wb.log_melhorado", nome=arquivo.name))
        return True
    except Exception as e:
        ev.log(t("wb.log_erro_melhorar", nome=arquivo.name, erro=e))
        return False
    finally:
        ex.marcar_processamento(arquivo, False)
