"""
Traduções da interface e do conteúdo gerado (PT-BR / EN-US).

Estrutura: locale/<idioma>/*.json  (todos os .json da pasta são mesclados)
           locale/<idioma>/manual.md
           locale/<idioma>/prompts/*.md   (lidos por core/prompts.py)

Dois "idiomas" convivem:
- idioma da INTERFACE: lido uma vez na inicialização; mudar exige reiniciar.  -> t()
- idioma do CONTEÚDO/IA: lido a cada chamada; muda na hora.                    -> tc()
"""
import json
import sys
from pathlib import Path

IDIOMAS = {
    "pt_br": "Português (Brasil)",
    "en_us": "English (US)",
}
IDIOMA_PADRAO = "pt_br"

# Nome do idioma usado DENTRO dos prompts ("Responda em ...")
NOME_IDIOMA_PARA_IA = {
    "pt_br": "português do Brasil",
    "en_us": "American English",
}

_cache: dict = {}
_idioma_interface = None


def pasta_locale() -> Path:
    """Pasta locale/ ao lado do código ou embutida pelo PyInstaller (_MEIPASS)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "locale"
    return Path(__file__).resolve().parent.parent / "locale"


def normalizar_idioma(codigo) -> str:
    codigo = str(codigo or "").strip().lower().replace("-", "_")
    return codigo if codigo in IDIOMAS else IDIOMA_PADRAO


def carregar_textos(idioma: str) -> dict:
    """Mescla todos os .json de locale/<idioma>/ (cache em memória)."""
    idioma = normalizar_idioma(idioma)
    if idioma not in _cache:
        textos = {}
        pasta = pasta_locale() / idioma
        for arq in sorted(pasta.glob("*.json")):
            try:
                with open(arq, "r", encoding="utf-8") as f:
                    textos.update(json.load(f))
            except Exception as e:
                print(f"[i18n] Erro ao ler {arq}: {e}")
        _cache[idioma] = textos
    return _cache[idioma]


def recarregar():
    """Limpa o cache (útil em testes ou ao editar os arquivos de tradução)."""
    _cache.clear()


def idioma_ativo() -> str:
    """Idioma atual configurado (lido do settings.json a cada chamada) — usado pela IA e conteúdo gerado."""
    import core.config as cfg
    return normalizar_idioma(cfg.obter("idioma", IDIOMA_PADRAO))


def idioma_interface() -> str:
    """Idioma da interface, fixado na primeira leitura (troca só após reiniciar o programa)."""
    global _idioma_interface
    if _idioma_interface is None:
        _idioma_interface = idioma_ativo()
    return _idioma_interface


def definir_idioma(codigo: str) -> str:
    """Salva o novo idioma. A IA passa a usá-lo imediatamente; a interface após reiniciar."""
    import core.config as cfg
    codigo = normalizar_idioma(codigo)
    cfg.atualizar_configuracoes({"idioma": codigo})
    return codigo


class _Seguro(dict):
    """Mantém {variavel} intacta se não for informada, em vez de quebrar a formatação."""
    def __missing__(self, chave):
        return "{" + chave + "}"


def traduzir(chave: str, idioma: str, padrao=None, **variaveis) -> str:
    texto = carregar_textos(idioma).get(chave)
    if texto is None and idioma != IDIOMA_PADRAO:
        texto = carregar_textos(IDIOMA_PADRAO).get(chave)
    if texto is None:
        texto = padrao if padrao is not None else chave
    if variaveis:
        try:
            texto = texto.format_map(_Seguro(variaveis))
        except (ValueError, IndexError):
            pass
    return texto


def t(chave: str, **variaveis) -> str:
    """Texto da INTERFACE (rótulos, botões, avisos, logs exibidos ao usuário)."""
    return traduzir(chave, idioma_interface(), **variaveis)


def tc(chave: str, **variaveis) -> str:
    """Texto do CONTEÚDO gerado e da IA (Markdown gerado, respostas do bot) no idioma ativo."""
    return traduzir(chave, idioma_ativo(), **variaveis)


def nome_idioma_ia(idioma: str = None) -> str:
    return NOME_IDIOMA_PARA_IA[normalizar_idioma(idioma or idioma_ativo())]
