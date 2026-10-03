"""Página de Log de Atividades (exibe o que a lógica publica em core.eventos)."""
import time
import tkinter as tk

from core.i18n import t
from ui.widgets import PaginaBase, cabecalho, texto_rolavel, anexar_texto


class PaginaLog(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("log.titulo"), t("log.subtitulo"))
        self.texto = texto_rolavel(self, fonte=("Consolas", 9))
        self.texto.configure(fg="#cccccc")
        self.texto.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

    def adicionar(self, mensagem: str):
        mensagem = str(mensagem).strip()
        if mensagem:
            anexar_texto(self.texto, f"[{time.strftime('%H:%M:%S')}] {mensagem}\n")
