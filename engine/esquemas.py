"""
Esquemas de propriedades: que chaves (YAML do Obsidian) cada tipo de arquivo deve ter.

As chaves vêm do bloco de propriedades dos templates. Para um tipo (type: cidade), vale o template
encontrado primeiro, na mesma ordem em que o WorldBuilder procura templates:
<projeto>/Templates (os do cofre do Obsidian) > .silent_data/Templates > modelos do programa.
Variantes por gênero (Templates/misterio/cidade.md) acrescentam as chaves que tiverem a mais.

Ao gravar o que a IA escreveu, a hierarquia é: o que já está no arquivo > o que a IA preencheu nas
chaves vazias > o padrão do template. Chaves que a IA inventar fora do esquema são descartadas.
"""
from pathlib import Path

import core.config as cfg
import core.propriedades as propriedades
import engine.project_utils as pu
from core.prompts import carregar_prompt


def _pastas_templates() -> list:
    return [Path(pu.CAMINHO_PROJETO) / "Templates", pu.PASTA_TEMPLATES,
            pu.pasta_modelos_iniciais(cfg.obter("idioma", "pt_br")) / "Templates"]


def catalogo() -> dict:
    """{tipo em minúsculas: [(chave, padrão)]} a partir dos templates que têm bloco de propriedades."""
    tipos = {}
    for pasta in _pastas_templates():
        if not pasta.is_dir():
            continue
        vistos_nesta_pasta = set()
        for arquivo in sorted(pasta.rglob("*.md"), key=lambda a: (len(a.relative_to(pasta).parts), a.name)):
            try:
                texto = arquivo.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            esquema = propriedades.esquema_de(texto)
            tipo = propriedades.valor_de(dict(esquema), "type")
            if not esquema or not tipo or isinstance(tipo, list):
                continue
            tipo = str(tipo).strip().lower()
            if tipo in tipos and tipo not in vistos_nesta_pasta:
                continue                                  # uma pasta com mais prioridade já definiu este tipo
            vistos_nesta_pasta.add(tipo)
            atual = tipos.setdefault(tipo, [])
            conhecidas = {c.lower() for c, _ in atual}
            atual += [(c, p) for c, p in esquema if c.lower() not in conhecidas]
    return tipos


def _com_base(esquema: list) -> list:
    """O esquema do template com as chaves básicas (type, tags, aliases) garantidas."""
    conhecidas = {c.lower() for c, _ in esquema}
    return list(esquema) + [(c, p) for c, p in propriedades.CHAVES_BASE if c not in conhecidas]


def _tipo_do(texto: str):
    tipo = propriedades.valor_de(propriedades.ler(texto or ""), "type")
    return str(tipo).strip().lower() if tipo and not isinstance(tipo, list) else None


def esquema_do_arquivo(texto: str, catalogo_tipos: dict = None):
    """Esquema do tipo do arquivo, ou None se o arquivo ainda não tem um tipo conhecido."""
    catalogo_tipos = catalogo() if catalogo_tipos is None else catalogo_tipos
    tipo = _tipo_do(texto)
    return _com_base(catalogo_tipos[tipo]) if tipo in catalogo_tipos else None


def esquema_final(original: str, saida_ia: str) -> tuple:
    """
    (esquema, veio_de_template): o do tipo do arquivo; sem tipo, o do tipo que a IA escolheu;
    senão, só as chaves básicas.
    """
    tipos = catalogo()
    esquema = esquema_do_arquivo(original, tipos) or esquema_do_arquivo(saida_ia, tipos)
    return (esquema, True) if esquema else (list(propriedades.CHAVES_BASE), False)


def aplicar(original: str, novo: str, saida_ia: str = None) -> str:
    """O texto novo com as propriedades completadas pelo esquema (ver a hierarquia no topo do módulo)."""
    saida_ia = novo if saida_ia is None else saida_ia
    esquema, de_template = esquema_final(original, saida_ia)
    # Campos vazios só aparecem quando são a estrutura de um template
    return propriedades.aplicar_esquema(original, novo, esquema, propriedades.ler(saida_ia), incluir_vazias=de_template)


def _descrever(esquema: list) -> str:
    linhas = []
    for chave, padrao in esquema:
        if propriedades.vazio(padrao):
            linhas.append(f"- {chave}")
        else:
            linhas.append(f"- {chave} ({', '.join(padrao) if isinstance(padrao, list) else padrao})")
    return "\n".join(linhas)


def bloco_prompt(texto_arquivo: str) -> str:
    """Instruções para a IA preencher as propriedades do arquivo (prompt melhorar_propriedades)."""
    tipos = catalogo()
    esquema = esquema_do_arquivo(texto_arquivo, tipos)
    linhas_atuais, _ = propriedades.separar(propriedades.normalizar(texto_arquivo or ""))
    atuais = "\n".join(linhas_atuais) if linhas_atuais else "-"
    if esquema:
        opcoes = ""
    else:
        esquema = list(propriedades.CHAVES_BASE)
        opcoes = "\n".join(f"- {tipo}: {', '.join(c for c, _ in chaves if c.lower() not in ('type', 'tags', 'aliases'))}"
                           for tipo, chaves in sorted(tipos.items()))
    return carregar_prompt("melhorar_propriedades", chaves=_descrever(esquema), atuais=atuais,
                           tipos=carregar_prompt("melhorar_propriedades_tipos", tipos=opcoes) if opcoes else "")
