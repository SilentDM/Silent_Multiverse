"""Abertura rápida (Ctrl+P): digite parte do nome e Enter abre o arquivo no Editor."""
import tkinter as tk
from tkinter import ttk

import engine.documento as documento
import ui.theme as tema
from core.i18n import t


class JanelaAberturaRapida(tk.Toplevel):
    def __init__(self, app, ao_escolher):
        super().__init__(app.root)
        self.ao_escolher = ao_escolher
        self.resultados = []
        self.title(t("editor.rapido_titulo"))
        self.configure(bg=tema.FUNDO)
        self.transient(app.root)
        largura, altura = 620, 400
        x = app.root.winfo_rootx() + (app.root.winfo_width() - largura) // 2
        y = app.root.winfo_rooty() + 90
        self.geometry(f"{largura}x{altura}+{max(x, 0)}+{max(y, 0)}")

        self.var = tk.StringVar()
        entrada = ttk.Entry(self, textvariable=self.var, font=("Segoe UI", 12))
        entrada.pack(fill=tk.X, padx=12, pady=(12, 6))
        ttk.Label(self, text=t("editor.rapido_dica"), style="Dica.TLabel").pack(anchor=tk.W, padx=12)
        self.lista = tk.Listbox(self, bg=tema.PAINEL, fg=tema.TEXTO, font=("Segoe UI", 10), borderwidth=0,
                                highlightthickness=0, activestyle="none", selectbackground=tema.VERDE_ESCURO)
        self.lista.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 12))

        self.var.trace_add("write", lambda *_: self._filtrar())
        for widget in (entrada, self.lista):
            widget.bind("<Return>", lambda e: self._escolher())
            widget.bind("<Escape>", lambda e: self.destroy())
        entrada.bind("<Down>", lambda e: self._mover(1))
        entrada.bind("<Up>", lambda e: self._mover(-1))
        self.lista.bind("<Double-1>", lambda e: self._escolher())
        self._filtrar()
        entrada.focus_set()

    def _filtrar(self):
        self.resultados = documento.buscar_arquivos(self.var.get())
        self.lista.delete(0, tk.END)
        for nome, relativo, _ in self.resultados:
            self.lista.insert(tk.END, f"{nome}    —    {relativo}")
        if self.resultados:
            self.lista.selection_set(0)

    def _mover(self, delta):
        if not self.resultados:
            return "break"
        atual = self.lista.curselection()
        novo = max(0, min(len(self.resultados) - 1, (atual[0] if atual else 0) + delta))
        self.lista.selection_clear(0, tk.END)
        self.lista.selection_set(novo)
        self.lista.see(novo)
        return "break"

    def _escolher(self):
        selecao = self.lista.curselection()
        if selecao and selecao[0] < len(self.resultados):
            caminho = self.resultados[selecao[0]][2]
            self.destroy()
            self.ao_escolher(caminho)
