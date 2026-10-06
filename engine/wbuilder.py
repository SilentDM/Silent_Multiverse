"""
WorldBuilder (nível alto): transforma uma ideia em um projeto de campanha completo.

Três etapas, com dois pontos de revisão do Mestre:
  1. Cânone   — a IA lê a ideia e o projeto e escreve uma ficha oficial (nomes, fatos,
                relações e segredos) em <projeto>/Canon/<título>.md, marcada como segredo.
                O Mestre edita à vontade; as etapas seguintes leem o arquivo do disco.
  2. Plano    — a IA propõe a lista de arquivos; o programa valida (sem IA) e o Mestre
                marca/desmarca e edita cada item.
  3. Execução — por fases (mundo → lugares → pessoas → ameaças → aventuras), usando as
                ferramentas de nível médio (Melhorar Arquivo) e os geradores estruturados.

Os níveis menores são outras ferramentas: tag TODO (Expander) e Melhorar Arquivo.
O estado fica numa sessão por projeto (.silent_data/logs/worldbuilder/<projeto>.json),
então a página se recupera após reiniciar e uma execução interrompida continua de onde parou.
Prompts em locale/<idioma>/prompts/wb_*.md.
"""
import json
import re
import threading
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

import core.ai_utils as au
import core.cache_gemini as cg
import core.config as st
import core.eventos as ev
import engine.expander as ex
import engine.geradores as geradores
import engine.historico as hist
import engine.melhorar as melhorar
import core.propriedades as propriedades
import engine.project_utils as pu
import engine.requisicao as requisicao
import engine.style_manager as estilo
from core.i18n import t, tc
from core.prompts import carregar_prompt

TIPOS = ("CreateFolder", "CreateFile", "CreateNPC", "CreateMonster", "ImproveFile", "GenerateAdventure",
         "GenerateLoreChecks")
TIPOS_QUE_CRIAM = ("CreateFile", "CreateNPC", "CreateMonster", "GenerateAdventure")
TEMPLATES = ("aventura", "cidade", "local", "monstro", "npc", "reinado", "nenhum")
TEMPLATE_DO_TIPO = {"CreateNPC": "npc", "CreateMonster": "monstro"}
CATEGORIAS = ("reino", "cidade", "local", "npc", "monstro", "faccao", "aventura", "outro")
FASES = (1, 2, 3, 4, 5)
PERMISSOES = {
    "CreateFolder": "wb_allow_create_folder",
    "CreateFile": "wb_allow_create_file",
    "CreateNPC": "wb_allow_create_file",
    "CreateMonster": "wb_allow_create_file",
    "ImproveFile": "wb_allow_improve_file",
    "GenerateAdventure": "wb_allow_generators",
    "GenerateLoreChecks": "wb_allow_generators",
}
MAX_ACOES_PADRAO = 25
PASTA_CANON = "Canon"

ETAPA_INICIO, ETAPA_CANON, ETAPA_PLANO, ETAPA_CONCLUIDA = "inicio", "canon", "plano", "concluida"
ORIGEM_IDEIA, ORIGEM_AUDITORIA = "ideia", "auditoria"     # de onde veio o plano: Cânone ou relatório da Auditoria
_lock_sessao = threading.Lock()


class ErroWorldBuilder(Exception):
    """Falha esperada com mensagem pronta para o Mestre (sem cânone, sem plano...)."""


# ----------------------------------------------------------------------
# SCHEMAS DA IA
# ----------------------------------------------------------------------
class EntidadeCanon(BaseModel):
    nome: str = Field(description="Nome oficial da entidade, exatamente como deve ser usado em todos os arquivos")
    categoria: Literal["reino", "cidade", "local", "npc", "monstro", "faccao", "aventura", "outro"] = Field(
        description="Tipo da entidade")
    resumo_publico: str = Field(description="O que pode ser conhecido pelos jogadores, em 1 a 3 frases")
    segredo_do_mestre: str = Field(default="", description="O que só o Mestre sabe sobre ela (vazio se não houver)")
    eh_segredo: bool = Field(default=False, description="True se a própria existência da entidade deve ficar escondida dos jogadores")
    relacoes: List[str] = Field(default_factory=list, description="Nomes de outras entidades ligadas a esta")


