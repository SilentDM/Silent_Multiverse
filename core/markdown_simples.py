"""
Markdown → trechos com estilo, para mostrar respostas da IA formatadas num widget de texto
(o chat do Silent). Sem Tk: devolve [(texto, (tags...))] e a interface só aplica as tags.

Cobre o que a IA costuma usar: títulos, listas, citações, blocos de código, tabelas,
linhas horizontais, **negrito**, *itálico*, `código` e [[links]] do projeto.
"""
import re

_TITULO = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_LISTA = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_NUMERADA = re.compile(r"^(\s*)(\d+[.)])\s+(.*)$")
_REGRA = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
_INLINE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__|`([^`]+)`|\[\[([^\]\n]+)\]\]|(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)"
                     r"|(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])")


def _inline(texto: str, base: tuple) -> list:
    trechos, pos = [], 0
    for achado in _INLINE.finditer(texto):
        if achado.start() > pos:
            trechos.append((texto[pos:achado.start()], base))
        negrito, negrito2, codigo, link, italico, italico2 = achado.groups()
        if negrito is not None or negrito2 is not None:
            trechos.extend(_inline(negrito if negrito is not None else negrito2, base + ("negrito",)))
        elif codigo is not None:
            trechos.append((codigo, base + ("codigo",)))
        elif link is not None:
            trechos.append((link, base + ("link",)))
        else:
            trechos.extend(_inline(italico if italico is not None else italico2, base + ("italico",)))
        pos = achado.end()
    if pos < len(texto):
        trechos.append((texto[pos:], base))
    return trechos


def segmentos(texto: str) -> list:
    """[(trecho, tags)] prontos para inserir em ordem; as quebras de linha já vêm nos trechos."""
    saida, em_codigo = [], False
    for linha in (texto or "").replace("\r\n", "\n").split("\n"):
        if linha.strip().startswith("```"):
            em_codigo = not em_codigo
            continue
        if em_codigo:
            saida.append((linha + "\n", ("bloco_codigo",)))
            continue
        titulo = _TITULO.match(linha)
        if titulo:
            nivel = min(len(titulo.group(1)), 3)
            saida.extend(_inline(titulo.group(2), (f"h{nivel}",)))
            saida.append(("\n", (f"h{nivel}",)))
            continue
        if _REGRA.match(linha):
            saida.append(("─" * 40 + "\n", ("regra",)))
            continue
        if linha.lstrip().startswith("|"):
            saida.append((linha + "\n", ("tabela",)))
            continue
        if linha.lstrip().startswith(">"):
            saida.extend(_inline(linha.lstrip()[1:].lstrip(), ("citacao",)))
            saida.append(("\n", ("citacao",)))
            continue
        lista = _LISTA.match(linha)
        numerada = None if lista else _NUMERADA.match(linha)
        if lista or numerada:
            recuo = len((lista or numerada).group(1).expandtabs(4)) // 2
            marcador = "•" if lista else numerada.group(2)
            corpo = lista.group(2) if lista else numerada.group(3)
            saida.append(("    " * recuo + f"  {marcador} ", ("lista",)))
            saida.extend(_inline(corpo, ("lista",)))
            saida.append(("\n", ("lista",)))
            continue
        saida.extend(_inline(linha, ()))
        saida.append(("\n", ()))
    while saida and saida[-1][0] == "\n":
        saida.pop()
    return saida
