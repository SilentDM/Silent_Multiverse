"""
Central de ações do programa.

Tudo que roda em segundo plano passa por aqui: Expander, WorldBuilder, Auditoria,
Livro do Cenário, Backup, contexto do mundo, troca de projeto e as ações de IA
sobre um arquivo (melhorar, aventura, testes de conhecimento, expander automático).

A interface chama uma função e recebe o resultado em ao_concluir/ao_falhar
(já na thread da interface). Cada ação publica o evento "acao.estado"
({"acao": nome, "rodando": bool}) para a interface atualizar botões e status.
"""
import os
import threading
from pathlib import Path

import core.cache_gemini as cg
import core.config as cfg
import core.eventos as ev
import core.memory as me
import core.silent_persona as silent
import core.sistema as sistema
import core.tarefas as tarefas
import engine.compiler as comp
import engine.expander as ex
import engine.geradores as geradores
import engine.historico as hist
import engine.melhorar as melhorar
import engine.notas as notas
import engine.requisicao as requisicao
import engine.style_manager as estilo
import engine.lore_auditor as auditor
import engine.project_utils as pu
import engine.token_counter as tc_tokens
import engine.wbuilder as wb
from core.i18n import t, tc

_lock = threading.Lock()
_em_execucao: set = set()


# ----------------------------------------------------------------------
# INFRAESTRUTURA
# ----------------------------------------------------------------------
def em_execucao(nome: str) -> bool:
    with _lock:
        return nome in _em_execucao


def _iniciar(nome: str, funcao, *args, ao_concluir=None, ao_falhar=None, reiniciar_cancelamento=False, **kwargs) -> bool:
    """Roda 'funcao' em segundo plano se a ação 'nome' não estiver rodando. Devolve False se já estava."""
    with _lock:
        if nome in _em_execucao:
            return False
        _em_execucao.add(nome)
    pu.esquecer_parada(nome)              # um pedido de parada antigo desta tarefa não vale para a nova
    if reiniciar_cancelamento:
        pu.reset_cancellation()
    ev.emitir("acao.estado", {"acao": nome, "rodando": True})

    def _finalizar():
        with _lock:
            _em_execucao.discard(nome)
        ev.emitir("acao.estado", {"acao": nome, "rodando": False})

    def _ok(resultado):
        _finalizar()
        if ao_concluir:
            ao_concluir(resultado)

    def _erro(erro):
        _finalizar()
        if ao_falhar:
            ao_falhar(erro)

    def _rodar(*a, **k):
        pu.definir_acao_da_thread(nome)
        try:
            return funcao(*a, **k)
        finally:
            pu.definir_acao_da_thread(None)

    tarefas.executar_em_segundo_plano(_rodar, *args, ao_concluir=_ok, ao_falhar=_erro, **kwargs)
    return True


def conversar_silent(mensagem: str, anexos: list, ao_concluir=None, ao_falhar=None) -> bool:
    """Envia a mensagem do chat a Silent em segundo plano (aparece na barra de tarefas)."""
    return _iniciar("chat", silent.conversar, mensagem, anexos, ao_concluir=ao_concluir, ao_falhar=ao_falhar)


def em_andamento() -> list:
    """Nomes das tarefas rodando agora (para a barra de tarefas)."""
    with _lock:
        return sorted(_em_execucao)


def parar_tudo():
    """Pede a interrupção de Expander/WorldBuilder/Auditoria em andamento."""
    pu.request_cancellation()
    ev.log(t("acoes.log_parada_solicitada"))


def parar(nome: str):
    """Pede a interrupção de uma tarefa só (as outras continuam)."""
    pu.request_cancellation(nome)
    ev.log(t("acoes.log_parada_tarefa", tarefa=nome_tarefa(nome)))


def nome_tarefa(nome: str) -> str:
    """Rótulo de uma tarefa para a interface e o log."""
    if nome.startswith("arquivo:"):
        return t("status.acao.arquivo_nome", nome=os.path.basename(nome[len("arquivo:"):]))
    return t(f"status.acao.{nome}")


