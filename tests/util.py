"""Utilitários dos testes: projetos temporários, IA falsa e troca de idioma."""
import contextlib
import shutil
import tempfile
from pathlib import Path

from tests import PASTA_TEMP  # garante o isolamento antes dos imports abaixo

import core.ai_utils as au
import core.config as cfg
import core.i18n as i18n
import engine.project_utils as pu


def novo_projeto(arquivos: dict) -> Path:
    """Cria um projeto temporário com {caminho_relativo: conteudo} e o torna o projeto ativo."""
    raiz = Path(tempfile.mkdtemp(prefix="proj_", dir=PASTA_TEMP))
    for relativo, conteudo in arquivos.items():
        caminho = raiz / relativo
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding="utf-8")
    pu.definir_projeto_ativo(raiz)
    return raiz


def apagar(caminho: Path):
    shutil.rmtree(caminho, ignore_errors=True)


def usar_idioma(codigo: str, interface: bool = True):
    """Muda o idioma ativo (IA/conteúdo) e, por padrão, também o da interface."""
    cfg.atualizar_configuracoes({"idioma": codigo})
    if interface:
        i18n._idioma_interface = None


class IAFalsa:
    """Substitui o provedor de IA: registra cada chamada e devolve 'resposta' (texto ou função)."""

    def __init__(self, resposta="ok"):
        self.resposta = resposta
        self.chamadas = []

    def __call__(self, **kwargs):
        self.chamadas.append(kwargs)
        return self.resposta(kwargs) if callable(self.resposta) else self.resposta

    @property
    def ultima(self) -> dict:
        return self.chamadas[-1]


@contextlib.contextmanager
def ia_falsa(resposta="ok"):
    falsa = IAFalsa(resposta)
    original = au._obter_implementacao
    au._obter_implementacao = lambda: falsa
    try:
        yield falsa
    finally:
        au._obter_implementacao = original