class CanonCampanha(BaseModel):
    titulo: str = Field(description="Título curto da campanha ou do arco")
    premissa: str = Field(description="A ideia central em um parágrafo")
    visao_geral_publica: str = Field(description="O que os personagens dos jogadores sabem ou podem descobrir facilmente")
    entidades: List[EntidadeCanon] = Field(description="Todos os reinos, lugares, pessoas, facções, monstros e aventuras da ideia, com nomes definitivos")
    segredos_principais: List[str] = Field(default_factory=list, description="As verdades escondidas da campanha")
    linha_do_tempo: List[str] = Field(default_factory=list, description="Eventos em ordem cronológica, do passado ao presente")


class Action(BaseModel):
    type: Literal["CreateFolder", "CreateFile", "CreateNPC", "CreateMonster", "ImproveFile", "GenerateAdventure",
                  "GenerateLoreChecks"] = Field(description="Ferramenta a usar")
    path: str = Field(description="Caminho do arquivo ou pasta, a partir da pasta do projeto")
    priority: int = Field(description="Prioridade dentro da fase (maior primeiro)")
    objective: str = Field(description="O que este arquivo deve conter ou o que deve mudar, citando os nomes do cânone")
    template: Optional[Literal["aventura", "cidade", "local", "monstro", "npc", "reinado", "nenhum"]] = Field(
        default="nenhum", description="Modelo usado ao criar o arquivo")
    segredo: bool = Field(default=False, description="True se o arquivo inteiro deve ficar escondido dos jogadores")
    fase: int = Field(default=3, description="Fase: 1 mundo e reinos, 2 lugares e cidades, 3 pessoas e facções, 4 ameaças e monstros, 5 aventuras e testes de conhecimento")
    genero: str = Field(default="", description="Gênero deste arquivo (um dos ids da lista de gêneros); vazio usa o padrão do projeto")


class ActionPlan(BaseModel):
    actions: List[Action] = Field(description="Lista de ações do plano")


# ----------------------------------------------------------------------
# CAMINHOS E MODELOS
# ----------------------------------------------------------------------
def resolver_caminho(path_str) -> Path:
    """Caminho sugerido pela IA sempre relativo à pasta do projeto (aceita 'Projeto/...' e absolutos)."""
    caminho = Path(str(path_str).strip().strip("/\\"))
    raiz = Path(pu.CAMINHO_PROJETO).resolve()
    if caminho.is_absolute():
        return caminho.resolve()
    partes = caminho.parts
    if partes and partes[0] == pu.PASTA_PROJETO:
        caminho = Path(*partes[1:]) if len(partes) > 1 else Path("")
    return (raiz / caminho).resolve()


def caminho_relativo(caminho: Path) -> str:
    try:
        return Path(caminho).resolve().relative_to(Path(pu.CAMINHO_PROJETO).resolve()).as_posix()
    except ValueError:
        return str(caminho)


def _com_md(caminho: Path) -> Path:
    # Sem with_suffix(): ele trocaria o trecho após um ponto do nome ("St. Varis" -> "St.md")
    return caminho if caminho.suffix.lower() == ".md" else caminho.with_name(caminho.name + ".md")


def obter_conteudo_template(nome_template: Optional[str], genero: str = None) -> str:
    """
    Conteúdo do template (.md). Procura primeiro a versão do gênero (Templates/<gênero>/<nome>.md)
    e depois a genérica, em <projeto>/Templates, .silent_data/Templates e nos modelos do programa.
    """
    if not nome_template or nome_template.lower() == "nenhum":
        return ""
    nome_arquivo = f"{nome_template.lower().strip()}.md"
    pastas = (Path(pu.CAMINHO_PROJETO) / "Templates", pu.PASTA_TEMPLATES,
              pu.pasta_modelos_iniciais(st.obter("idioma", "pt_br")) / "Templates")
    candidatos = ([pasta / genero / nome_arquivo for pasta in pastas] if genero else []) + [pasta / nome_arquivo for pasta in pastas]
    for caminho in candidatos:
        if caminho.exists():
            try:
                ev.log(t("wb.log_template", template=nome_template, arquivo=caminho.name))
                return caminho.read_text(encoding="utf-8")
            except Exception as e:
                ev.log(t("wb.log_erro_template", arquivo=caminho, erro=e))
                return ""
    ev.log(t("wb.log_template_ausente", template=nome_template, arquivo=nome_arquivo))
    return ""


