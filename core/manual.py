"""
Manual do programa (locale/<idioma>/manual.md) convertido em blocos com estilo.

Marcação simples:  "# " título,  "## " subtítulo,  "- " item,
"> " nota,  blocos entre ``` como código; linhas comuns viram parágrafo.
"""
import core.i18n as i18n


def carregar_manual(idioma: str = None) -> list:
    """Lista de (estilo, texto) com estilo ∈ {h1, h2, bullet, note, code, p}."""
    idioma = i18n.normalizar_idioma(idioma or i18n.idioma_interface())
    caminho = i18n.pasta_locale() / idioma / "manual.md"
    if not caminho.exists():
        caminho = i18n.pasta_locale() / i18n.IDIOMA_PADRAO / "manual.md"
    blocos, codigo, em_codigo = [], [], False
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if linha.strip().startswith("```"):
            if em_codigo:
                blocos.append(("code", "\n".join(codigo)))
                codigo = []
            em_codigo = not em_codigo
            continue
        if em_codigo:
            codigo.append(linha)
        elif linha.startswith("## "):
            blocos.append(("h2", linha[3:]))
        elif linha.startswith("# "):
            blocos.append(("h1", linha[2:]))
        elif linha.startswith("- "):
            blocos.append(("bullet", "  • " + linha[2:]))
        elif linha.startswith("> "):
            blocos.append(("note", linha[2:]))
        elif linha.strip():
            blocos.append(("p", linha))
    return blocos
