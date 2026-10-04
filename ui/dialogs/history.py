"""Janela de Histórico: versões anteriores de um arquivo, com pré-visualização e restauração em um clique."""
import tkinter as tk
from tkinter import ttk, messagebox

import engine.acoes as acoes
import engine.arquivos as arq
import ui.theme as tema
from core.i18n import t
from ui.widgets import texto_rolavel, substituir_texto


class JanelaHistorico(tk.Toplevel):
    def __init__(self, parent, caminho: str, toast_callback=None, ao_restaurar=None):
        super().__init__(parent)
        self.caminho = caminho
        self.toast = toast_callback or (lambda m: None)
        self.ao_restaurar = ao_restaurar or (lambda c: None)
        self.versoes = []
        self.title(t("historico.janela_titulo", nome=arq.nome(caminho)))
        self.geometry("900x560")
        self.minsize(640, 380)
        self.configure(bg=tema.FUNDO)
        self.transient(parent)

        tk.Label(self, text=t("historico.cabecalho", nome=arq.nome(caminho)), font=("Segoe UI", 12, "bold"),
                 bg=tema.FUNDO, fg=tema.VERDE).pack(anchor=tk.W, padx=15, pady=(12, 2))
        tk.Label(self, text=t("historico.explicacao"), font=("Segoe UI", 9), bg=tema.FUNDO, fg=tema.SUAVE,
                 justify="left", wraplength=860).pack(anchor=tk.W, padx=15, pady=(0, 8))

        corpo = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        corpo.pack(fill=tk.BOTH, expand=True, padx=15)
        lista = ttk.Frame(corpo)
        corpo.add(lista, weight=1)
        self.tree = ttk.Treeview(lista, columns=("versao", "data", "tamanho"), show="headings", selectmode="browse")
        for coluna, largura in (("versao", 70), ("data", 140), ("tamanho", 80)):
            self.tree.heading(coluna, text=t(f"historico.col_{coluna}"))
            self.tree.column(coluna, width=largura, anchor="w")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._selecionado)
        self.tree.bind("<Double-1>", lambda e: self._restaurar())

        self.preview = texto_rolavel(corpo, fonte=("Consolas", 9))
        corpo.add(self.preview, weight=3)

        botoes = tk.Frame(self, bg=tema.FUNDO)
        botoes.pack(fill=tk.X, padx=15, pady=10)
        self.btn_restaurar = ttk.Button(botoes, text=t("historico.btn_restaurar"), command=self._restaurar,
                                        state=tk.DISABLED)
        self.btn_restaurar.pack(side=tk.LEFT)
        ttk.Button(botoes, text=t("comum.fechar"), command=self.destroy).pack(side=tk.RIGHT)
        self._carregar()

    def _carregar(self):
        self.versoes = acoes.versoes_do_arquivo(self.caminho)
        self.tree.delete(*self.tree.get_children())
        for i, versao in enumerate(self.versoes):
            self.tree.insert("", "end", iid=str(i), values=(
                f"v{versao.numero:02d}", versao.data.strftime(t("historico.formato_data")), (t("historico.tamanho", kb=f"{versao.tamanho / 1024:.1f}") if versao.tamanho >= 1024 else t("historico.tamanho_bytes", bytes=versao.tamanho))))
        if self.versoes:
            self.tree.selection_set("0")
        else:
            substituir_texto(self.preview, t("historico.vazio"))
            self.btn_restaurar.config(state=tk.DISABLED)

    def _versao_selecionada(self):
        selecao = self.tree.selection()
        return self.versoes[int(selecao[0])] if selecao and int(selecao[0]) < len(self.versoes) else None

    def _selecionado(self, _evento=None):
        versao = self._versao_selecionada()
        if not versao:
            return
        try:
            substituir_texto(self.preview, acoes.ler_versao(versao))
        except OSError as e:
            substituir_texto(self.preview, str(e))
        self.btn_restaurar.config(state=tk.NORMAL)

    def _restaurar(self):
        versao = self._versao_selecionada()
        if not versao or not messagebox.askyesno(
                t("historico.confirmar_titulo"), t("historico.confirmar", numero=f"{versao.numero:02d}",
                                                   nome=arq.nome(self.caminho)), parent=self):
            return
        try:
            acoes.restaurar_versao(self.caminho, versao)
        except Exception as e:
            messagebox.showerror(t("comum.erro"), str(e), parent=self)
            return
        self.toast(t("historico.toast_restaurado", numero=f"{versao.numero:02d}", nome=arq.nome(self.caminho)))
        self.ao_restaurar(self.caminho)
        self._carregar()
