"""
WorldBuilder: planeja ações (criar pastas/arquivos, melhorar arquivos) a partir de
um objetivo e as executa. Também gera Aventuras 5-Room e Testes de Conhecimento.
Prompts em locale/<idioma>/prompts/wb_*.md.
"""
import re
import shutil
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel

import core.ai_image as aimg
import core.ai_utils as au
import core.cache_gemini as cg
import core.config as st
import core.eventos as ev
import engine.dnd_schemas as dnd
import engine.expander as ex
import engine.knowledge_schemas as ks
import engine.project_utils as pu
from core.i18n import t, tc
from core.prompts import carregar_prompt


def resolver_caminho(path_str):
    """
    Normaliza um caminho sugerido pela IA para garantir que ele sempre
    seja interpretado como relativo à pasta raiz do projeto (CAMINHO_PROJETO).
    """
    caminho = Path(path_str)
    raiz = Path(pu.CAMINHO_PROJETO).resolve()
    if caminho.is_absolute():
        return caminho.resolve()
    partes = caminho.parts
    if partes and partes[0] == pu.PASTA_PROJETO:
        caminho = Path(*partes[1:]) if len(partes) > 1 else Path("")
    return (raiz / caminho).resolve()


def obter_conteudo_template(nome_template: Optional[str]) -> str:
    """Conteúdo do template (.md) em <projeto>/Templates ou .silent_data/Templates."""
    if not nome_template or nome_template.lower() == "nenhum":
        return ""
    nome_arquivo = f"{nome_template.lower().strip()}.md"
    for caminho in (Path(pu.CAMINHO_PROJETO) / "Templates" / nome_arquivo, pu.PASTA_TEMPLATES / nome_arquivo):
        if caminho.is_file():
            try:
                conteudo = caminho.read_text(encoding="utf-8").strip()
                ev.log(t("wb.log_template", template=nome_template, arquivo=caminho.name))
                return f"\n\n{conteudo}"
            except Exception as e:
                ev.log(t("wb.log_erro_template", arquivo=caminho, erro=e))
                return ""
    ev.log(t("wb.log_template_ausente", template=nome_template, arquivo=nome_arquivo))
    return ""


class Action(BaseModel):
    type: Literal["CreateFolder", "CreateFile", "ImproveFile"]
    path: str
    priority: int
    objective: str
    template: Optional[Literal["aventura", "cidade", "local", "npc", "reinado", "nenhum"]] = "nenhum"


class ActionPlan(BaseModel):
    actions: List[Action]


# ----------------------------------------------------------------------
# PLANEJAMENTO E EXECUÇÃO
# ----------------------------------------------------------------------
def taskplanner(reason: Optional[str] = None):
    reason = reason or tc("wb.objetivo_padrao")
    ev.log(t("wb.log_inicio"))

    config = st.carregar_configuracoes()
    allow_folder = config.get("wb_allow_create_folder", True)
    allow_file = config.get("wb_allow_create_file", True)
    allow_improve = config.get("wb_allow_improve_file", True)

    ferramentas = [nome for nome, ativo in (("CreateFolder", allow_folder), ("CreateFile", allow_file),
                                            ("ImproveFile", allow_improve)) if ativo]
    if not ferramentas:
        ev.log(t("wb.log_sem_ferramentas"))
        return
    if pu.is_cancelled():
        ev.log(t("wb.log_interrompido"))
        return

    instrucao = carregar_prompt(
        "wb_planner_sistema", objetivo=reason, ferramentas="\n".join(ferramentas), projeto=pu.PASTA_PROJETO,
        restricao_pastas="" if allow_folder else carregar_prompt("wb_planner_restricao_pastas"))

    try:
        resposta = au.ask_ai(contents=carregar_prompt("wb_planner_usuario", objetivo=reason),
                             system_instruction=instrucao, temperature=0.4, response_schema=ActionPlan,
                             use_world_context=True)
        plano = ActionPlan.model_validate_json(ex.remover_markdown_fences(str(resposta)))

        acoes_filtradas = []
        for acao in plano.actions:
            permitido = {"CreateFolder": allow_folder, "CreateFile": allow_file, "ImproveFile": allow_improve}[acao.type]
            if permitido:
                acoes_filtradas.append(acao)
            else:
                ev.log(t("wb.log_bloqueada", tipo=acao.type))

        acoes = sorted([a.model_dump() for a in acoes_filtradas], key=lambda x: x.get("priority", 0), reverse=True)
        # Mostra o plano na página do WorldBuilder antes de executar
        ev.emitir("wb.plano", acoes)
        if acoes:
            enactchoices(acoes)
        else:
            ev.log(t("wb.log_nada_a_fazer"))
        if pu.is_cancelled():
            ev.log(t("wb.log_interrompido"))
            return
    except Exception as e:
        ev.log(t("wb.log_erro_planner", erro=e))

    ex.processar_arquivos()
    ev.log(t("wb.log_fim"))


def enactchoices(actions):
    ev.log(t("wb.log_executando", total=len(actions)))
    for indice, action in enumerate(actions):
        if pu.is_cancelled():
            ev.log(t("wb.log_interrompido"))
            return
        tipo = action["type"]
        path = action.get("path", "")
        objective = action.get("objective", "")
        template = action.get("template", "nenhum")

        ev.emitir("wb.acao", {"indice": indice, "estado": "executando"})
        resultado = False
        try:
            if tipo == "CreateFolder":
                resultado = createfolder(path, objective)
            elif tipo == "CreateFile":
                resultado = createfile(path, objective, template)
            elif tipo == "ImproveFile":
                resultado = improvefile(path, objective)
        finally:
            # Registro thread-safe no changelog.jsonl (com o resultado da ação)
            registro = {"timestamp": pu.currentdate(), "action": tipo, "path": path, "template": template,
                        "objective": objective, "result": bool(resultado)}
            pu.anexar_jsonl_seguro(pu.log_path("changelog.jsonl"), registro, pu.LOCK_CHANGELOG)
            ev.emitir("wb.acao", {"indice": indice, "estado": "concluida" if resultado else "falhou", "registro": registro})

        ex.processar_arquivos()
        ev.log(t("wb.log_reconstruindo"))
        cg.force_rebuild_world_context()
    ev.log(t("wb.log_execucao_fim"))


