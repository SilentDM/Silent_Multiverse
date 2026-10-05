"""Página do Manual (conteúdo em locale/<idioma>/manual.md), com índice clicável das seções."""
import tkinter as tk
from tkinter import ttk

import core.manual as manual
import ui.theme as tema
from core.i18n import t
from ui.widgets import PaginaBase, cabecalho, texto_rolavel


class PaginaManual(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("manual.titulo"), t("manual.subtitulo"))
        corpo = ttk.Frame(self)
        corpo.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        indice = ttk.LabelFrame(corpo, text=t("manual.indice"))
        indice.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        self.lista = tk.Listbox(indice, width=42, bg=tema.FUNDO_SIDEBAR, fg=tema.TEXTO, borderwidth=0,
                                highlightthickness=0, activestyle="none", font=("Segoe UI", 9),
                                selectbackground=tema.AZUL)
        self.lista.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.lista.bind("<<ListboxSelect>>", self._ir_para_secao)

        self.texto = texto_rolavel(corpo, somente_leitura=False)
        self.texto.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        texto = self.texto
        texto.tag_config("h1", font=("Segoe UI", 13, "bold"), foreground=tema.VERDE, spacing1=14, spacing3=6)
        texto.tag_config("h2", font=("Segoe UI", 11, "bold"), foreground=tema.AZUL_CLARO, spacing1=10, spacing3=4)
        texto.tag_config("bullet", font=("Segoe UI", 10), foreground="#cccccc", lmargin1=15, lmargin2=30)
        texto.tag_config("p", font=("Segoe UI", 10), foreground="#cccccc", lmargin1=15, lmargin2=15)
        texto.tag_config("note", font=("Segoe UI", 9, "italic"), foreground="#34d399", lmargin1=15, lmargin2=15)
        texto.tag_config("code", font=("Consolas", 10, "bold"), foreground=tema.LARANJA, background="#2a1205")

        self._secoes = []
        for estilo, conteudo in manual.carregar_manual():
            if estilo == "h1":
                marca = f"secao{len(self._secoes)}"
                texto.mark_set(marca, tk.END + "-1c")
                texto.mark_gravity(marca, tk.LEFT)
                self._secoes.append(marca)
                self.lista.insert(tk.END, conteudo)
            texto.insert(tk.END, conteudo + "\n", estilo)
        texto.config(state=tk.DISABLED)

    def _ir_para_secao(self, _evento=None):
        selecao = self.lista.curselection()
        if selecao:
            self.texto.yview(self._secoes[selecao[0]])
