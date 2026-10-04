"""
Geradores estruturados sobre um arquivo: Aventura 5-Room (com ficha do oponente e mapa
de batalha da sala final) e Testes de Conhecimento. Usados pelo menu do Editor e pelo
WorldBuilder. Prompts em locale/<idioma>/prompts/wb_aventura_*.md e wb_conhecimento_*.md.
"""
import shutil
from pathlib import Path

import core.ai_image as aimg
import core.ai_utils as au
import core.eventos as ev
import engine.dnd_schemas as dnd
import engine.expander as ex
import engine.historico as hist
import engine.knowledge_schemas as ks
from core.i18n import t, tc
from core.prompts import carregar_prompt


def gerar_aventura_completa(path, reason=None):
    arquivo = Path(path)
    reason = reason or tc("acoes.padrao_aventura", nome=arquivo.name)
    ev.log(t("wb.log_aventura", caminho=path, objetivo=reason))
    if not arquivo.is_file():
        ev.log(t("wb.log_arquivo_invalido", caminho=arquivo))
        return False

    ex.marcar_processamento(arquivo, True)
    try:
        conteudo = arquivo.read_text(encoding="utf-8", errors="ignore")
        resposta = au.ask_ai(
            contents=carregar_prompt("wb_aventura_usuario", arquivo=arquivo.name, objetivo=reason, conteudo=conteudo),
            system_instruction=carregar_prompt("wb_aventura_sistema", estilo=ex.carregar_diretrizes_estilo()),
            temperature=0.7, response_schema=dnd.ModuloAventura5Rooms, use_world_context=True)
        if not resposta:
            ev.log(t("wb.log_retorno_vazio", nome=arquivo.name))
            return False
        aventura = dnd.ModuloAventura5Rooms.model_validate_json(ex.remover_markdown_fences(str(resposta)))

        # Battlemap da Sala 4 (clímax), copiado para a pasta da aventura
        try:
            sala4 = aventura.sala4
            ev.log(t("wb.log_battlemap", sala=sala4.titulo_sala))
            mapa = aimg.gerar_battlemap_boss(nome_sala=sala4.titulo_sala, descricao_ambiente=sala4.narracao)
            if mapa and Path(mapa).exists():
                shutil.copy2(mapa, arquivo.parent / Path(mapa).name)
                sala4.mapa_imagem = Path(mapa).name
                ev.log(t("wb.log_battlemap_ok", nome=Path(mapa).name))
        except Exception as e:
            ev.log(t("wb.log_battlemap_erro", erro=e))

        hist.arquivar_versao_para_historico(arquivo)
        arquivo.write_text(dnd.aventura_5rooms_para_markdown(aventura), encoding="utf-8")
        ev.log(t("wb.log_aventura_ok", nome=arquivo.name))
        return True
    except Exception as e:
        ev.log(t("wb.log_aventura_erro", erro=e))
        return False
    finally:
        ex.marcar_processamento(arquivo, False)


def gerar_tabelas_de_conhecimento(path, foco_especifico=None):
    foco_especifico = foco_especifico or tc("acoes.padrao_conhecimento")
    ev.log(t("wb.log_conhecimento", caminho=path))
    arquivo = Path(path)
    if not arquivo.is_file():
        ev.log(t("wb.log_arquivo_invalido", caminho=arquivo))
        return False
    try:
        conteudo = arquivo.read_text(encoding="utf-8", errors="ignore")
        resposta = au.ask_ai(
            contents=carregar_prompt("wb_conhecimento_usuario", arquivo=arquivo.name, conteudo=conteudo, foco=foco_especifico),
            system_instruction=carregar_prompt("wb_conhecimento_sistema"),
            temperature=0.5, response_schema=ks.CompendioConhecimento, use_world_context=True)
        if not resposta:
            ev.log(t("wb.log_retorno_vazio", nome=arquivo.name))
            return False
        compendio = ks.CompendioConhecimento.model_validate_json(ex.remover_markdown_fences(str(resposta)))
        hist.arquivar_versao_para_historico(arquivo)
        arquivo.write_text(conteudo.rstrip() + "\n" + ks.compendio_para_markdown(compendio) + "\n", encoding="utf-8")
        ev.log(t("wb.log_conhecimento_ok", nome=arquivo.name))
        return True
    except Exception as e:
        ev.log(t("wb.log_conhecimento_erro", erro=e))
        return False
