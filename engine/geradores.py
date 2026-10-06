"""
Geradores estruturados sobre um arquivo (nível médio):
  - Aventura 5-Room (com ficha do oponente e mapa de batalha da sala final)
  - Testes de Conhecimento
  - Ficha de Combate de NPC ou monstro (5e conferida pelo SRD; outros sistemas em texto)

Usados pela aba Requisições e pelo WorldBuilder. Todos recebem a Requisição (estilo,
diretrizes extras, referências, dados de mesa...) e preservam a seção "Notas do Mestre".
Prompts em locale/<idioma>/prompts/wb_aventura_*.md, wb_conhecimento_*.md e ficha_*.md.
"""
import shutil
from pathlib import Path

import core.ai_image as aimg
import core.ai_utils as au
import core.eventos as ev
import engine.dnd_schemas as dnd
import engine.expander as ex
import engine.fichas as fichas
import engine.historico as hist
import engine.knowledge_schemas as ks
import engine.notas as notas
import engine.project_utils as pu
import engine.style_manager as estilo
from core.i18n import t, tc
from core.prompts import carregar_prompt


def _contexto_requisicao(arquivo: Path, requisicao):
    """(corpo do arquivo, seção de notas, bloco da requisição, bloco das notas, escolhas de estilo)."""
    corpo, secao = notas.separar(arquivo.read_text(encoding="utf-8", errors="ignore"))
    return (corpo, secao, requisicao.bloco_prompt() if requisicao else "",
            notas.bloco_para_prompt(arquivo, secao), requisicao.escolhas_estilo() if requisicao else None)


def _gravar(arquivo: Path, texto: str, secao_notas: str, requisicao):
    """Grava o que o gerador escreveu mantendo as propriedades (YAML) que o arquivo já tinha."""
    original = arquivo.read_text(encoding="utf-8", errors="ignore") if arquivo.exists() else None
    hist.arquivar_versao_para_historico(arquivo)
    pu.gravar_markdown(arquivo, notas.reanexar(texto, secao_notas), original=original,
                       segredo=True if requisicao and requisicao.segredo else None)


def gerar_aventura_completa(path, reason=None, requisicao=None):
    arquivo = Path(path)
    reason = reason or (requisicao.objetivo if requisicao else "") or tc("acoes.padrao_aventura", nome=arquivo.name)
    ev.log(t("wb.log_aventura", caminho=path, objetivo=reason))
    if not arquivo.is_file():
        ev.log(t("wb.log_arquivo_invalido", caminho=arquivo))
        return False

    ex.marcar_processamento(arquivo, True)
    try:
        corpo, secao, bloco_req, bloco_notas, escolhas = _contexto_requisicao(arquivo, requisicao)
        resposta = au.ask_ai(
            contents=carregar_prompt("wb_aventura_usuario", arquivo=arquivo.name, objetivo=reason, conteudo=corpo,
                                     requisicao=bloco_req, notas=bloco_notas),
            system_instruction=carregar_prompt("wb_aventura_sistema", estilo=ex.carregar_diretrizes_estilo(escolhas)),
            temperature=requisicao.temperatura(0.7) if requisicao else 0.7,
            response_schema=dnd.ModuloAventura5Rooms, use_world_context=True)
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

        _gravar(arquivo, dnd.aventura_5rooms_para_markdown(aventura), secao, requisicao)
        ev.log(t("wb.log_aventura_ok", nome=arquivo.name))
        return True
    except Exception as e:
        ev.log(t("wb.log_aventura_erro", erro=e))
        return False
    finally:
        ex.marcar_processamento(arquivo, False)


