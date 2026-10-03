"""
Configurações do programa (settings.json em .silent_data/logs).

Antes viviam em ui/settings.py, o que fazia módulos de lógica (engine, bot, core)
dependerem da interface. Agora qualquer parte do programa importa daqui.
"""
import json
import threading

import engine.project_utils as pu

SETTINGS_FILE = pu.PASTA_LOGS / "settings.json"
_LOCK = threading.Lock()

CONFIG_PADRAO_DISCORD = {
    "discord_prefix": "!silent",
    "discord_channels_allowed": "",
    "discord_channels_blocked": "",
    "discord_channels_knowledge": "",  # Canais lidos pelo Scraper
    "discord_roles_dm": "Mestre, DM, GM",
    "discord_cooldown_seconds": 15,
}

DEFAULT_SETTINGS = {
    "idioma": "pt_br",                 # Idioma da interface e das chamadas de IA (pt_br | en_us)
    "auto_expander": False,
    "verificar_atualizacoes": True,    # Procura versão nova no GitHub ao abrir o programa
    "wb_allow_create_folder": True,
    "wb_allow_create_file": True,
    "wb_allow_improve_file": True,
    "tom_clima_perfil": "dark_fantasy",
    "rpg_sistema_ativo": "dnd5e",
    "ai_provider_ativo": "Gemini",
    "servidores_descobertos": [],
    "servidores": {},                  # ID_SERVIDOR: { config_especifica }
    "termos_secretos": "",
    "modelos_modo_ordenacao": "automatico",  # "automatico" ou "manual"
    "ordem_manual_modelos": [],
}
DEFAULT_SETTINGS.update(CONFIG_PADRAO_DISCORD)

PROVEDORES_IA = {
    "Gemini": "gemini",
    "Pro (OpenAI)": "pro",
    "Claude (Anthropic)": "claude",
}


def carregar_configuracoes() -> dict:
    config = DEFAULT_SETTINGS.copy()
    with _LOCK:
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    config.update(json.load(f))
            except Exception as e:
                print(f"Erro ao carregar configurações: {e}")
    return config


def salvar_configuracoes(config: dict):
    """Grava de forma atômica (arquivo temporário + replace) para nunca deixar um JSON pela metade."""
    with _LOCK:
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = SETTINGS_FILE.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            tmp.replace(SETTINGS_FILE)
        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")


def atualizar_configuracoes(novos_valores: dict) -> dict:
    """
    Relê o settings.json do disco, aplica apenas as chaves informadas e grava.
    Evita sobrescrever alterações feitas por outras partes do programa
    (projeto ativo, servidores do Discord, modo dos modelos...).
    """
    cfg = carregar_configuracoes()
    cfg.update(novos_valores)
    salvar_configuracoes(cfg)
    return cfg


def obter(chave, padrao=None):
    return carregar_configuracoes().get(chave, padrao)


def obter_configuracao_servidor(guild_id: str = None) -> dict:
    """
    Retorna a configuração resolvida para um servidor específico.
    Se o servidor não tiver personalização ou um campo estiver vazio, usa o fallback global.
    """
    cfg = carregar_configuracoes()
    base = {k: cfg.get(k, CONFIG_PADRAO_DISCORD.get(k, "")) for k in CONFIG_PADRAO_DISCORD}

    if guild_id and "servidores" in cfg and str(guild_id) in cfg["servidores"]:
        custom = cfg["servidores"][str(guild_id)]
        # Sobrescreve apenas o que estiver preenchido no servidor específico
        for k, v in custom.items():
            if v is not None and str(v).strip() != "":
                base[k] = v
    return base


def salvar_configuracao_discord(target_id: str, novos_dados: dict):
    """Grava campos do Discord no perfil global ('global') ou na partição de um servidor específico."""
    cfg = carregar_configuracoes()
    if target_id == "global":
        cfg.update(novos_dados)
    else:
        cfg.setdefault("servidores", {}).setdefault(target_id, {}).update(novos_dados)
    salvar_configuracoes(cfg)


def valores_discord_para_edicao(target_id: str) -> dict:
    """Valores a exibir no formulário do Discord: globais (com padrões) ou só os personalizados do servidor."""
    cfg = carregar_configuracoes()
    if target_id == "global":
        return {k: cfg.get(k, CONFIG_PADRAO_DISCORD.get(k, "")) for k in CONFIG_PADRAO_DISCORD}
    return dict(cfg.get("servidores", {}).get(target_id, {}))


def registrar_servidores_descobertos(guilds_info: list):
    """Atualiza a lista de servidores conhecidos no settings.json (id, name)."""
    cfg = carregar_configuracoes()
    atuais = {str(item["id"]): item["name"] for item in cfg.get("servidores_descobertos", [])}
    for gid, gname in guilds_info:
        atuais[str(gid)] = gname
    cfg["servidores_descobertos"] = [{"id": gid, "name": name} for gid, name in atuais.items()]
    salvar_configuracoes(cfg)


def servidores_conhecidos() -> list:
    """Lista [(id, nome)] dos servidores do Discord já descobertos pelo bot."""
    lista = []
    for item in carregar_configuracoes().get("servidores_descobertos", []):
        if isinstance(item, dict):
            lista.append((str(item.get("id")), item.get("name") or str(item.get("id"))))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            lista.append((str(item[0]), str(item[1])))
    return lista


def provedor_ia_ativo() -> str:
    """Rótulo do provedor de IA ativo (chave de PROVEDORES_IA)."""
    import core.credentials as cred
    valor = cred.obter_credencial("AI_PROVIDER", "gemini").lower()
    return next((rotulo for rotulo, v in PROVEDORES_IA.items() if v == valor), "Gemini")


def definir_provedor_ia(rotulo: str):
    """Grava a escolha (settings + cofre). Vale na próxima chamada de IA, sem reiniciar."""
    import core.credentials as cred
    atualizar_configuracoes({"ai_provider_ativo": rotulo})
    cred.salvar_credencial("AI_PROVIDER", PROVEDORES_IA.get(rotulo, "gemini"))


def credencial_para_edicao(nome_chave: str) -> str:
    """Valor atual de uma credencial do cofre, para preencher a tela de Opções."""
    import core.credentials as cred
    return cred.obter_credencial(nome_chave)


def salvar_credenciais(valores: dict):
    """Grava várias credenciais no cofre de uma vez (valores vazios removem a chave)."""
    import core.credentials as cred
    cred.atualizar_credenciais_em_lote(valores)
