"""
Perfis de Tom & Clima e Sistema de Regras do cenário.

Escreve Style/Tom_e_Clima.md (lido pelo Expander, Aventuras e Lore Checks como
diretriz de estilo) no idioma ativo. Antes vivia dentro da tela de Opções.
"""
import core.config as cfg
import engine.project_utils as pu
from core.i18n import t, tc

PERFIS_TOM = ["dark_fantasy", "high_fantasy", "misterio", "cyberpunk", "neutro"]
SISTEMAS_RPG = ["dnd5e", "tormenta20", "pf2e", "generico"]

# Valores antigos (rótulos em português gravados no settings.json) -> IDs atuais
_LEGADO_TOM = {
    "Dark Fantasy (Grimdark)": "dark_fantasy",
    "High Fantasy Épico": "high_fantasy",
    "Mistério & Investigação": "misterio",
    "Cyberpunk / Sci-Fi": "cyberpunk",
    "Nenhum / Neutro": "neutro",
}
_LEGADO_SISTEMA = {
    "D&D 5e": "dnd5e",
    "Tormenta20": "tormenta20",
    "Pathfinder 2e": "pf2e",
    "Generic / Regras Livres": "generico",
}

ARQUIVO_TOM = "Tom_e_Clima.md"


def _normalizar(valor, legado, validos, padrao):
    valor = legado.get(valor, valor)
    return valor if valor in validos else padrao


def perfil_tom_ativo() -> str:
    return _normalizar(cfg.obter("tom_clima_perfil"), _LEGADO_TOM, PERFIS_TOM, "dark_fantasy")


def sistema_ativo() -> str:
    return _normalizar(cfg.obter("rpg_sistema_ativo"), _LEGADO_SISTEMA, SISTEMAS_RPG, "dnd5e")


def listar_perfis_tom() -> list:
    """[(id, rótulo traduzido)] para exibir na interface."""
    return [(pid, t(f"style.tom.{pid}")) for pid in PERFIS_TOM]


def listar_sistemas() -> list:
    return [(sid, t(f"style.sistema.{sid}")) for sid in SISTEMAS_RPG]


def escrever_arquivo_estilo_tom(perfil: str = None):
    """Grava Style/Tom_e_Clima.md com a diretriz do perfil, no idioma ativo."""
    perfil = _normalizar(perfil or perfil_tom_ativo(), _LEGADO_TOM, PERFIS_TOM, "neutro")
    try:
        pu.CAMINHO_ESTILO.mkdir(parents=True, exist_ok=True)
        (pu.CAMINHO_ESTILO / ARQUIVO_TOM).write_text(tc(f"style.conteudo.{perfil}"), encoding="utf-8")
    except Exception as e:
        print(f"Erro ao escrever arquivo de tom em Style: {e}")


def definir_perfil_tom(perfil: str):
    perfil = _normalizar(perfil, _LEGADO_TOM, PERFIS_TOM, "dark_fantasy")
    cfg.atualizar_configuracoes({"tom_clima_perfil": perfil})
    escrever_arquivo_estilo_tom(perfil)


def definir_sistema(sistema: str):
    sistema = _normalizar(sistema, _LEGADO_SISTEMA, SISTEMAS_RPG, "dnd5e")
    cfg.atualizar_configuracoes({"rpg_sistema_ativo": sistema})