# ----------------------------------------------------------------------
# AÇÕES DO PROJETO
# ----------------------------------------------------------------------
def executar_expander(ao_concluir=None, ao_falhar=None) -> bool:
    return _iniciar("expander", ex.processar_arquivos, ao_concluir=ao_concluir, ao_falhar=ao_falhar,
                    reiniciar_cancelamento=True)


def objetivo_padrao_worldbuilder() -> str:
    return tc("wb.objetivo_padrao")


# --- WorldBuilder (nível alto): Cânone -> Plano -> Execução ---
def wb_sessao() -> dict:
    return wb.carregar_sessao()


def wb_nova_sessao() -> dict:
    return wb.nova_sessao()


def wb_caminho_canon():
    caminho = wb.caminho_canon()
    return str(caminho) if caminho else None


def wb_atualizar_item(indice: int, **campos) -> dict:
    return wb.atualizar_item(indice, **campos)


def wb_opcoes() -> dict:
    """Listas para os seletores da página (tipos, modelos, fases) e limites atuais."""
    return {"tipos": list(wb.TIPOS), "templates": list(wb.TEMPLATES), "fases": list(wb.FASES),
            "max_acoes": wb.max_acoes(), "generos": [("", t("wb.genero_padrao"))] + estilo.opcoes("genero")}


def wb_definir_max_acoes(valor) -> int:
    try:
        valor = max(1, min(200, int(valor)))
    except (TypeError, ValueError):
        valor = wb.MAX_ACOES_PADRAO
    cfg.atualizar_configuracoes({"wb_max_acoes": valor})
    return valor


def wb_gerar_canon(objetivo: str, ao_concluir=None, ao_falhar=None) -> bool:
    return _iniciar("worldbuilder", wb.gerar_canon, objetivo, ao_concluir=ao_concluir, ao_falhar=ao_falhar,
                    reiniciar_cancelamento=True)


def wb_gerar_plano(ao_concluir=None, ao_falhar=None) -> bool:
    return _iniciar("worldbuilder", wb.gerar_plano, ao_concluir=ao_concluir, ao_falhar=ao_falhar,
                    reiniciar_cancelamento=True)


def wb_gerar_plano_auditoria(relatorio: str, ao_concluir=None, ao_falhar=None) -> bool:
    """Plano de correção no WorldBuilder a partir do relatório da Auditoria de Lore."""
    return _iniciar("worldbuilder", wb.gerar_plano_da_auditoria, relatorio, ao_concluir=ao_concluir,
                    ao_falhar=ao_falhar, reiniciar_cancelamento=True)


def wb_tem_plano_pendente() -> bool:
    return wb.tem_plano_pendente()


def auditoria_vai_ao_worldbuilder() -> bool:
    return bool(cfg.obter("auditoria_para_wb", False))


def definir_auditoria_vai_ao_worldbuilder(ativo: bool):
    cfg.atualizar_configuracoes({"auditoria_para_wb": bool(ativo)})


def wb_executar(ao_concluir=None, ao_falhar=None) -> bool:
    return _iniciar("worldbuilder", wb.executar_plano, ao_concluir=ao_concluir, ao_falhar=ao_falhar,
                    reiniciar_cancelamento=True)


def executar_auditoria(ao_concluir=None, ao_falhar=None) -> bool:
    return _iniciar("auditoria", auditor.executar_auditoria, ao_concluir=ao_concluir, ao_falhar=ao_falhar,
                    reiniciar_cancelamento=True)


def _compilar_e_abrir():
    caminho = comp.compilar_livro_cenario()
    if not caminho or not Path(caminho).exists():
        raise RuntimeError(t("acoes.erro_livro_vazio"))
    sistema.abrir_no_sistema(caminho)
    return caminho


def compilar_livro(ao_concluir=None, ao_falhar=None) -> bool:
    return _iniciar("livro", _compilar_e_abrir, ao_concluir=ao_concluir, ao_falhar=ao_falhar)


def analisar_tamanho(ao_concluir=None, ao_falhar=None) -> bool:
    return _iniciar("tamanho", tc_tokens.analisar_projeto, ao_concluir=ao_concluir, ao_falhar=ao_falhar)