def createfolder(path, reason):
    ev.log(t("wb.log_criar_pasta", caminho=path, motivo=reason))
    if not st.carregar_configuracoes().get("wb_allow_create_folder", True):
        ev.log(t("wb.log_pasta_desabilitada"))
        return False
    try:
        raiz = Path(pu.CAMINHO_PROJETO).resolve()
        destino = resolver_caminho(path)
        if not destino.is_relative_to(raiz):
            ev.log(t("wb.log_fora_da_raiz"))
            return False
        parecido = pu.existe_nome_parecido(destino.name, destino.parent)
        if parecido:
            ev.log(t("wb.log_nome_parecido", nome=destino.name, existente=parecido))
            return False
        if destino.exists():
            ev.log(t("wb.log_ja_existe", caminho=destino))
            return False
        destino.mkdir(parents=True, exist_ok=True)
        ev.log(t("wb.log_pasta_criada", caminho=destino))
        return True
    except Exception as e:
        ev.log(t("wb.log_erro_pasta", erro=e))
        return False


def createfile(path, reason, template="nenhum"):
    ev.log(t("wb.log_criar_arquivo", caminho=path, template=template, motivo=reason))
    try:
        raiz = Path(pu.CAMINHO_PROJETO).resolve()
        arquivo = resolver_caminho(path)
        if not arquivo.is_relative_to(raiz):
            ev.log(t("wb.log_fora_da_raiz"))
            return False
        # Acrescenta .md sem usar with_suffix(), que trocaria o trecho após um ponto do nome ("St. Varis" -> "St.md")
        if arquivo.suffix.lower() != ".md":
            arquivo = arquivo.with_name(arquivo.name + ".md")

        if not arquivo.parent.exists():
            if not st.carregar_configuracoes().get("wb_allow_create_folder", True):
                ev.log(t("wb.log_pasta_inexistente", nome=arquivo.name, pasta=arquivo.parent.name))
                return False
            arquivo.parent.mkdir(parents=True, exist_ok=True)

        parecido = pu.existe_nome_parecido(arquivo.name, arquivo.parent)
        if parecido:
            ev.log(t("wb.log_nome_parecido", nome=arquivo.name, existente=parecido))
            return False
        if arquivo.exists():
            ev.log(t("wb.log_ja_existe", caminho=arquivo))
            return False

        titulo = re.sub(r"_v\d+$", "", arquivo.stem)
        conteudo = tc("wb.stub_arquivo", titulo=titulo, marcador_rascunho=tc("marcador.rascunho"), motivo=reason) \
            + "\n" + obter_conteudo_template(template) + "\n"
        arquivo.write_text(conteudo, encoding="utf-8")
        ev.log(t("wb.log_arquivo_criado", caminho=arquivo))
        # Usa o caminho final (já com .md); o 'path' original da IA pode não ter extensão
        improvefile(str(arquivo), reason)
        return True
    except Exception as e:
        ev.log(t("wb.log_erro_arquivo", caminho=path, erro=e))
        return False


def improvefile(path, reason=None):
    reason = reason or tc("acoes.padrao_melhorar")
    ev.log(t("wb.log_melhorar", caminho=path, motivo=reason))
    arquivo = resolver_caminho(path)
    if not arquivo.is_file():
        ev.log(t("wb.log_arquivo_invalido", caminho=arquivo))
        return False

    ex.marcar_processamento(arquivo, True)
    try:
        conteudo = arquivo.read_text(encoding="utf-8", errors="ignore")
        texto = au.ask_ai(
            contents=carregar_prompt("wb_melhorar_usuario", objetivo=reason, conteudo=conteudo),
            system_instruction=carregar_prompt("wb_melhorar_sistema", arquivo=arquivo.name, objetivo=reason),
            temperature=0.4)
        if not texto:
            ev.log(t("wb.log_retorno_vazio", nome=arquivo.name))
            return False
        ex.arquivar_versao_para_historico(arquivo)
        arquivo.write_text(ex.remover_markdown_fences(texto), encoding="utf-8")
        ev.log(t("wb.log_melhorado", nome=arquivo.name))
        return True
    except Exception as e:
        ev.log(t("wb.log_erro_melhorar", nome=arquivo.name, erro=e))
        return False
    finally:
        ex.marcar_processamento(arquivo, False)


# ----------------------------------------------------------------------
# AVENTURA 5-ROOM E TESTES DE CONHECIMENTO
# ----------------------------------------------------------------------
def gerar_aventura_completa(path, reason=None):
    arquivo = resolver_caminho(path)
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

        ex.arquivar_versao_para_historico(arquivo)
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
    arquivo = resolver_caminho(path)
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
        ex.arquivar_versao_para_historico(arquivo)
        arquivo.write_text(conteudo.rstrip() + "\n" + ks.compendio_para_markdown(compendio) + "\n", encoding="utf-8")
        ev.log(t("wb.log_conhecimento_ok", nome=arquivo.name))
        return True
    except Exception as e:
        ev.log(t("wb.log_conhecimento_erro", erro=e))
        return False
