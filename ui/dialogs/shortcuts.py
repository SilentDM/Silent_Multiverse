"""Janela para editar os atalhos de pedido do chat do Silent (nome + texto do pedido)."""
import tkinter as tk
from tkinter import ttk, messagebox

import core.atalhos_chat as atalhos
import ui.theme as tema
from core.i18n import t


class JanelaAtalhos(tk.Toplevel):
    def __init__(self, app, ao_salvar=None):
        super().__init__(app.root)
        self.app = app
        self.ao_salvar = ao_salvar or (lambda: None)
        self.lista_atalhos = atalhos.listar()
        self._indice = None
        self.title(t("atalhos.titulo"))
        self.configure(bg=tema.FUNDO)
        self.transient(app.root)
        self.geometry("820x480")
        self.minsize(640, 380)

        ttk.Label(self, text=t("atalhos.explicacao"), style="Dica.TLabel", wraplength=780,
                  justify="left").pack(anchor=tk.W, padx=14, pady=(12, 6))
        corpo = ttk.Frame(self)
        corpo.pack(fill=tk.BOTH, expand=True, padx=14)

        esquerda = ttk.Frame(corpo)
        esquerda.pack(side=tk.LEFT, fill=tk.Y)
        self.lista = tk.Listbox(esquerda, width=28, bg=tema.PAINEL, fg=tema.TEXTO, font=("Segoe UI", 10),
                                borderwidth=0, highlightthickness=0, activestyle="none",
                                selectbackground=tema.VERDE_ESCURO, exportselection=False)
        self.lista.pack(fill=tk.Y, expand=True)
        self.lista.bind("<<ListboxSelect>>", lambda e: self._selecionar())
        mover = ttk.Frame(esquerda)
        mover.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(mover, text="▲", width=3, command=lambda: self._mover(-1)).pack(side=tk.LEFT)
        ttk.Button(mover, text="▼", width=3, command=lambda: self._mover(1)).pack(side=tk.LEFT, padx=4)
        ttk.Button(mover, text=t("atalhos.novo"), command=self._novo).pack(side=tk.LEFT)
        ttk.Button(mover, text=t("atalhos.excluir"), style="Perigo.TButton", command=self._excluir).pack(side=tk.LEFT, padx=4)

        direita = ttk.Frame(corpo)
        direita.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(14, 0))
        ttk.Label(direita, text=t("atalhos.nome")).pack(anchor=tk.W)
        self.var_nome = tk.StringVar()
        ttk.Entry(direita, textvariable=self.var_nome).pack(fill=tk.X, pady=(2, 8))
        ttk.Label(direita, text=t("atalhos.texto")).pack(anchor=tk.W)
        self.txt = tk.Text(direita, height=8, wrap=tk.WORD, font=("Segoe UI", 10), bg=tema.PAINEL, fg=tema.TEXTO,
                           insertbackground="white", bd=0, padx=6, pady=4, highlightthickness=1,
                           highlightbackground="#3a3a3a", highlightcolor=tema.VERDE)
        self.txt.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        ttk.Label(direita, text=t("atalhos.dica_campo"), style="Dica.TLabel").pack(anchor=tk.W, pady=(4, 0))

        rodape = ttk.Frame(self)
        rodape.pack(fill=tk.X, padx=14, pady=12)
        ttk.Button(rodape, text=t("atalhos.restaurar"), command=self._restaurar).pack(side=tk.LEFT)
        ttk.Button(rodape, text=t("comum.fechar"), command=self.destroy).pack(side=tk.RIGHT)
        ttk.Button(rodape, text=t("atalhos.salvar"), style="Primario.TButton", command=self._salvar).pack(side=tk.RIGHT, padx=6)

        self._preencher_lista(0)

    def _preencher_lista(self, selecionar=None):
        self.lista.delete(0, tk.END)
        for atalho in self.lista_atalhos:
            self.lista.insert(tk.END, atalho["nome"])
        self._indice = None
        if selecionar is not None and self.lista_atalhos:
            selecionar = max(0, min(selecionar, len(self.lista_atalhos) - 1))
            self.lista.selection_set(selecionar)
            self._selecionar()
        elif not self.lista_atalhos:
            self.var_nome.set("")
            self.txt.delete("1.0", tk.END)

    def _guardar_edicao(self):
        """Leva o que está nos campos para o atalho selecionado."""
        if self._indice is None or self._indice >= len(self.lista_atalhos):
            return
        self.lista_atalhos[self._indice] = {"nome": self.var_nome.get().strip(),
                                            "texto": self.txt.get("1.0", "end-1c").strip()}
        self.lista.delete(self._indice)
        self.lista.insert(self._indice, self.lista_atalhos[self._indice]["nome"])

    def _selecionar(self):
        selecao = self.lista.curselection()
        if not selecao:
            return
        if self._indice is not None and self._indice != selecao[0]:
            self._guardar_edicao()
            self.lista.selection_set(selecao[0])
        self._indice = selecao[0]
        atalho = self.lista_atalhos[self._indice]
        self.var_nome.set(atalho["nome"])
        self.txt.delete("1.0", tk.END)
        self.txt.insert("1.0", atalho["texto"])

    def _mover(self, delta):
        self._guardar_edicao()
        i = self._indice
        if i is None or not 0 <= i + delta < len(self.lista_atalhos):
            return
        self.lista_atalhos[i], self.lista_atalhos[i + delta] = self.lista_atalhos[i + delta], self.lista_atalhos[i]
        self._preencher_lista(i + delta)

    def _novo(self):
        self._guardar_edicao()
        self.lista_atalhos.append({"nome": t("atalhos.novo_nome"), "texto": ""})
        self._preencher_lista(len(self.lista_atalhos) - 1)

    def _excluir(self):
        if self._indice is None:
            return
        del self.lista_atalhos[self._indice]
        self._preencher_lista(self._indice)

    def _restaurar(self):
        if messagebox.askyesno(t("atalhos.restaurar"), t("atalhos.restaurar_confirmar"), parent=self):
            self.lista_atalhos = atalhos.restaurar_padroes()
            self._preencher_lista(0)
            self.ao_salvar()

    def _salvar(self):
        self._guardar_edicao()
        self.lista_atalhos = atalhos.salvar(self.lista_atalhos)
        self.ao_salvar()
        self.app.toast(t("atalhos.toast_salvo", total=len(self.lista_atalhos)))
        self.destroy()
