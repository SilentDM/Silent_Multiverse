"""Página do Manual (conteúdo em locale/<idioma>/manual.md)."""
import tkinter as tk

import core.manual as manual
import ui.theme as tema
from core.i18n import t
from ui.widgets import PaginaBase, cabecalho, texto_rolavel


class PaginaManual(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("manual.titulo"), t("manual.subtitulo"))
        texto = texto_rolavel(self, somente_leitura=False)
        texto.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        texto.tag_config("h1", font=("Segoe UI", 13, "bold"), foreground=tema.VERDE, spacing1=14, spacing3=6)
        texto.tag_config("h2", font=("Segoe UI", 11, "bold"), foreground=tema.AZUL_CLARO, spacing1=10, spacing3=4)
        texto.tag_config("bullet", font=("Segoe UI", 10), foreground="#cccccc", lmargin1=15, lmargin2=30)
        texto.tag_config("p", font=("Segoe UI", 10), foreground="#cccccc", lmargin1=15, lmargin2=15)
        texto.tag_config("note", font=("Segoe UI", 9, "italic"), foreground="#34d399", lmargin1=15)
        texto.tag_config("code", font=("Consolas", 10, "bold"), foreground=tema.LARANJA, background="#2a1205")
        for estilo, conteudo in manual.carregar_manual():
            texto.insert(tk.END, conteudo + "\n", estilo)
        texto.config(state=tk.DISABLED)
