"""
Execução de tarefas em segundo plano.

A interface nunca cria threads: chama executar_em_segundo_plano() e recebe o
resultado em ao_concluir / ao_falhar, já de volta na thread da interface
(o "despachante" é registrado pela interface na inicialização, ex: root.after).
"""
import threading
import traceback

import core.eventos as ev

_despachante = None


def definir_despachante(agendar):
    """agendar(ms, funcao) — ex: tkinter root.after. Sem despachante, os callbacks rodam direto."""
    global _despachante
    _despachante = agendar


def na_interface(funcao, *args, **kwargs):
    """Executa 'funcao' na thread da interface (ou imediatamente, se não houver despachante)."""
    if _despachante is None:
        return funcao(*args, **kwargs)
    try:
        _despachante(0, lambda: funcao(*args, **kwargs))
    except RuntimeError:
        # A janela já foi fechada (ou o laço da interface parou): não há mais quem receber o resultado.
        pass


def executar_em_segundo_plano(funcao, *args, ao_concluir=None, ao_falhar=None, **kwargs):
    """Roda funcao(*args, **kwargs) numa thread daemon e entrega o resultado na interface."""
    def _executar():
        try:
            resultado = funcao(*args, **kwargs)
        except Exception as erro:
            ev.log("".join(traceback.format_exception(type(erro), erro, erro.__traceback__)).rstrip())
            if ao_falhar:
                na_interface(ao_falhar, erro)
            return
        if ao_concluir:
            na_interface(ao_concluir, resultado)

    thread = threading.Thread(target=_executar, daemon=True)
    thread.start()
    return thread
