"""Janela com o relatório da Auditoria de Lore."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import engine.lore_auditor as auditor
import engine.project_utils as pu
import ui.theme as tema
from core.i18n import t
from ui.widgets import texto_rolavel, substituir_texto


class JanelaAuditoria(tk.Toplevel):
    def __init__(self, parent, relatorio: str, toast=None, ao_corrigir=None):
        super().__init__(parent)
        self.relatorio = relatorio
        self.toast = toast or (lambda m: None)
        self.title(t("auditoria.janela_titulo", projeto=pu.PASTA_PROJETO))
        self.geometry("850x650")
        self.minsize(600, 400)
        self.configure(bg=tema.FUNDO)

        tk.Label(self, text=t("auditoria.janela_cabecalho"), font=("Segoe UI", 12, "bold"),
                 bg=tema.FUNDO, fg=tema.VERDE).pack(anchor=tk.W, padx=15, pady=10)
        texto = texto_rolavel(self, fonte=("Consolas", 10), somente_leitura=False)
        self.texto = texto
        texto.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        substituir_texto(texto, relatorio, somente_leitura=False)

        botoes = tk.Frame(self, bg=tema.FUNDO)
        botoes.pack(fill=tk.X, padx=15, pady=10)
        ttk.Button(botoes, text=t("auditoria.btn_salvar"), command=self._salvar).pack(side=tk.LEFT)
        if ao_corrigir:
            # Manda o relatório (com as edições feitas aqui) para o WorldBuilder montar o plano de correção
            ttk.Button(botoes, text=t("auditoria.btn_corrigir"),
                       command=lambda: (ao_corrigir(self.texto.get("1.0", "end").strip()), self.destroy())
                       ).pack(side=tk.LEFT, padx=8)
        ttk.Button(botoes, text=t("comum.fechar"), command=self.destroy).pack(side=tk.RIGHT)

    def _salvar(self):
        padrao = auditor.caminho_padrao_relatorio()
        destino = filedialog.asksaveasfilename(
            parent=self, initialdir=str(padrao.parent), initialfile=padrao.name, defaultextension=".md",
            filetypes=[("Markdown", "*.md"), (t("comum.texto"), "*.txt")])
        if not destino:
            return
        try:
            auditor.salvar_relatorio(destino, self.relatorio)
            self.toast(t("auditoria.toast_salvo"))
        except Exception as e:
            messagebox.showerror(t("comum.erro_salvar"), str(e), parent=self)
