"""
Estilo do cenário em quatro eixos e sistema de regras.

Eixos (cada opção é um arquivo com descrição, diretrizes e exemplo de escrita):
  Gênero  — o tipo de história (fantasia épica, horror cósmico, mistério...)
  Tom     — a atitude do texto (sombrio, esperançoso, solene...)
  Clima   — a atmosfera da cena (opressivo, tenso, festivo...)
  Escrita — a forma da prosa (enciclopédico, para ler em voz alta, módulo, documento)

Opções do programa: locale/<idioma>/modelos/Estilos/<Eixo>/<id>.md.
Opções do Mestre:   .silent_data/Estilos/<Eixo>/<id>.md (aparecem junto, nos dois idiomas).
O padrão do projeto fica nas Opções; a aba Requisições pode trocar só para um pedido.
"""
import re
from pathlib import Path

import core.config as cfg
import core.i18n as i18n
import engine.project_utils as pu
from core.i18n import t, tc

EIXOS = ("genero", "tom", "clima", "escrita")
PASTAS_EIXO = {"genero": "Genero", "tom": "Tom", "clima": "Clima", "escrita": "Escrita"}
PADROES = {"genero": "dark_fantasy", "tom": "sombrio", "clima": "opressivo", "escrita": "enciclopedico"}
SISTEMAS_RPG = ["dnd5e", "tormenta20", "pf2e", "generico"]

# Perfil antigo "Tom e Clima" (um único seletor) -> eixos novos
_MIGRACAO_PERFIL = {
    "dark_fantasy": {"genero": "dark_fantasy", "tom": "sombrio", "clima": "opressivo"},
    "high_fantasy": {"genero": "fantasia_epica", "tom": "solene", "clima": "neutro"},
    "misterio": {"genero": "misterio", "tom": "neutro", "clima": "misterioso"},
    "cyberpunk": {"genero": "ficcao_cientifica", "tom": "sombrio", "clima": "tenso"},
    "neutro": {"genero": "fantasia_epica", "tom": "neutro", "clima": "neutro"},
}
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
ARQUIVO_TOM_ANTIGO = "Tom_e_Clima.md"


# ----------------------------------------------------------------------
# OPÇÕES DOS EIXOS
# ----------------------------------------------------------------------
def _pastas_opcoes(eixo: str, idioma: str = None) -> list:
    pasta = PASTAS_EIXO[eixo]
    idioma = i18n.normalizar_idioma(idioma or i18n.idioma_ativo())
    outros = [i for i in i18n.IDIOMAS if i != idioma]
    return ([pu.PASTA_DADOS_NEXUS / "Estilos" / pasta]
            + [pu.pasta_modelos_iniciais(i) / "Estilos" / pasta for i in [idioma] + outros])


def _arquivo_opcao(eixo: str, ident: str, idioma: str = None):
    for pasta in _pastas_opcoes(eixo, idioma):
        arquivo = pasta / f"{ident}.md"
        if arquivo.is_file():
            return arquivo
    return None


def _nome_da_opcao(arquivo: Path) -> str:
    try:
        primeira = arquivo.read_text(encoding="utf-8").lstrip().splitlines()[0]
    except (OSError, IndexError):
        return arquivo.stem
    return re.sub(r"^#+\s*", "", primeira).strip() or arquivo.stem


def opcoes(eixo: str, idioma: str = None) -> list:
    """[(id, nome)] do eixo: primeiro as opções do programa, depois as criadas pelo Mestre."""
    vistos, lista = set(), []
    pastas = _pastas_opcoes(eixo, idioma)
    for pasta in pastas[1:] + pastas[:1]:
        if pasta.is_dir():
            for arquivo in sorted(pasta.glob("*.md")):
                if arquivo.stem not in vistos:
                    vistos.add(arquivo.stem)
                    lista.append(arquivo.stem)
    return [(ident, _nome_da_opcao(_arquivo_opcao(eixo, ident, idioma))) for ident in lista]


