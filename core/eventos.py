"""
Barramento simples de logs e eventos.

A lógica (engine, core, bot) publica mensagens com log() e eventos estruturados
com emitir(); a interface apenas se inscreve para exibi-los. Assim nenhum módulo
de lógica precisa conhecer a interface (e vice-versa).

Canais de log: "geral" recebe TUDO; canais específicos (ex: "worldbuilder")
recebem apenas o que for publicado neles, além de aparecer em "geral".
"""
import sys
import threading
import traceback
from collections import defaultdict

_lock = threading.Lock()
_inscritos_log = defaultdict(list)      # canal -> [callback(msg)]
_inscritos_evento = defaultdict(list)   # evento -> [callback(dados)]


def inscrever_log(callback, canal: str = "geral"):
    with _lock:
        _inscritos_log[canal].append(callback)


def inscrever_evento(evento: str, callback):
    with _lock:
        _inscritos_evento[evento].append(callback)


def cancelar_inscricoes():
    """Remove todos os inscritos (usado em testes)."""
    with _lock:
        _inscritos_log.clear()
        _inscritos_evento.clear()


def _chamar(callbacks, valor):
    for cb in callbacks:
        try:
            cb(valor)
        except Exception:
            traceback.print_exc()


def log(mensagem, canal: str = "geral"):
    """Publica uma mensagem de log. Sem inscritos, cai no stdout (console de desenvolvimento)."""
    mensagem = str(mensagem)
    with _lock:
        destinos = list(_inscritos_log.get("geral", []))
        if canal != "geral":
            destinos += _inscritos_log.get(canal, [])
    if destinos:
        _chamar(destinos, mensagem)
    elif sys.__stdout__ is not None:
        # Console original (não o sys.stdout, que a interface pode redirecionar para cá mesmo).
        # Um log nunca pode derrubar quem o chamou: consoles do Windows (cp1252) não têm emojis.
        try:
            sys.__stdout__.write(mensagem + "\n")
        except UnicodeEncodeError:
            codificacao = getattr(sys.__stdout__, "encoding", None) or "ascii"
            sys.__stdout__.write(mensagem.encode(codificacao, "replace").decode(codificacao) + "\n")
        except (OSError, ValueError):
            pass


def emitir(evento: str, dados=None):
    """Publica um evento estruturado (ex: 'wb.plano' com a lista de ações planejadas)."""
    with _lock:
        destinos = list(_inscritos_evento.get(evento, []))
    _chamar(destinos, dados)
