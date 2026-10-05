"""
Verifica se há uma versão mais nova publicada nas Releases do GitHub.

Lê a lista de releases publicadas (ignora rascunhos e pré-lançamentos) e compara
o maior número de versão encontrado no nome da tag (ex.: "v2.1.0", "Release_V1.1.0")
com core.versao.VERSAO. Não usa o "Latest" do GitHub, que pode estar marcado numa
release antiga. Nada é baixado ou instalado: a interface só mostra o link.
"""
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

import core.config as cfg
import core.eventos as ev
from core.i18n import t
from core.versao import VERSAO, REPOSITORIO, URL_RELEASES

URL_API = f"https://api.github.com/repos/{REPOSITORIO}/releases?per_page=30"
TEMPO_LIMITE = 8


@dataclass
class NovaVersao:
    versao: str
    url: str
    notas: str = ""


def numero_versao(texto: str):
    """'Release_V1.2' -> (1, 2, 0). None se o texto não tiver número de versão."""
    achado = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", texto or "")
    if not achado:
        return None
    return tuple(int(g or 0) for g in achado.groups())


def _baixar_releases() -> list:
    pedido = urllib.request.Request(URL_API, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"SilentMultiverse/{VERSAO}",
    })
    with urllib.request.urlopen(pedido, timeout=TEMPO_LIMITE) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def escolher_mais_nova(releases: list, versao_atual: str = VERSAO):
    """Entre as releases publicadas, devolve NovaVersao da maior que seja mais nova que a atual (ou None)."""
    atual = numero_versao(versao_atual) or (0, 0, 0)
    melhor, melhor_numero = None, atual
    for release in releases or []:
        if release.get("draft") or release.get("prerelease"):
            continue
        numero = numero_versao(release.get("tag_name", "")) or numero_versao(release.get("name", ""))
        if numero and numero > melhor_numero:
            melhor, melhor_numero = release, numero
    if melhor is None:
        return None
    return NovaVersao(versao=".".join(map(str, melhor_numero)),
                      url=melhor.get("html_url") or URL_RELEASES,
                      notas=(melhor.get("body") or "").strip())


def verificar() -> "NovaVersao | None":
    """Consulta o GitHub agora. Lança exceção em falha de rede (para a verificação manual avisar)."""
    try:
        releases = _baixar_releases()
    except urllib.error.HTTPError as e:
        if e.code == 404:          # repositório sem releases
            return None
        raise
    nova = escolher_mais_nova(releases)
    if nova:
        ev.emitir("atualizacao.disponivel", nova)
    return nova


def verificar_na_inicializacao():
    """Verificação silenciosa ao abrir o programa (se ativada nas Opções). Falhas só vão para o Log."""
    if not cfg.obter("verificar_atualizacoes", True):
        return None
    try:
        nova = verificar()
    except Exception as e:
        ev.log(t("update.log_erro", erro=e))
        return None
    if nova:
        ev.log(t("update.log_disponivel", versao=nova.versao, url=nova.url))
    return nova


def verificacao_automatica_ativa() -> bool:
    return bool(cfg.obter("verificar_atualizacoes", True))


def definir_verificacao_automatica(ativa: bool):
    cfg.atualizar_configuracoes({"verificar_atualizacoes": bool(ativa)})