def texto_opcao(eixo: str, ident: str, idioma: str = None) -> str:
    arquivo = _arquivo_opcao(eixo, ident, idioma)
    return arquivo.read_text(encoding="utf-8").strip() if arquivo else ""


def _migrar_perfil_antigo():
    """Projetos de versões antigas: converte 'tom_clima_perfil' nos eixos (uma vez)."""
    config = cfg.carregar_configuracoes()
    if all(f"estilo_{eixo}" in config for eixo in EIXOS):
        return
    antigo = _LEGADO_TOM.get(config.get("tom_clima_perfil"), config.get("tom_clima_perfil"))
    valores = {f"estilo_{eixo}": valor for eixo, valor in {**PADROES, **_MIGRACAO_PERFIL.get(antigo, {})}.items()}
    cfg.atualizar_configuracoes({chave: valor for chave, valor in valores.items() if chave not in config})


def padrao(eixo: str) -> str:
    """Opção padrão do projeto para o eixo (Opções)."""
    _migrar_perfil_antigo()
    valor = cfg.obter(f"estilo_{eixo}", PADROES[eixo])
    return valor if _arquivo_opcao(eixo, valor) else PADROES[eixo]


def padroes() -> dict:
    return {eixo: padrao(eixo) for eixo in EIXOS}


def definir_padrao(eixo: str, ident: str):
    if eixo in EIXOS and _arquivo_opcao(eixo, ident):
        cfg.atualizar_configuracoes({f"estilo_{eixo}": ident})


def nome_opcao(eixo: str, ident: str) -> str:
    arquivo = _arquivo_opcao(eixo, ident)
    return _nome_da_opcao(arquivo) if arquivo else ident


def bloco_estilos(escolhas: dict = None) -> str:
    """Texto dos quatro eixos escolhidos (ou os padrões do projeto), para entrar nos prompts."""
    escolhas = {**padroes(), **{k: v for k, v in (escolhas or {}).items() if v}}
    partes = [tc("estilo.bloco_cabecalho")]
    for eixo in EIXOS:
        texto = texto_opcao(eixo, escolhas[eixo])
        if texto:
            partes.append(f"<{eixo}>\n{tc(f'estilo.eixo.{eixo}')}\n{texto}\n</{eixo}>")
    return "\n\n".join(partes)


def eh_tom_e_clima_gerado(texto: str) -> bool:
    """True se o Style/Tom_e_Clima.md antigo é exatamente um texto gerado pelo programa (agora substituído pelos eixos)."""
    limpo = (texto or "").strip()
    for idioma in i18n.IDIOMAS:
        for perfil in _MIGRACAO_PERFIL:
            if limpo == i18n.traduzir(f"style.conteudo.{perfil}", idioma, "").strip():
                return True
    return False


# ----------------------------------------------------------------------
# SISTEMA DE REGRAS
# ----------------------------------------------------------------------
def _normalizar(valor, legado, validos, padrao_):
    valor = legado.get(valor, valor)
    return valor if valor in validos else padrao_


def sistema_ativo() -> str:
    return _normalizar(cfg.obter("rpg_sistema_ativo"), _LEGADO_SISTEMA, SISTEMAS_RPG, "dnd5e")


def listar_sistemas() -> list:
    return [(sid, t(f"style.sistema.{sid}")) for sid in SISTEMAS_RPG]


def definir_sistema(sistema: str):
    sistema = _normalizar(sistema, _LEGADO_SISTEMA, SISTEMAS_RPG, "dnd5e")
    cfg.atualizar_configuracoes({"rpg_sistema_ativo": sistema})


def aplicar_idioma():
    """Depois de trocar o idioma: os modelos iniciais nunca editados passam para o novo idioma."""
    pu.instalar_modelos_iniciais(cfg.obter("idioma"))