def max_acoes() -> int:
    try:
        return max(1, int(st.obter("wb_max_acoes", MAX_ACOES_PADRAO)))
    except (TypeError, ValueError):
        return MAX_ACOES_PADRAO


def tipo_permitido(tipo: str) -> bool:
    return bool(st.obter(PERMISSOES.get(tipo, ""), True))


# ----------------------------------------------------------------------
# SESSÃO
# ----------------------------------------------------------------------
def _arquivo_sessao() -> Path:
    nome = re.sub(r'[<>:"/\\|?*]', "_", str(pu.PASTA_PROJETO))
    return pu.PASTA_LOGS / "worldbuilder" / f"{nome}.json"


def _sessao_vazia() -> dict:
    return {"objetivo": "", "etapa": ETAPA_INICIO, "canon": None, "plano": [], "resumo": None,
            "origem": ORIGEM_IDEIA, "auditoria": None, "auditoria_data": None}


def carregar_sessao() -> dict:
    with _lock_sessao:
        try:
            dados = json.loads(_arquivo_sessao().read_text(encoding="utf-8"))
            return {**_sessao_vazia(), **dados}
        except Exception:
            return _sessao_vazia()


def salvar_sessao(sessao: dict):
    with _lock_sessao:
        arquivo = _arquivo_sessao()
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        temporario = arquivo.with_suffix(".tmp")
        temporario.write_text(json.dumps(sessao, ensure_ascii=False, indent=2), encoding="utf-8")
        temporario.replace(arquivo)


def nova_sessao() -> dict:
    sessao = _sessao_vazia()
    salvar_sessao(sessao)
    return sessao


def caminho_canon(sessao: dict = None):
    """Caminho absoluto do cânone da sessão (ou None se não existir mais)."""
    sessao = sessao or carregar_sessao()
    if not sessao.get("canon"):
        return None
    caminho = resolver_caminho(sessao["canon"])
    return caminho if caminho.is_file() else None


def _referencia(sessao: dict) -> dict:
    """O texto que guia cada arquivo na execução: o Cânone (ideia) ou o relatório (auditoria)."""
    if sessao.get("origem") == ORIGEM_AUDITORIA:
        return {"auditoria": sessao.get("auditoria") or ""}
    return {"canon": _ler_canon(sessao)}


def _ler_canon(sessao: dict) -> str:
    caminho = caminho_canon(sessao)
    if not caminho:
        raise ErroWorldBuilder(t("wb.erro_sem_canon"))
    return caminho.read_text(encoding="utf-8", errors="ignore")


# ----------------------------------------------------------------------
# ETAPA 1 — CÂNONE
# ----------------------------------------------------------------------
def canon_para_markdown(canon: CanonCampanha) -> str:
    linhas = [f"# {canon.titulo}", "", f"> {tc('wb.canon.aviso')}", "",
              f"## {tc('wb.canon.premissa')}", canon.premissa.strip(), "",
              f"## {tc('wb.canon.visao_publica')}", canon.visao_geral_publica.strip(), "",
              f"## {tc('wb.canon.entidades')}"]
    for entidade in canon.entidades:
        rotulo = tc(f"wb.categoria.{entidade.categoria}")
        marca = " 🤫" if entidade.eh_segredo else ""
        linhas += ["", f"### [[{entidade.nome}]] — {rotulo}{marca}",
                   f"- **{tc('wb.canon.resumo')}:** {entidade.resumo_publico.strip()}"]
        if entidade.segredo_do_mestre.strip():
            linhas.append(f"- **{tc('wb.canon.segredo')}:** {entidade.segredo_do_mestre.strip()}")
        if entidade.relacoes:
            linhas.append(f"- **{tc('wb.canon.relacoes')}:** " + ", ".join(f"[[{r}]]" for r in entidade.relacoes))
    if canon.segredos_principais:
        linhas += ["", f"## {tc('wb.canon.segredos')}"] + [f"- {s}" for s in canon.segredos_principais]
    if canon.linha_do_tempo:
        linhas += ["", f"## {tc('wb.canon.linha_do_tempo')}"] + [f"- {e}" for e in canon.linha_do_tempo]
    return "\n".join(linhas).strip() + "\n"


def _nome_seguro(texto: str) -> str:
    nome = re.sub(r'[<>:"/\\|?*\n\r\t]', "", texto).strip().strip(".")
    return nome[:80] or "Canon"


