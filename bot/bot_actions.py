# bot/bot_actions.py
import asyncio

import discord

import core.ai_utils as au
import core.ao_persona as ao_persona
import core.memory as memory
import engine.project_utils as pu
from core.i18n import t, tc


def _parse_lista_texto(raw_str: str) -> list[str]:
    if not raw_str:
        return []
    raw_str = raw_str.replace(";", ",")
    return [item.strip().lower() for item in raw_str.split(",") if item.strip()]


def verificar_permissao_mestre(message, config: dict, mestre_ids: str) -> bool:
    userid = str(message.author.id)
    user_name = message.author.name

    # MESTRE_DISCORD_ID aceita um ou vários IDs separados por vírgula/ponto-e-vírgula
    if userid in set(_parse_lista_texto(mestre_ids or "")):
        print(t("bot.log_mestre_id", nome=user_name))
        return True

    cargos_mestre = _parse_lista_texto(config.get("discord_roles_dm", "Mestre, DM, GM"))
    if hasattr(message.author, "roles"):
        cargos_usuario = [r.name.lower() for r in message.author.roles]
        if any(cargo in cargos_usuario for cargo in cargos_mestre):
            print(t("bot.log_mestre_cargo", nome=user_name))
            return True

    print(t("bot.log_jogador", nome=user_name))
    return False


def dividir_em_chunks_limpos(texto: str, max_chars: int = 1900) -> list[str]:
    """Divide o texto respeitando parágrafos e quebras de linha para não quebrar links."""
    if len(texto) <= max_chars:
        return [texto]
    chunks = []
    restante = texto
    while len(restante) > max_chars:
        corte = restante.rfind('\n', 0, max_chars)
        if corte == -1 or corte < max_chars // 2:
            corte = max_chars
        chunk = restante[:corte].strip()
        if chunk:
            chunks.append(chunk)
        restante = restante[corte:].strip()
    if restante:
        chunks.append(restante)
    return chunks


async def processar_mensagem_ia(prompt: str, eh_mestre: bool, user_name: str, guild_id: str, guild_name: str, userid: str) -> str:
    extra = pu.detectar_intencao(prompt)
    conhecimento_discord = pu.carregar_conhecimento_discord(guild_id=guild_id)
    memorias = memory.carregar_memorias(guild_id, guild_name, userid, user_name)

    blocos = []
    if conhecimento_discord:
        blocos.append(tc("bot.bloco_registros", conteudo=conhecimento_discord))
    if memorias:
        blocos.append(tc("bot.bloco_historico", historico=memorias))
    blocos.append(tc("bot.bloco_mensagem", nome=user_name, mensagem=prompt) + (f" {extra}" if extra else ""))

    print(t("bot.log_consultando", mestre=eh_mestre))
    try:
        resposta = await asyncio.to_thread(
            au.ask_ai,
            contents="\n\n".join(blocos),
            system_instruction=ao_persona.instrucoes_discord(),
            temperature=0.65,
            use_world_context=True,
            is_dm=eh_mestre,
        )
    except Exception as e:
        print(t("bot.log_erro_ia", erro=e))
        resposta = tc("bot.resposta_erro")

    if resposta:
        resposta = memory.trim_incomplete_sentences(resposta)
        # Em thread separada: pode chamar a IA para resumir e não pode travar o event loop do Discord
        await asyncio.to_thread(memory.salvar_memoria, guild_id, guild_name, userid, user_name, prompt, resposta)
    return resposta or ""


def criar_embed_resposta(texto_chunk: str, eh_mestre: bool, idx: int, total_chunks: int) -> discord.Embed:
    embed = discord.Embed(description=texto_chunk, color=0x10b981 if eh_mestre else 0x3b82f6)
    if idx == 0:
        embed.set_author(name=tc("bot.autor"))
        embed.set_footer(text=tc("bot.rodape_acesso", acesso=tc("bot.acesso_mestre") if eh_mestre else tc("bot.acesso_jogador")))
    elif idx == total_chunks - 1:
        embed.set_footer(text=tc("bot.rodape_pagina", atual=idx + 1, total=total_chunks))
    return embed


def criar_embed_help() -> discord.Embed:
    embed = discord.Embed(title=tc("bot.ajuda_titulo"), description=tc("bot.ajuda_descricao"), color=0x10b981)
    embed.add_field(name=tc("bot.ajuda_lore_titulo"), value=tc("bot.ajuda_lore"), inline=False)
    embed.add_field(name=tc("bot.ajuda_dados_titulo"), value=tc("bot.ajuda_dados"), inline=False)
    embed.add_field(name=tc("bot.ajuda_sync_titulo"), value=tc("bot.ajuda_sync"), inline=False)
    embed.set_footer(text="Silent Multiverse Nexus Console")
    return embed
