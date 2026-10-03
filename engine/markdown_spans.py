"""
Análise de texto Markdown para o editor: trechos a destacar e estatísticas.

A interface só aplica as cores; quem decide O QUE destacar é este módulo.
Posições são deslocamentos em caracteres a partir do início do texto.
"""
import re

_TITULO = re.compile(r'^(#{1,3})\s+(.*)$', re.MULTILINE)
_CITACAO = re.compile(r'^(>.*)$', re.MULTILINE)
_TODO = re.compile(r'(<--\s*(?:TODO|TO DO|To Do|To-Do|todo):?.*)', re.IGNORECASE)
_WIKILINK = re.compile(r'\[\[([^\|\]]+)(?:\|([^\]]+))?\]\]')
_NEGRITO = re.compile(r'(\*\*[^\*\n]+\*\*)')

TAGS = ["md_h1", "md_h2", "md_h3", "md_bold", "md_italic", "md_wikilink", "md_todo", "md_quote"]


def destaques(texto: str) -> list:
    """Lista de (tag, inicio, fim) para colorir o editor."""
    if not texto or not texto.strip():
        return []
    trechos = []
    for m in _TITULO.finditer(texto):
        trechos.append((f"md_h{len(m.group(1))}", m.start(), m.end()))
    for m in _CITACAO.finditer(texto):
        trechos.append(("md_quote", m.start(), m.end()))
    for m in _TODO.finditer(texto):
        trechos.append(("md_todo", m.start(), m.end()))
    for m in _WIKILINK.finditer(texto):
        trechos.append(("md_wikilink", m.start(), m.end()))
    for m in _NEGRITO.finditer(texto):
        trechos.append(("md_bold", m.start(), m.end()))
    return trechos


def alvo_wikilink(trecho: str):
    """Do texto '[[Alvo|Apelido]]' devolve 'Alvo' (ou None se não for um wikilink)."""
    m = _WIKILINK.match(trecho.strip())
    return m.group(1).strip() if m else None


def estatisticas(texto: str) -> dict:
    """Palavras, caracteres (sem quebras), linhas e tokens estimados."""
    texto = texto or ""
    palavras = len(texto.split())
    return {
        "palavras": palavras,
        "caracteres": len(texto.replace("\n", "")),
        "linhas": texto.count("\n") + 1 if texto else 0,
        "tokens": round(palavras / 0.75) if palavras else 0,
    }