def gerar_canon(objetivo: str = None) -> str:
    """Etapa 1. Escreve o cânone e devolve o caminho absoluto do arquivo."""
    objetivo = (objetivo or "").strip() or tc("wb.objetivo_padrao")
    ev.log(t("wb.log_canon_inicio"))
    resposta = au.ask_ai(
        contents=carregar_prompt("wb_canon_usuario", objetivo=objetivo),
        system_instruction=carregar_prompt("wb_canon_sistema", estilo=ex.carregar_diretrizes_estilo()),
        temperature=0.6, response_schema=CanonCampanha, use_world_context=True)
    if not resposta:
        raise ErroWorldBuilder(t("wb.erro_resposta_vazia"))
    canon = CanonCampanha.model_validate_json(ex.remover_markdown_fences(str(resposta)))

    sessao = carregar_sessao()
    destino = caminho_canon(sessao)
    if destino:                              # gerar de novo: mesmo arquivo, versão anterior no histórico
        hist.arquivar_versao_para_historico(destino)
    else:
        pasta = Path(pu.CAMINHO_PROJETO) / PASTA_CANON
        pasta.mkdir(parents=True, exist_ok=True)
        base = _nome_seguro(canon.titulo)
        destino, n = pasta / f"{base}.md", 2
        while destino.exists():
            destino, n = pasta / f"{base} ({n}).md", n + 1
    pu.gravar_markdown(destino, canon_para_markdown(canon), segredo=True)     # só o Mestre vê o Cânone

    sessao.update(objetivo=objetivo, etapa=ETAPA_CANON, canon=caminho_relativo(destino), plano=[], resumo=None)
    salvar_sessao(sessao)
    ev.log(t("wb.log_canon_ok", caminho=caminho_relativo(destino), total=len(canon.entidades)))
    ev.emitir("wb.sessao", sessao)
    return str(destino)


# ----------------------------------------------------------------------
# ETAPA 2 — PLANO
# ----------------------------------------------------------------------
def generos_validos() -> list:
    return [ident for ident, _ in estilo.opcoes("genero")]


def _novo_item(acao: dict) -> dict:
    tipo = acao.get("type") if acao.get("type") in TIPOS else "CreateFile"
    template = TEMPLATE_DO_TIPO.get(tipo) or (acao.get("template") if acao.get("template") in TEMPLATES else "nenhum")
    genero = acao.get("genero") if acao.get("genero") in generos_validos() else ""
    try:
        fase = min(max(int(acao.get("fase", 3)), FASES[0]), FASES[-1])
    except (TypeError, ValueError):
        fase = 3
    try:
        prioridade = int(acao.get("priority", 0))
    except (TypeError, ValueError):
        prioridade = 0
    return {"type": tipo, "path": str(acao.get("path", "")).strip(), "objective": str(acao.get("objective", "")).strip(),
            "template": template, "segredo": bool(acao.get("segredo", False)), "fase": fase, "priority": prioridade,
            "genero": genero, "ativo": True, "estado": "pendente", "aviso": ""}


def _validar_item(item: dict, caminhos_criados: set):
    """Valida um item do plano (sem IA). Ajusta 'path', 'type', 'ativo' e 'aviso' no próprio dicionário."""
    item["aviso"] = ""
    raiz = Path(pu.CAMINHO_PROJETO).resolve()
    if not item["path"]:
        item.update(ativo=False, aviso=t("wb.aviso.sem_caminho"))
        return
    destino = resolver_caminho(item["path"])
    if item["type"] != "CreateFolder":
        destino = _com_md(destino)
    if not destino.is_relative_to(raiz) or destino == raiz:
        item.update(ativo=False, aviso=t("wb.aviso.fora_do_projeto"))
        return
    item["path"] = caminho_relativo(destino)

    if item["type"] == "CreateFolder" and destino.is_dir():
        item.update(ativo=False, aviso=t("wb.aviso.pasta_existe"))
        return
    if item["type"] in ("CreateFile", "CreateNPC", "CreateMonster") and destino.exists():
        item.update(type="ImproveFile", aviso=t("wb.aviso.vira_melhoria"))
    if item["type"] in ("ImproveFile", "GenerateLoreChecks") and not destino.exists() \
            and item["path"] not in caminhos_criados:
        item.update(ativo=False, aviso=t("wb.aviso.arquivo_nao_existe"))
        return
    if not tipo_permitido(item["type"]):
        item.update(ativo=False, aviso=t("wb.aviso.sem_permissao"))
        return
    if item["type"] != "CreateFolder" and not destino.parent.is_dir() and not tipo_permitido("CreateFolder") \
            and caminho_relativo(destino.parent) not in caminhos_criados:
        item.update(ativo=False, aviso=t("wb.aviso.pasta_nao_existe"))
        return
    if (item["type"] in TIPOS_QUE_CRIAM or item["type"] == "CreateFolder") and not destino.exists():
        parecido = pu.existe_nome_parecido(destino.stem if item["type"] != "CreateFolder" else destino.name, destino.parent)
        if parecido:
            item["aviso"] = t("wb.aviso.nome_parecido", nome=parecido)


