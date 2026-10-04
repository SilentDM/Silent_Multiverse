"""
Silent — a entidade guardiã do Nexus, persona do programa (chat local e bot do Discord).

Antes, o texto das instruções e a montagem do prompt viviam dentro do gui.py.
Agora a interface só chama conversar() e historico_chat().
"""
import os
import re

import core.ai_utils as au
import core.memory as me
import engine.project_utils as pu
from core.i18n import tc
from core.prompts import carregar_prompt

USUARIO_LOCAL_ID = "999999"
USUARIO_LOCAL_NOME = "Silent Dungeon Master"


def _identificadores_chat_local():
    """Memória do chat local isolada por projeto."""
    return (f"desktop_{pu.PASTA_PROJETO}", f"Console_{pu.PASTA_PROJETO}", USUARIO_LOCAL_ID, USUARIO_LOCAL_NOME)


def instrucoes_chat() -> str:
    return carregar_prompt("chat_silent_sistema")


def instrucoes_discord() -> str:
    return carregar_prompt("discord_silent_sistema")


def preparar_anexo(caminho: str) -> dict:
    """Lê um arquivo para anexar à próxima mensagem do chat."""
    with open(caminho, "r", encoding="utf-8") as f:
        return {"nome": os.path.basename(caminho), "conteudo": f.read().strip()}


def historico_chat() -> list:
    """
    Conversa salva do chat local como lista de (papel, texto),
    papel ∈ {"usuario", "silent", "resumo"}.
    """
    memorias = me.carregar_memorias(*_identificadores_chat_local())
    if not memorias or not memorias.strip():
        return []
    partes = re.split(r'(Prompt Usuário:|Resposta:|Resumo de Memórias:)', memorias)
    papeis = {"Prompt Usuário:": "usuario", "Resposta:": "silent", "Resumo de Memórias:": "resumo"}
    mensagens = []
    for i in range(1, len(partes), 2):
        conteudo = partes[i + 1].strip() if i + 1 < len(partes) else ""
        if conteudo:
            mensagens.append((papeis[partes[i].strip()], conteudo))
    return mensagens


def conversar(mensagem: str, anexo: dict = None) -> str:
    """Envia a mensagem a Silent (com o mundo como contexto), salva na memória e devolve a resposta."""
    guild_id, guild_name, userid, user_name = _identificadores_chat_local()
    memorias = me.carregar_memorias(guild_id, guild_name, userid, user_name)

    blocos = []
    if anexo:
        blocos.append(tc("chat.bloco_anexo", nome=anexo["nome"], conteudo=anexo["conteudo"]))
    if memorias:
        blocos.append(tc("chat.bloco_historico", historico=memorias))
    blocos.append(tc("chat.bloco_mensagem", mensagem=mensagem))

    resposta = au.ask_ai(
        contents="\n\n".join(blocos),
        system_instruction=instrucoes_chat(),
        temperature=0.6,
        use_world_context=True,
    )
    resposta = me.trim_incomplete_sentences(resposta or "")
    if resposta:
        me.salvar_memoria(guild_id, guild_name, userid, user_name, mensagem, resposta)
    return resposta


def conversa_como_texto(limite: int = 12) -> str:
    """As últimas mensagens do chat como texto corrido (para virar a ideia do WorldBuilder)."""
    linhas = []
    for papel, conteudo in historico_chat()[-limite:]:
        if papel == "resumo":
            linhas.append(tc("chat.texto_resumo", texto=conteudo))
        else:
            linhas.append(f"{tc('chat.texto_mestre') if papel == 'usuario' else 'Silent'}: {conteudo}")
    return "\n\n".join(linhas)
