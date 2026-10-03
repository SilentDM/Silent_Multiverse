import os, asyncio, time
import discord
import core.config as st
import engine.project_utils as pu
import bot.dice_roller as dice
import bot.bot_actions as actions
from core.i18n import t, tc
import core.credentials as se

# 🟢 Garante que as chaves do cofre estejam carregadas
se.carregar_todas_credenciais()

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

def obter_ids_mestres() -> str:
    """Lido a cada mensagem para refletir alterações feitas na aba 'Opções' sem reiniciar."""
    return os.getenv("MESTRE_DISCORD_ID", "").strip()
DISCORD_ENABLED = bool(TOKEN)

USER_COOLDOWNS = {}
ULTIMO_STATUS_PRESENCA = None

if DISCORD_ENABLED:
    intents = discord.Intents.default()
    intents.message_content = True
    discordclient = discord.Client(intents=intents)

    async def atualizar_presenca_bot(prefixo):
        global ULTIMO_STATUS_PRESENCA
        if not discordclient or not discordclient.is_ready():
            return

        projeto_atual = getattr(pu, "PASTA_PROJETO", "Projeto") or "Projeto"
        chave_atual = f"{prefixo}_{projeto_atual}"

        if ULTIMO_STATUS_PRESENCA != chave_atual:
            try:
                texto_status = f"{prefixo} | {projeto_atual}"
                atividade = discord.Activity(
                    type=discord.ActivityType.listening, 
                    name=texto_status
                )
                await discordclient.change_presence(
                    status=discord.Status.online,
                    activity=atividade
                )
                ULTIMO_STATUS_PRESENCA = chave_atual
                print(t("bot.log_status", status=texto_status))
            except Exception as e:
                print(t("bot.log_erro_presenca", erro=e))

    @discordclient.event
    async def on_ready():
        print(t("bot.log_logado", usuario=discordclient.user))

        try:
            guilds_info = [(str(g.id), g.name) for g in discordclient.guilds]
            st.registrar_servidores_descobertos(guilds_info)

            if hasattr(discordclient, "callback_guilds"):
                discordclient.callback_guilds(guilds_info)

            print(t("bot.log_servidores", servidores=guilds_info))

            import bot.discord_scraper as scraper
            config = st.obter_configuracao_servidor()
            asyncio.create_task(scraper.varrer_e_salvar_canais_conhecimento(discordclient, config))

        except Exception as e:
            print(t("bot.log_erro_servidores", erro=e))

        config = st.obter_configuracao_servidor()
        prefixo = config.get("discord_prefix", "!silent")
        await atualizar_presenca_bot(prefixo)

    @discordclient.event
    async def on_message(message):
        if message.author == discordclient.user:
            return

        user_name = message.author.name
        channel_name = message.channel.name if hasattr(message.channel, 'name') else "DM"
        guild_name = message.guild.name if message.guild else "DM Privado"
        guild_id = str(message.guild.id) if message.guild else "global"

        # 1. DMs: IGNORA OU RESPONDE APENAS AJUDA
        if isinstance(message.channel, discord.DMChannel):
            if any(k in message.content.lower() for k in ["help", "ajuda", "/help", "!help", "!ajuda"]):
                async with message.channel.typing():
                    prefixo_global = st.obter_configuracao_servidor("global").get("discord_prefix", "!silent").strip()
                    embed_help = actions.criar_embed_help(prefixo_global)
                    await message.reply(embed=embed_help)
            return

        config = st.obter_configuracao_servidor(guild_id)
        prefixo = config.get("discord_prefix", "!silent").strip()
        prefixo_lower = prefixo.lower()
        content = message.content.strip()
        content_lower = content.lower()

        # 2. ROLADOR RÁPIDO (!r 1d20+5 ou !rolar 2d6)
        partes_cmd = content.split(maxsplit=1)
        if partes_cmd and partes_cmd[0].lower() in ("!r", "!rolar", "!roll"):
            expr = partes_cmd[1] if len(partes_cmd) > 1 else ""
            await message.reply(dice.rolar_dados(expr))
            return

        if dice.eh_comando_dado(content):
            resposta_dados = dice.processar_rolagem(content)
            if resposta_dados:
                await message.reply(resposta_dados)
                return

        # 3. VERIFICAÇÃO DO GATILHO / PREFIXO
        if content_lower.startswith(prefixo_lower):
            raw_prompt = content[len(prefixo):]
            if raw_prompt.startswith(",") or raw_prompt.startswith(" "):
                raw_prompt = raw_prompt.lstrip(", ")
            prompt = raw_prompt.strip()

            if not prompt:
                return

            if prompt.lower() in ["help", "ajuda"]:
                embed_help = actions.criar_embed_help(prefixo)
                await message.reply(embed=embed_help)
                return

            if prompt.lower().split(" ")[0] in ("rolar", "roll", "r") and " " in prompt:
                expr = prompt.split(maxsplit=1)[1] if len(prompt.split(maxsplit=1)) > 1 else ""
                res = dice.rolar_dados(expr)
                await message.reply(res)
                return

            # SINCRONIZAÇÃO MANUAL DISPARADA PELO MESTRE (ex.: !silent sync)
            if prompt.lower() in ["sincronizar", "sync", "synchronize"]:
                if not actions.verificar_permissao_mestre(message, config, obter_ids_mestres()):
                    await message.reply(tc("bot.sync_apenas_mestres"))
                    return

                print(t("bot.log_sync_mestre", nome=user_name))
                async with message.channel.typing():
                    import bot.discord_scraper as scraper
                    total_arq, total_msg = await scraper.varrer_e_salvar_canais_conhecimento(discordclient, config)
                    msg_res = tc("bot.sync_concluido", canais=total_arq, mensagens=total_msg, pasta=f"Discord_Knowledge/server_{guild_id}/")
                    await message.reply(msg_res)
                return

            # CANAIS PERMITIDOS E BLOQUEADOS
            channel_id = str(message.channel.id)
            canais_permitidos = actions._parse_lista_texto(config.get("discord_channels_allowed", ""))
            canais_bloqueados = actions._parse_lista_texto(config.get("discord_channels_blocked", ""))

            if canais_bloqueados:
                if channel_name.lower() in canais_bloqueados or channel_id in canais_bloqueados:
                    return

            if canais_permitidos:
                if channel_name.lower() not in canais_permitidos and channel_id not in canais_permitidos:
                    return

            # COOLDOWN POR USUÁRIO
            userid = message.author.id
            tempo_cooldown = int(config.get("discord_cooldown_seconds", 15))
            agora = time.time()
            ultimo_envio = USER_COOLDOWNS.get(userid, 0)

            if agora - ultimo_envio < tempo_cooldown:
                return
            USER_COOLDOWNS[userid] = agora

            # PERMISSÃO DE MESTRE
            eh_mestre = actions.verificar_permissao_mestre(message, config, obter_ids_mestres())

            # DIGITANDO... + CHAMADA DA IA
            async with message.channel.typing():
                resposta = await actions.processar_mensagem_ia(
                    prompt=prompt,
                    eh_mestre=eh_mestre,
                    user_name=user_name,
                    guild_id=guild_id,
                    guild_name=guild_name,
                    userid=str(userid)
                )

            # ENTREGA EM CHUNKS SEM QUEBRAR PALAVRAS/LINKS
            if resposta:
                chunks = actions.dividir_em_chunks_limpos(resposta, max_chars=1900)
                total_c = len(chunks)
                for idx, chunk in enumerate(chunks):
                    embed = actions.criar_embed_resposta(chunk, eh_mestre, idx, total_c)
                    if idx == 0:
                        await message.reply(embed=embed)
                    else:
                        await message.channel.send(embed=embed)
                    await asyncio.sleep(1.0)

else:
    discordclient = None
    print(t("bot.log_sem_token"))

if __name__ == "__main__":
    if discordclient and TOKEN:
        discordclient.run(TOKEN)