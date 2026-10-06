"""
Atalhos de pedido do chat do Silent: textos prontos que o Mestre clica para não digitar
de novo (Resumir, Nomes, Ganchos...). Um [trecho entre colchetes] marca o que completar.

Os atalhos padrão vêm de locale/<idioma>/chat/atalhos.json. Quando o Mestre edita a lista,
ela é salva em .silent_data/logs/atalhos_chat.json e passa a valer em vez dos padrões.
"""
import json

import engine.project_utils as pu
from core.i18n import pasta_locale, idioma_interface


def _arquivo_usuario():
    return pu.PASTA_LOGS / "atalhos_chat.json"


def _validos(lista) -> list:
    atalhos = []
    for item in lista or []:
        if isinstance(item, dict):
            nome, texto = str(item.get("nome", "")).strip(), str(item.get("texto", "")).strip()
            if nome and texto:
                atalhos.append({"nome": nome, "texto": texto})
    return atalhos


def padroes(idioma: str = None) -> list:
    caminho = pasta_locale() / (idioma or idioma_interface()) / "chat" / "atalhos.json"
    try:
        return _validos(json.loads(caminho.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return []


def listar() -> list:
    """[{"nome", "texto"}]: os atalhos do Mestre, ou os padrões do idioma se ele nunca editou."""
    try:
        return _validos(json.loads(_arquivo_usuario().read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return padroes()


def salvar(atalhos: list) -> list:
    atalhos = _validos(atalhos)
    pu.PASTA_LOGS.mkdir(parents=True, exist_ok=True)
    _arquivo_usuario().write_text(json.dumps(atalhos, ensure_ascii=False, indent=2), encoding="utf-8")
    return atalhos


def restaurar_padroes() -> list:
    """Volta aos atalhos padrão do idioma (apaga a lista editada)."""
    try:
        _arquivo_usuario().unlink()
    except OSError:
        pass
    return padroes()


def primeiro_campo(texto: str):
    """(início, fim) do primeiro [trecho a completar] do texto, ou None."""
    inicio = texto.find("[")
    fim = texto.find("]", inicio + 1) if inicio >= 0 else -1
    if inicio < 0 or fim < 0 or texto[inicio:inicio + 2] == "[[":
        return None
    return inicio, fim + 1
