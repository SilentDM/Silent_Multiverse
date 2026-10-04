"""
Histórico de versões dos arquivos do projeto.

Antes de a IA (ou uma restauração) alterar um arquivo, a versão atual é copiada para
.silent_data/logs/history/<projeto>/<pasta relativa>/<nome>_vNN.md. Daqui a interface lista
as versões e restaura qualquer uma com um clique.

Versões antigas (de antes do histórico ser separado por projeto) ficam em
logs/history/<pasta relativa>/ e continuam aparecendo; a numeração segue depois delas.
"""
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import core.eventos as ev
import engine.project_utils as pu
from core.i18n import t


class ErroHistorico(Exception):
    """Falha esperada (arquivo travado, versão inexistente) com mensagem pronta para o usuário."""


@dataclass
class Versao:
    numero: int
    caminho: Path
    data: datetime
    tamanho: int


def _pastas_historico(caminho_original: Path) -> tuple:
    """(pasta deste projeto, pasta antiga sem o nome do projeto)."""
    base = pu.PASTA_LOGS / "history"
    try:
        relativo = caminho_original.resolve().relative_to(Path(pu.CAMINHO_PROJETO).resolve()).parent
    except ValueError:
        return base / "_fora_do_projeto", base
    projeto = re.sub(r'[<>:"/\|?*]', "_", str(pu.PASTA_PROJETO))
    return base / projeto / relativo, base / relativo


def _nome_base(caminho: Path) -> str:
    return re.sub(r"_v\d+$", "", caminho.stem, flags=re.IGNORECASE)


def listar_versoes(caminho) -> list:
    """Versões arquivadas do arquivo, da mais nova para a mais antiga."""
    caminho = Path(caminho)
    base, extensao = _nome_base(caminho), caminho.suffix or ".md"
    versoes = {}
    for pasta in reversed(_pastas_historico(caminho)):          # a pasta do projeto vence em caso de empate
        if not pasta.is_dir():
            continue
        for arq in pasta.glob(f"{base}_v*{extensao}"):
            achado = re.fullmatch(re.escape(base) + r"_v(\d+)", arq.stem, flags=re.IGNORECASE)
            if achado:
                info = arq.stat()
                numero = int(achado.group(1))
                versoes[numero] = Versao(numero, arq, datetime.fromtimestamp(info.st_mtime), info.st_size)
    return sorted(versoes.values(), key=lambda v: v.numero, reverse=True)


def obter_proximo_caminho_historico(caminho_original) -> Path:
    """Próximo nome versionado (ex.: logs/history/<projeto>/Reinos/Valia_v03.md), preservando as subpastas."""
    caminho = Path(caminho_original)
    pasta = _pastas_historico(caminho)[0]
    pasta.mkdir(parents=True, exist_ok=True)
    versoes = listar_versoes(caminho)
    proximo = (versoes[0].numero if versoes else 0) + 1
    return pasta / f"{_nome_base(caminho)}_v{proximo:02d}{caminho.suffix or '.md'}"


def arquivar_versao_para_historico(caminho_original):
    """
    Copia a versão atual para o histórico. Cópia (não mover): se a escrita da nova
    versão falhar, o original fica intacto. Devolve o caminho arquivado ou None.
    """
    caminho = Path(caminho_original)
    try:
        if not caminho.exists():
            return None
        destino = obter_proximo_caminho_historico(caminho)
        shutil.copy2(str(caminho), str(destino))
        ev.log(t("expander.log_backup", nome=destino.name))
        return destino
    except Exception as e:
        ev.log(t("expander.log_erro_backup", nome=caminho.name, erro=e))
        return None


def ler_versao(versao: Versao) -> str:
    return Path(versao.caminho).read_text(encoding="utf-8", errors="ignore")


def restaurar_versao(caminho, versao: Versao) -> Path:
    """
    Volta o arquivo para a versão escolhida. A versão atual é arquivada antes,
    então a própria restauração pode ser desfeita pelo histórico.
    """
    import engine.expander as ex
    caminho = Path(caminho)
    if ex.esta_em_processamento(caminho):
        raise ErroHistorico(t("historico.erro_travado", nome=caminho.name))
    if not Path(versao.caminho).is_file():
        raise ErroHistorico(t("historico.erro_versao", numero=versao.numero))
    if caminho.exists():
        arquivar_versao_para_historico(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(versao.caminho), str(caminho))
    ev.log(t("historico.log_restaurado", nome=caminho.name, numero=versao.numero))
    return caminho
