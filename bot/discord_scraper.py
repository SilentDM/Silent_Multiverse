# bot/discord_scraper.py
import os, asyncio, unicodedata, re
import discord
from pathlib import Path
import engine.project_utils as pu
import ui.settings as st

def normalizar_texto_canal(texto: str) -> str:
    """Remove acentos, maiúsculas e caracteres especiais para bater 'visão-da-mesa' com 'visao-da-mesa'."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII")
    texto = texto.lower().strip()
    texto = re.sub(r'[^a-z0-9]', '', texto)
    return texto

async def varrer_e_salvar_canais_conhecimento(client: discord.Client, config: dict = None) -> tuple[int, int]:
    """
    Varre os canais configurados (incluindo threads ativas e arquivadas)
    e compila tudo em arquivos .md na pasta Discord_Knowledge/server_ID/.
    """
    if not client or not client.is_ready():
        print("⚠️ [SCRAPER] Client do Discord ainda não está pronto.")
        return 0, 0

    total_mensagens = 0
    total_arquivos = 0

    print("📚 [SCRAPER] Iniciando varredura de canais de conhecimento...")

    for guild in client.guilds:
        guild_id = str(guild.id)
        config_srv = st.obter_configuracao_servidor(guild_id)
        raw_channels = config_srv.get("discord_channels_knowledge", "")

        if not raw_channels or not raw_channels.strip():
            continue

        canais_alvo_brutos = [c.strip() for c in raw_channels.replace(";", ",").split(",") if c.strip()]
        canais_alvo_norm = [normalizar_texto_canal(c) for c in canais_alvo_brutos]
        ids_alvo = [c for c in canais_alvo_brutos if c.isdigit()]

        print(f"🔍 [SCRAPER] Servidor '{guild.name}': Varrendo canais {canais_alvo_brutos}...")

        pasta_servidor = pu.PASTA_DISCORD_KNOWLEDGE / f"server_{guild_id}"
        pasta_servidor.mkdir(parents=True, exist_ok=True)

        for channel in guild.channels:
            c_name_raw = channel.name
            c_name_norm = normalizar_texto_canal(c_name_raw)
            c_id = str(channel.id)

            match_nome = c_name_norm in canais_alvo_norm
            match_id = c_id in ids_alvo

            if match_nome or match_id:
                print(f"✅ [SCRAPER] Lendo canal: #{c_name_raw} em '{guild.name}'")

                conteudo_canal = [
                    f"# Registros do Canal: #{c_name_raw}",
                    f"> Servidor: {guild.name} | Sincronizado em: {pu.currentdate()}\n"
                ]

                # 1. MENSAGENS FIXADAS E HISTÓRICO
                if isinstance(channel, (discord.TextChannel, discord.ForumChannel)):
                    try:
                        pins = await channel.pins()
                        if pins:
                            conteudo_canal.append("## 📌 Informações e Regras Fixadas")
                            for pin in pins:
                                if pin.content.strip():
                                    conteudo_canal.append(f"- **{pin.author.display_name}** 🔗 [Ver no Discord]({pin.jump_url}):\n  {pin.content}\n")
                                    total_mensagens += 1
                            conteudo_canal.append("\n")

                        conteudo_canal.append("## 💬 Histórico de Mensagens Relevantes")
                        async for msg in channel.history(limit=200, oldest_first=True):
                            if not msg.author.bot and msg.content.strip():
                                conteudo_canal.append(f"- **[{msg.created_at.strftime('%Y-%m-%d')}] {msg.author.display_name}** 🔗 [Ver no Discord]({msg.jump_url}):\n  {msg.content}\n")
                                total_mensagens += 1

                    except discord.Forbidden:
                        print(f"❌ [SCRAPER] Sem permissão para ler histórico de #{c_name_raw}!")
                    except Exception as e:
                        print(f"❌ [SCRAPER] Erro ao ler histórico de #{c_name_raw}: {e}")

                # 2. THREADS ATIVAS E ARQUIVADAS
                threads_para_varrer = []
                if hasattr(channel, "threads"):
                    threads_para_varrer.extend(channel.threads)

                if hasattr(channel, "archived_threads"):
                    try:
                        async for archived_thread in channel.archived_threads(limit=30):
                            threads_para_varrer.append(archived_thread)
                    except Exception:
                        pass

                if threads_para_varrer:
                    conteudo_canal.append("\n## 🧵 Tópicos e Threads de Discussão")
                    for thread in threads_para_varrer:
                        conteudo_canal.append(f"\n### Tópico: {thread.name}")
                        conteudo_canal.append(f"🔗 [Ir para a Thread no Discord]({thread.jump_url})")
                        try:
                            async for t_msg in thread.history(limit=100, oldest_first=True):
                                if not t_msg.author.bot and t_msg.content.strip():
                                    conteudo_canal.append(f"- **{t_msg.author.display_name}** 🔗 [Ver no Discord]({t_msg.jump_url}):\n  {t_msg.content}\n")
                                    total_mensagens += 1
                        except Exception as e:
                            print(f"❌ [SCRAPER] Erro ao ler thread {thread.name}: {e}")

                # Salva o arquivo .md
                nome_arquivo = f"{c_name_norm}.md"
                caminho_file = pasta_servidor / nome_arquivo
                with open(caminho_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(conteudo_canal))

                total_arquivos += 1

    print(f"✅ [SCRAPER] Varredura concluída: {total_arquivos} canal(is) salvos, {total_mensagens} mensagem(ns).\n")
    return total_arquivos, total_mensagens