def criar_backup(ao_concluir=None, ao_falhar=None) -> bool:
    """ao_concluir recebe (caminho_zip, total_arquivos)."""
    return _iniciar("backup", pu.criar_backup_projeto, ao_concluir=ao_concluir, ao_falhar=ao_falhar)


def status_cache_gemini() -> dict:
    return cg.status_cache()


def reativar_cache_gemini():
    cg.reativar_cache()
    ev.log(t("gemini.log_cache_reativado"))


def reconstruir_contexto(ao_concluir=None, ao_falhar=None) -> bool:
    return _iniciar("contexto", cg.force_rebuild_world_context, ao_concluir=ao_concluir, ao_falhar=ao_falhar)


def excluir_memorias():
    me.delete_all_memories()
    ev.log(t("acoes.log_memorias_excluidas"))


def abrir_pasta_dados():
    pu.PASTA_DADOS_NEXUS.mkdir(parents=True, exist_ok=True)
    sistema.abrir_no_sistema(pu.PASTA_DADOS_NEXUS)


# ----------------------------------------------------------------------
# PROJETOS
# ----------------------------------------------------------------------
def projetos_recentes() -> dict:
    """{nome_da_pasta: caminho} dos projetos recentes."""
    return {Path(p).name: p for p in pu.obter_projetos_recentes()}


def projeto_ativo() -> tuple:
    return pu.PASTA_PROJETO, str(pu.CAMINHO_PROJETO)


def trocar_projeto(caminho: str) -> str:
    """Ativa outro projeto e reconstrói o contexto do mundo em segundo plano. Devolve o nome."""
    pu.definir_projeto_ativo(caminho)
    ev.log(t("acoes.log_projeto_trocado", caminho=pu.CAMINHO_PROJETO))
    reconstruir_contexto()
    return pu.PASTA_PROJETO


# ----------------------------------------------------------------------
# AÇÕES DE IA SOBRE UM ARQUIVO
# ----------------------------------------------------------------------
TIPOS_ACAO_ARQUIVO = ("melhorar", "aventura", "conhecimento", "ficha", "expander")


def texto_padrao_acao(tipo: str, caminho: str) -> str:
    """Objetivo usado quando o usuário deixa o campo em branco."""
    nome = os.path.basename(caminho)
    return {
        "melhorar": tc("acoes.padrao_melhorar"),
        "aventura": tc("acoes.padrao_aventura", nome=nome),
        "conhecimento": tc("acoes.padrao_conhecimento"),
        "ficha": "",
        "expander": "",
    }[tipo]


def arquivo_em_processamento(caminho: str) -> bool:
    return ex.esta_em_processamento(caminho)


def executar_acao_arquivo(tipo: str, caminho: str, texto_usuario: str = "", ao_concluir=None, ao_falhar=None,
                          requisicao=None) -> bool:
    """
    Roda uma ação de IA sobre o arquivo, travando-o (o editor não grava por cima enquanto isso).
    ao_concluir recebe True/False (sucesso da ação). Devolve False se o arquivo já estava em processamento.
    """
    if tipo not in TIPOS_ACAO_ARQUIVO:
        raise ValueError(tipo)
    caminho = os.path.abspath(caminho)
    if ex.esta_em_processamento(caminho):
        return False
    texto = (texto_usuario or "").strip() or texto_padrao_acao(tipo, caminho)
    ex.marcar_processamento(caminho, True)

    def _rodar():
        try:
            if tipo == "melhorar":
                return melhorar.melhorar_arquivo(caminho, texto, requisicao=requisicao)
            if tipo == "aventura":
                return geradores.gerar_aventura_completa(caminho, reason=texto, requisicao=requisicao)
            if tipo == "conhecimento":
                return geradores.gerar_tabelas_de_conhecimento(caminho, foco_especifico=texto, requisicao=requisicao)
            if tipo == "ficha":
                return geradores.gerar_ficha(caminho, texto, requisicao=requisicao,
                                             tipo=requisicao.criatura if requisicao else "npc")
            ex.processar_arquivo_unico(caminho)
            return True
        finally:
            ex.marcar_processamento(caminho, False)

    return _iniciar(f"arquivo:{caminho}", _rodar, ao_concluir=ao_concluir, ao_falhar=ao_falhar)


