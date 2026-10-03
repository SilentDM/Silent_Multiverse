# bot/discord_scraper.py
"""Lê os canais de conhecimento configurados e salva cada um como .md (usado pelo bot como contexto)."""
import re
import unicodedata

import discord

import core.config as st
import engine.project_utils as pu
from core.i18n import t, tc


def normalizar_texto_canal(texto: str) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII")
    return re.sub(r'[^a-z0-9]', '', texto.lower().strip())


def _linha_mensagem(autor, url, conteudo, data=None):
    prefixo = f"[{data}] " if data else ""
    return tc("scraper.mensagem", data=prefixo, autor=autor, link=tc("scraper.ver_no_discord"), url=url, conteudo=conteudo)


async def varrer_e_salvar_canais_conhecimento(client: discord.Client, config: dict = None) -> tuple[int, int]:
    if not client or not client.is_ready():
        print(t("scraper.log_nao_pronto"))
        return 0, 0

    total_mensagens = 0
    total_arquivos = 0
    print(t("scraper.log_inicio"))

    for guild in client.guilds:
        guild_id = str(guild.id)
        raw_channels = st.obter_configuracao_servidor(guild_id).get("discord_channels_knowledge", "")
        if not raw_channels or not raw_channels.strip():
            continue

        canais_alvo_brutos = [c.strip() for c in raw_channels.replace(";", ",").split(",") if c.strip()]
        canais_alvo_norm = [normalizar_texto_canal(c) for c in canais_alvo_brutos]
        ids_alvo = [c for c in canais_alvo_brutos if c.isdigit()]
        print(t("scraper.log_servidor", servidor=guild.name, canais=canais_alvo_brutos))

        pasta_servidor = pu.PASTA_DISCORD_KNOWLEDGE / f"server_{guild_id}"
        pasta_servidor.mkdir(parents=True, exist_ok=True)

        for channel in guild.channels:
            nome_canal = channel.name
            nome_norm = normalizar_texto_canal(nome_canal)
            if nome_norm not in canais_alvo_norm and str(channel.id) not in ids_alvo:
                continue
            print(t("scraper.log_lendo", canal=nome_canal, servidor=guild.name))

            conteudo_canal = [
                tc("scraper.titulo_canal", canal=nome_canal),
                tc("scraper.cabecalho_canal", servidor=guild.name, data=pu.currentdate()),
                "",
            ]

            # 1. MENSAGENS FIXADAS E HISTÓRICO
            if isinstance(channel, (discord.TextChannel, discord.ForumChannel)):
                try:
                    pins = await channel.pins()
                    if pins:
                        conteudo_canal.append(tc("scraper.fixadas"))
                        for pin in pins:
                            if pin.content.strip():
                                conteudo_canal.append(_linha_mensagem(pin.author.display_name, pin.jump_url, pin.content))
                                total_mensagens += 1
                        conteudo_canal.append("")

                    conteudo_canal.append(tc("scraper.historico"))
                    async for msg in channel.history(limit=200, oldest_first=True):
                        if not msg.author.bot and msg.content.strip():
                            conteudo_canal.append(_linha_mensagem(msg.author.display_name, msg.jump_url, msg.content,
                                                                  msg.created_at.strftime('%Y-%m-%d')))
                            total_mensagens += 1
                except discord.Forbidden:
                    print(t("scraper.log_sem_permissao", canal=nome_canal))
                except Exception as e:
                    print(t("scraper.log_erro_historico", canal=nome_canal, erro=e))

            # 2. THREADS ATIVAS E ARQUIVADAS
            threads = list(getattr(channel, "threads", []) or [])
            if hasattr(channel, "archived_threads"):
                try:
                    async for arquivada in channel.archived_threads(limit=30):
                        threads.append(arquivada)
                except Exception:
                    pass

            if threads:
                conteudo_canal.append("")
                conteudo_canal.append(tc("scraper.threads"))
                for thread in threads:
                    conteudo_canal.append("")
                    conteudo_canal.append(tc("scraper.topico", nome=thread.name))
                    conteudo_canal.append(tc("scraper.ir_para_thread", url=thread.jump_url))
                    try:
                        async for t_msg in thread.history(limit=100, oldest_first=True):
                            if not t_msg.author.bot and t_msg.content.strip():
                                conteudo_canal.append(_linha_mensagem(t_msg.author.display_name, t_msg.jump_url, t_msg.content))
                                total_mensagens += 1
                    except Exception as e:
                        print(t("scraper.log_erro_thread", nome=thread.name, erro=e))

            (pasta_servidor / f"{nome_norm}.md").write_text("\n".join(conteudo_canal), encoding="utf-8")
            total_arquivos += 1

    print(t("scraper.log_fim", canais=total_arquivos, mensagens=total_mensagens))
    return total_arquivos, total_mensagens
