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
import core.sistema as sistema
import core.tarefas as tarefas
import engine.compiler as comp
import engine.expander as ex
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

    tarefas.executar_em_segundo_plano(funcao, *args, ao_concluir=_ok, ao_falhar=_erro, **kwargs)
    return True


def parar_tudo():
    """Pede a interrupção de Expander/WorldBuilder/Auditoria em andamento."""
    pu.request_cancellation()
    ev.log(t("acoes.log_parada_solicitada"))


# ----------------------------------------------------------------------
# AÇÕES DO PROJETO
# ----------------------------------------------------------------------
def executar_expander(ao_concluir=None, ao_falhar=None) -> bool:
    return _iniciar("expander", ex.processar_arquivos, ao_concluir=ao_concluir, ao_falhar=ao_falhar,
                    reiniciar_cancelamento=True)


def objetivo_padrao_worldbuilder() -> str:
    return tc("wb.objetivo_padrao")


def executar_worldbuilder(objetivo: str, ao_concluir=None, ao_falhar=None) -> bool:
    objetivo = (objetivo or "").strip() or objetivo_padrao_worldbuilder()
    return _iniciar("worldbuilder", wb.taskplanner, objetivo, ao_concluir=ao_concluir, ao_falhar=ao_falhar,
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
TIPOS_ACAO_ARQUIVO = ("melhorar", "aventura", "conhecimento", "expander")


def texto_padrao_acao(tipo: str, caminho: str) -> str:
    """Objetivo usado quando o usuário deixa o campo em branco."""
    nome = os.path.basename(caminho)
    return {
        "melhorar": tc("acoes.padrao_melhorar"),
        "aventura": tc("acoes.padrao_aventura", nome=nome),
        "conhecimento": tc("acoes.padrao_conhecimento"),
        "expander": "",
    }[tipo]


def arquivo_em_processamento(caminho: str) -> bool:
    return ex.esta_em_processamento(caminho)


def executar_acao_arquivo(tipo: str, caminho: str, texto_usuario: str = "", ao_concluir=None, ao_falhar=None) -> bool:
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
                return wb.improvefile(caminho, reason=texto)
            if tipo == "aventura":
                return wb.gerar_aventura_completa(caminho, reason=texto)
            if tipo == "conhecimento":
                return wb.gerar_tabelas_de_conhecimento(caminho, foco_especifico=texto)
            ex.processar_arquivo_unico(caminho)
            return True
        finally:
            ex.marcar_processamento(caminho, False)

    return _iniciar(f"arquivo:{caminho}", _rodar, ao_concluir=ao_concluir, ao_falhar=ao_falhar)


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