def gerar_tabelas_de_conhecimento(path, foco_especifico=None, requisicao=None):
    foco_especifico = foco_especifico or (requisicao.objetivo if requisicao else "") or tc("acoes.padrao_conhecimento")
    ev.log(t("wb.log_conhecimento", caminho=path))
    arquivo = Path(path)
    if not arquivo.is_file():
        ev.log(t("wb.log_arquivo_invalido", caminho=arquivo))
        return False
    try:
        corpo, secao, bloco_req, bloco_notas, escolhas = _contexto_requisicao(arquivo, requisicao)
        resposta = au.ask_ai(
            contents=carregar_prompt("wb_conhecimento_usuario", arquivo=arquivo.name, conteudo=corpo, foco=foco_especifico,
                                     requisicao=bloco_req, notas=bloco_notas),
            system_instruction=carregar_prompt("wb_conhecimento_sistema", estilo=ex.carregar_diretrizes_estilo(escolhas)),
            temperature=requisicao.temperatura(0.5) if requisicao else 0.5,
            response_schema=ks.CompendioConhecimento, use_world_context=True)
        if not resposta:
            ev.log(t("wb.log_retorno_vazio", nome=arquivo.name))
            return False
        compendio = ks.CompendioConhecimento.model_validate_json(ex.remover_markdown_fences(str(resposta)))
        _gravar(arquivo, corpo.rstrip() + "\n" + ks.compendio_para_markdown(compendio) + "\n", secao, requisicao)
        ev.log(t("wb.log_conhecimento_ok", nome=arquivo.name))
        return True
    except Exception as e:
        ev.log(t("wb.log_conhecimento_erro", erro=e))
        return False


def gerar_ficha(path, foco=None, requisicao=None, tipo: str = "npc") -> bool:
    """Gera (ou refaz) a seção 'Ficha de Combate' do arquivo no sistema de regras do projeto."""
    arquivo = Path(path)
    foco = foco or (requisicao.objetivo if requisicao else "") or ""
    sistema = estilo.sistema_ativo()
    ev.log(t("ficha.log_inicio", nome=arquivo.name, sistema=t(f"style.sistema.{sistema}")))
    if not arquivo.is_file():
        ev.log(t("wb.log_arquivo_invalido", caminho=arquivo))
        return False

    ex.marcar_processamento(arquivo, True)
    try:
        corpo, secao, bloco_req, bloco_notas, escolhas = _contexto_requisicao(arquivo, requisicao)
        estruturada = sistema == "dnd5e"
        resposta = au.ask_ai(
            contents=carregar_prompt("ficha_usuario", arquivo=arquivo.name, conteudo=corpo, foco=foco,
                                     tipo=tc(f"ficha.tipo.{'monstro' if tipo == 'monstro' else 'npc'}"),
                                     formato=tc("ficha.formato_5e" if estruturada else "ficha.formato_livre",
                                                titulo=tc("ficha.titulo")),
                                     requisicao=bloco_req, notas=bloco_notas),
            system_instruction=carregar_prompt("ficha_sistema", sistema=t(f"style.sistema.{sistema}"),
                                               estilo=ex.carregar_diretrizes_estilo(escolhas)),
            temperature=requisicao.temperatura(0.4) if requisicao else 0.4,
            response_schema=fichas.FichaCombate5e if estruturada else None, use_world_context=True)
        if not resposta or not str(resposta).strip():
            ev.log(t("wb.log_retorno_vazio", nome=arquivo.name))
            return False
        if estruturada:
            secao_ficha = fichas.ficha_5e_para_markdown(
                fichas.FichaCombate5e.model_validate_json(ex.remover_markdown_fences(str(resposta))))
        else:
            secao_ficha = ex.remover_markdown_fences(str(resposta)).strip()
            if not secao_ficha.startswith("## "):
                secao_ficha = f"## {tc('ficha.titulo')}\n{secao_ficha}"
        _gravar(arquivo, fichas.substituir_secao_ficha(corpo, secao_ficha), secao, requisicao)
        ev.log(t("ficha.log_ok", nome=arquivo.name))
        return True
    except Exception as e:
        ev.log(t("ficha.log_erro", nome=arquivo.name, erro=e))
        return False
    finally:
        ex.marcar_processamento(arquivo, False)