def validar_plano(acoes: list) -> list:
    """Normaliza e valida o plano da IA: ordem por fase/prioridade, duplicados, permissões e limite."""
    itens = sorted((_novo_item(a) for a in acoes), key=lambda i: (i["fase"], -i["priority"]))
    vistos, criados, limite, ativos = set(), set(), max_acoes(), 0
    for item in itens:
        _validar_item(item, criados)
        # Testes de conhecimento num arquivo criado antes no plano não são repetição
        chave = (item["path"].lower(), item["type"] if item["type"] in ("CreateFolder", "GenerateLoreChecks") else "conteudo")
        if item["ativo"] and chave in vistos:
            item.update(ativo=False, aviso=t("wb.aviso.duplicado"))
        if item["ativo"]:
            vistos.add(chave)
            if item["type"] in TIPOS_QUE_CRIAM or item["type"] == "CreateFolder":
                criados.add(item["path"])
            ativos += 1
            if ativos > limite:
                item.update(ativo=False, aviso=t("wb.aviso.acima_do_limite", limite=limite))
    return itens


def _planejar(sessao: dict, prompt_sistema: str, pedido: str) -> list:
    """Pede o plano à IA, valida (sem IA) e grava na sessão. Comum ao Cânone e à Auditoria."""
    ferramentas = [tipo for tipo in TIPOS if tipo_permitido(tipo)]
    if not ferramentas:
        raise ErroWorldBuilder(t("wb.log_sem_ferramentas"))
    ev.log(t("wb.log_inicio"))
    generos = "\n".join(f'- "{ident}": {nome}' for ident, nome in estilo.opcoes("genero"))
    instrucao = carregar_prompt(
        prompt_sistema, ferramentas="\n".join(f"- {f}" for f in ferramentas), projeto=pu.PASTA_PROJETO,
        max_acoes=max_acoes(), generos=generos, genero_padrao=estilo.padrao("genero"),
        restricao_pastas="" if tipo_permitido("CreateFolder") else carregar_prompt("wb_planner_restricao_pastas"))
    resposta = au.ask_ai(contents=pedido, system_instruction=instrucao, temperature=0.3,
                         response_schema=ActionPlan, use_world_context=True)
    if not resposta:
        raise ErroWorldBuilder(t("wb.erro_resposta_vazia"))
    plano = ActionPlan.model_validate_json(ex.remover_markdown_fences(str(resposta)))
    itens = validar_plano([a.model_dump() for a in plano.actions])

    sessao.update(etapa=ETAPA_PLANO, plano=itens, resumo=None)
    salvar_sessao(sessao)
    ev.log(t("wb.log_plano_ok", total=len(itens), ativos=sum(1 for i in itens if i["ativo"])))
    ev.emitir("wb.sessao", sessao)
    return itens


def gerar_plano() -> list:
    """Etapa 2. A IA propõe as ações a partir do cânone (lido do disco, com as edições do Mestre)."""
    sessao = carregar_sessao()
    if sessao.get("origem") == ORIGEM_AUDITORIA:
        return gerar_plano_da_auditoria(sessao.get("auditoria") or "")
    pedido = carregar_prompt("wb_planner_usuario", objetivo=sessao.get("objetivo") or tc("wb.objetivo_padrao"),
                             canon=_ler_canon(sessao), max_acoes=max_acoes())
    return _planejar(sessao, "wb_planner_sistema", pedido)


