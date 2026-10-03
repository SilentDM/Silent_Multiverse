"""Janela modal para criar um arquivo (nome + template opcional)."""
import tkinter as tk
from tkinter import ttk, messagebox

import ui.theme as tema
from core.i18n import t


class DialogoNovoArquivo(tk.Toplevel):
    """Após fechar: .nome (str ou None) e .template (str ou None = sem template)."""

    def __init__(self, parent, templates: list):
        super().__init__(parent)
        self.title(t("novo.titulo"))
        self.geometry("420x230")
        self.resizable(False, False)
        self.configure(bg=tema.FUNDO)
        self.transient(parent)
        self.grab_set()
        self.nome = None
        self.template = None
        self._sem_template = t("novo.sem_template")

        quadro = ttk.Frame(self)
        quadro.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        ttk.Label(quadro, text=t("novo.nome"), font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 4))
        self.entrada = ttk.Entry(quadro, font=("Segoe UI", 10))
        self.entrada.pack(fill=tk.X, pady=(0, 14))
        self.entrada.focus_set()
        self.entrada.bind("<Return>", lambda e: self._confirmar())
        ttk.Label(quadro, text=t("novo.template"), font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 4))
        self.combo = ttk.Combobox(quadro, values=[self._sem_template] + templates, state="readonly", font=("Segoe UI", 10))
        self.combo.set(self._sem_template)
        self.combo.pack(fill=tk.X, pady=(0, 20))
        botoes = ttk.Frame(quadro)
        botoes.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(botoes, text=t("comum.cancelar"), command=self.destroy).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(botoes, text=t("novo.criar"), command=self._confirmar).pack(side=tk.RIGHT)
        self.wait_window()

    def _confirmar(self):
        nome = self.entrada.get().strip()
        if not nome:
            messagebox.showwarning(t("comum.aviso"), t("novo.digite_nome"), parent=self)
            return
        self.nome = nome
        escolhido = self.combo.get()
        self.template = None if escolhido == self._sem_template else escolhido
        self.destroy()