def executar_requisicao(req, ao_concluir=None, ao_falhar=None) -> bool:
    """Executa uma Requisição da aba Requisições (o Conselho é aberto pela própria interface)."""
    return executar_acao_arquivo(req.tipo, req.caminho, req.objetivo, ao_concluir=ao_concluir, ao_falhar=ao_falhar,
                                 requisicao=req)


# ----------------------------------------------------------------------
# REQUISIÇÕES, ESTILOS E NOTAS
# ----------------------------------------------------------------------
def nova_requisicao(tipo: str, caminho: str, objetivo: str = ""):
    return requisicao.nova(tipo, caminho, objetivo)


def opcoes_requisicao() -> dict:
    """Listas para os seletores da aba Requisições."""
    return {"eixos": {eixo: estilo.opcoes(eixo) for eixo in estilo.EIXOS}, "modos": list(requisicao.MODOS),
            "profundidades": list(requisicao.PROFUNDIDADES), "publicos": list(requisicao.PUBLICOS),
            "criatividades": list(requisicao.CRIATIVIDADES)}


def sugerir_referencias(caminho: str) -> list:
    return requisicao.sugerir_referencias(caminho)


def estimar_tokens_requisicao(req) -> int:
    return requisicao.estimar_tokens(req)


def presets_requisicao() -> list:
    return requisicao.listar_presets()


def salvar_preset_requisicao(nome: str, req):
    requisicao.salvar_preset(nome, req)


def aplicar_preset_requisicao(nome: str, req):
    return requisicao.aplicar_preset(nome, req)


def excluir_preset_requisicao(nome: str):
    requisicao.excluir_preset(nome)


def estilos_do_projeto() -> dict:
    """{eixo: (id_padrão, [(id, nome)])} para as Opções."""
    return {eixo: (estilo.padrao(eixo), estilo.opcoes(eixo)) for eixo in estilo.EIXOS}


def definir_estilo_do_projeto(eixo: str, ident: str):
    estilo.definir_padrao(eixo, ident)


def adicionar_nota(caminho: str, texto: str, origem: str = "mestre", autor: str = "") -> str:
    """Guarda a nota na seção secreta 'Notas do Mestre' do arquivo. Lança notas.ErroNotas com mensagem pronta."""
    return notas.adicionar_nota(caminho, texto, origem, autor)


def sugerir_destinos_nota(texto: str, arquivo_atual: str = None, nomes=()) -> list:
    return notas.sugerir_destinos(texto, arquivo_atual, nomes)


def notas_do_arquivo(caminho: str) -> list:
    return notas.listar_notas(caminho)


# ----------------------------------------------------------------------
# HISTÓRICO DE VERSÕES DE UM ARQUIVO
# ----------------------------------------------------------------------
def versoes_do_arquivo(caminho: str) -> list:
    return hist.listar_versoes(caminho)


def ler_versao(versao) -> str:
    return hist.ler_versao(versao)


def restaurar_versao(caminho: str, versao) -> str:
    """Restaura a versão (a atual vai para o histórico). Lança hist.ErroHistorico com mensagem pronta."""
    return str(hist.restaurar_versao(caminho, versao))


def deve_auto_expandir(caminho: str) -> bool:
    """True se o Expander automático está ligado e o arquivo salvo tem uma tag TODO."""
    if not cfg.obter("auto_expander", False) or not caminho or not os.path.isfile(caminho):
        return False
    if ex.esta_em_processamento(caminho):
        return False
    conteudo = pu.ler_markdown(Path(caminho)) or ""
    return any(tag in conteudo for tag in pu.TAG_ALVO)


def executar_benchmark_modelos(ao_concluir=None, ao_falhar=None) -> bool:
    """Testa e reordena os modelos Gemini (página Performance). ao_concluir recebe a lista nova."""
    import core.modelos_gemini as modelos
    return _iniciar("benchmark", modelos.executar_benchmark, ao_concluir=ao_concluir, ao_falhar=ao_falhar)