def gerar_plano_da_auditoria(relatorio: str) -> list:
    """
    Plano de correção a partir do relatório da Auditoria de Lore (sem etapa de Cânone):
    cada inconsistência vira ações sobre os arquivos envolvidos, com a explicação e a
    solução do Auditor no objetivo. Substitui a sessão atual do WorldBuilder.
    """
    relatorio = (relatorio or "").strip()
    if not relatorio:
        raise ErroWorldBuilder(t("wb.erro_sem_relatorio"))
    sessao = _sessao_vazia()
    sessao.update(origem=ORIGEM_AUDITORIA, auditoria=relatorio, auditoria_data=pu.currentdate(),
                  objetivo=tc("wb.objetivo_auditoria"))
    salvar_sessao(sessao)
    ev.log(t("wb.log_auditoria_inicio"))
    pedido = carregar_prompt("wb_planner_auditoria_usuario", relatorio=relatorio, max_acoes=max_acoes())
    return _planejar(sessao, "wb_planner_auditoria_sistema", pedido)


def tem_plano_pendente() -> bool:
    """True se a sessão atual tem itens marcados que ainda não foram executados."""
    return any(i.get("ativo") and i.get("estado") != "concluida" for i in carregar_sessao().get("plano") or [])


def atualizar_item(indice: int, **campos) -> dict:
    """Edição do Mestre em um item do plano (caminho, objetivo, modelo, segredo, ativo). Revalida o item."""
    sessao = carregar_sessao()
    plano = sessao.get("plano", [])
    if not 0 <= indice < len(plano):
        raise ErroWorldBuilder(t("wb.erro_item"))
    item = plano[indice]
    for chave in ("path", "objective", "template", "segredo", "ativo", "type", "fase", "genero"):
        if chave in campos and campos[chave] is not None:
            item[chave] = campos[chave]
    if item.get("estado") != "concluida":
        quer_ativo = item["ativo"]
        criados = {i["path"] for j, i in enumerate(plano) if j != indice and i["ativo"]
                   and (i["type"] in TIPOS_QUE_CRIAM or i["type"] == "CreateFolder")}
        _validar_item(item, criados)
        if not quer_ativo:
            item["ativo"] = False
    salvar_sessao(sessao)
    return item


# ----------------------------------------------------------------------
# ETAPA 3 — EXECUÇÃO
# ----------------------------------------------------------------------
garantir_marcadores = pu.garantir_marcadores_arquivo


def _criar_esboco(arquivo: Path, item: dict, com_template: bool):
    titulo = re.sub(r"_v\d+$", "", arquivo.stem)
    conteudo = tc("wb.stub_arquivo", titulo=titulo, motivo=item["objective"])
    if com_template:
        conteudo = propriedades.juntar_template(
            conteudo + "\n", obter_conteudo_template(item.get("template"), item.get("genero") or estilo.padrao("genero")))
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    pu.gravar_markdown(arquivo, conteudo)
    ev.log(t("wb.log_arquivo_criado", caminho=caminho_relativo(arquivo)))


def _executar_item(item: dict, referencia: dict) -> bool:
    tipo = item["type"]
    destino = resolver_caminho(item["path"])
    ev.log(t("wb.log_acao", tipo=t(f"wb.tipo.{tipo}"), caminho=item["path"]))
    if tipo == "CreateFolder":
        destino.mkdir(parents=True, exist_ok=True)
        ev.log(t("wb.log_pasta_criada", caminho=item["path"]))
        return True

    arquivo = _com_md(destino)
    # Cada ação vira uma Requisição: o gênero do item (ou o do projeto) e os demais eixos padrão
    req = requisicao.nova("melhorar", arquivo, item["objective"], genero=item.get("genero") or None)
    if tipo in ("CreateFile", "CreateNPC", "CreateMonster"):
        if not arquivo.exists():
            _criar_esboco(arquivo, item, com_template=True)
        ok = melhorar.melhorar_arquivo(arquivo, item["objective"], requisicao=req, **referencia)
        if ok and tipo in ("CreateNPC", "CreateMonster"):
            ok = geradores.gerar_ficha(arquivo, item["objective"], requisicao=req,
                                       tipo="monstro" if tipo == "CreateMonster" else "npc")
    elif tipo == "ImproveFile":
        ok = melhorar.melhorar_arquivo(arquivo, item["objective"], requisicao=req, **referencia)
    elif tipo == "GenerateAdventure":
        if not arquivo.exists():
            _criar_esboco(arquivo, item, com_template=False)
        ok = geradores.gerar_aventura_completa(arquivo, reason=item["objective"], requisicao=req)
    else:  # GenerateLoreChecks
        if not arquivo.is_file():
            ev.log(t("wb.log_arquivo_invalido", caminho=item["path"]))
            return False
        ex.marcar_processamento(arquivo, True)
        try:
            ok = geradores.gerar_tabelas_de_conhecimento(arquivo, foco_especifico=item["objective"], requisicao=req)
        finally:
            ex.marcar_processamento(arquivo, False)
    if arquivo.is_file():
        garantir_marcadores(arquivo, item.get("segredo", False))
    return bool(ok)


