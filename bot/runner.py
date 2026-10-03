"""
Ciclo de vida do bot do Discord dentro do programa (antes vivia no gui.py).

iniciar() sobe o bot numa thread própria com seu event loop; o estado é
publicado por callbacks e pelo evento "discord.estado" ("desativado",
"conectando", "online", "erro"). parar() encerra a conexão.
"""
import asyncio
import os
import threading

import core.config as cfg
import core.eventos as ev
import core.tarefas as tarefas
from core.i18n import t

DESATIVADO, CONECTANDO, ONLINE, ERRO = "desativado", "conectando", "online", "erro"

_loop = None
_estado = DESATIVADO


def estado() -> str:
    return _estado


def _definir_estado(novo):
    global _estado
    _estado = novo
    ev.emitir("discord.estado", novo)


def token_configurado() -> bool:
    return bool(os.getenv("DISCORD_TOKEN", "").strip())


def iniciar(ao_descobrir_servidores=None):
    """Inicia o bot em segundo plano (se houver DISCORD_TOKEN). ao_descobrir_servidores([(id, nome)]) roda na interface."""
    if not token_configurado():
        _definir_estado(DESATIVADO)
        return

    def _rodar():
        global _loop
        try:
            ev.log(t("discord.log_iniciando"))
            from bot.dbot import discordclient

            def _servidores(guilds_info):
                _definir_estado(ONLINE)
                ev.log(t("discord.log_online"))
                if ao_descobrir_servidores:
                    tarefas.na_interface(ao_descobrir_servidores, guilds_info)

            discordclient.callback_guilds = _servidores
            _loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_loop)
            _definir_estado(CONECTANDO)
            _loop.run_until_complete(discordclient.start(os.getenv("DISCORD_TOKEN", "").strip()))
        except Exception as e:
            ev.log(t("discord.log_erro", erro=e))
            _definir_estado(ERRO)

    threading.Thread(target=_rodar, daemon=True).start()


def parar(timeout: float = 3.0):
    """Encerra a conexão com o Discord (se estiver rodando)."""
    try:
        if _loop and _loop.is_running():
            from bot.dbot import discordclient
            futuro = asyncio.run_coroutine_threadsafe(discordclient.close(), _loop)
            futuro.result(timeout=timeout)
    except Exception as e:
        ev.log(t("discord.log_erro_encerrar", erro=e))


def sincronizar_canais(servidor_id: str, ao_concluir=None, ao_falhar=None) -> bool:
    """
    Relê agora os canais de conhecimento configurados. ao_concluir((canais, mensagens)).
    Devolve False se o bot não estiver conectado.
    """
    try:
        from bot.dbot import discordclient
        import bot.discord_scraper as scraper
    except Exception:
        return False
    if not discordclient or not discordclient.is_ready():
        return False

    futuro = asyncio.run_coroutine_threadsafe(
        scraper.varrer_e_salvar_canais_conhecimento(discordclient, cfg.obter_configuracao_servidor(servidor_id)),
        discordclient.loop,
    )

    def _fim(f):
        try:
            resultado = f.result()
        except Exception as erro:
            ev.log(t("discord.log_erro_sync", erro=erro))
            if ao_falhar:
                tarefas.na_interface(ao_falhar, erro)
            return
        if ao_concluir:
            tarefas.na_interface(ao_concluir, resultado)

    futuro.add_done_callback(_fim)
    return True