def links_sem_arquivo(caminhos) -> list:
    """Nomes citados como [[link]] nos arquivos dados que ainda não têm arquivo no projeto."""
    import engine.arquivos as arq
    faltando = set()
    for caminho in caminhos:
        try:
            texto = Path(caminho).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for alvo in re.findall(r"(?<!!)\[\[([^\]]+)\]\]", texto):
            nome = arq.nome_do_wikilink(alvo)
            if nome and not nome.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")) \
                    and not arq.resolver_wikilink(nome):
                faltando.add(nome)
    return sorted(faltando, key=str.lower)


def executar_plano() -> dict:
    """Etapa 3. Executa os itens marcados, fase por fase. Itens já concluídos são pulados (retomada)."""
    sessao = carregar_sessao()
    referencia = _referencia(sessao)
    plano = sessao.get("plano", [])
    ordem = [i for i in sorted(range(len(plano)), key=lambda i: (plano[i]["fase"], -plano[i]["priority"]))
             if plano[i]["ativo"] and plano[i]["estado"] != "concluida"]
    if not ordem:
        raise ErroWorldBuilder(t("wb.log_nada_a_fazer"))
    ev.log(t("wb.log_executando", total=len(ordem)))

    fase_atual, tocados, falhas, interrompido = None, [], 0, False
    for indice in ordem:
        if pu.is_cancelled():
            interrompido = True
            ev.log(t("wb.log_interrompido"))
            break
        item = plano[indice]
        if item["fase"] != fase_atual:
            fase_atual = item["fase"]
            ev.log(t("wb.log_fase", fase=t(f"wb.fase.{fase_atual}")))
            ev.log(t("wb.log_reconstruindo"))
            cg.force_rebuild_world_context()      # a fase vê o que as anteriores (e o Mestre) escreveram

        item["estado"] = "executando"
        ev.emitir("wb.acao", {"indice": indice, "estado": "executando"})
        try:
            ok = _executar_item(item, referencia)
        except Exception as e:
            ev.log(t("wb.log_erro_acao", caminho=item["path"], erro=e))
            ok = False
        item["estado"] = "concluida" if ok else "falhou"
        if ok and item["type"] != "CreateFolder":
            tocados.append(str(_com_md(resolver_caminho(item["path"]))))
        falhas += 0 if ok else 1
        registro = {"timestamp": pu.currentdate(), "action": item["type"], "path": item["path"],
                    "template": item.get("template"), "objective": item["objective"],
                    "secret": item.get("segredo", False), "phase": item["fase"], "result": ok}
        pu.anexar_jsonl_seguro(pu.log_path("changelog.jsonl"), registro, pu.LOCK_CHANGELOG)
        salvar_sessao(sessao)
        ev.emitir("wb.acao", {"indice": indice, "estado": item["estado"], "registro": registro})

    if tocados:
        ev.log(t("wb.log_reconstruindo"))
        cg.force_rebuild_world_context()
    resumo = {"concluidas": len(tocados) + sum(1 for i in ordem if plano[i]["type"] == "CreateFolder"
                                                and plano[i]["estado"] == "concluida"),
              "falhas": falhas, "interrompido": interrompido, "arquivos": [caminho_relativo(c) for c in tocados],
              "links_sem_arquivo": links_sem_arquivo(tocados)}
    sessao.update(resumo=resumo, etapa=ETAPA_PLANO if interrompido else ETAPA_CONCLUIDA)
    salvar_sessao(sessao)
    ev.log(t("wb.log_fim_resumo", concluidas=resumo["concluidas"], falhas=falhas,
             links=len(resumo["links_sem_arquivo"])))
    ev.emitir("wb.sessao", sessao)
    return resumo
