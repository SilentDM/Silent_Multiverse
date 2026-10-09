"""
Página Sessões: um editor livre para o Mestre anotar durante a mesa (salva sozinho) e o botão
"Finalizar sessão", que pede a Silent o diário da sessão. Só interface: a lógica está em engine.sessoes.
"""
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox

import engine.acoes as acoes
import ui.theme as tema
from core.i18n import t
from ui.widgets import PaginaBase, cabecalho, ajuda, caixa_com_ajuda

SALVAR_MS = 1000


class PaginaSessoes(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("sess.titulo"), t("sess.subtitulo"))
        self._timer = None
        self._diarios = []

        topo = ttk.Frame(self)
        topo.pack(fill=tk.X, padx=15, pady=(0, 6))
        ttk.Label(topo, text=t("sess.numero")).pack(side=tk.LEFT)
        self.var_numero = tk.StringVar(value=str(acoes.sessao_proximo_numero()))
        ttk.Spinbox(topo, from_=1, to=9999, width=6, textvariable=self.var_numero).pack(side=tk.LEFT, padx=(4, 2))
        ajuda(topo, t("ajuda.sess.numero")).pack(side=tk.LEFT, padx=(2, 10))
        ttk.Button(topo, text=t("sess.btn_hora"), style="Ferramenta.TButton", command=self._inserir_hora).pack(side=tk.LEFT)
        self.lbl_estado = ttk.Label(topo, text="", style="Dica.TLabel")
        self.lbl_estado.pack(side=tk.LEFT, padx=10)
        self.btn_finalizar = ttk.Button(topo, text=t("sess.btn_finalizar"), style="Primario.TButton", command=self._finalizar)
        self.btn_finalizar.pack(side=tk.RIGHT)
        ajuda(topo, t("ajuda.sess.finalizar")).pack(side=tk.RIGHT, padx=(0, 6))

        corpo = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        corpo.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        caixa_notas = caixa_com_ajuda(corpo, t("sess.notas"), t("ajuda.sess.notas"))
        corpo.add(caixa_notas, weight=4)
        self.texto = tk.Text(caixa_notas, wrap=tk.WORD, font=("Segoe UI", 11), undo=True, bg=tema.PAINEL, fg=tema.TEXTO,
                             insertbackground="white", bd=0, padx=10, pady=8, highlightthickness=0,
                             selectbackground=tema.VERDE_ESCURO)
        barra = ttk.Scrollbar(caixa_notas, orient="vertical", command=self.texto.yview)
        self.texto.configure(yscrollcommand=barra.set)
        barra.pack(side=tk.RIGHT, fill=tk.Y, pady=6)
        self.texto.pack(fill=tk.BOTH, expand=True, padx=(6, 0), pady=6)
        self.texto.bind("<KeyRelease>", self._editado)
        self.texto.bind("<FocusOut>", lambda e: self.salvar_agora())

        caixa_diarios = caixa_com_ajuda(corpo, t("sess.diarios"), t("ajuda.sess.diarios"))
        corpo.add(caixa_diarios, weight=1)
        self.lista = tk.Listbox(caixa_diarios, bg=tema.PAINEL, fg=tema.TEXTO, font=("Segoe UI", 10), borderwidth=0,
                                highlightthickness=0, activestyle="none", selectbackground=tema.VERDE_ESCURO, width=26)
        self.lista.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.lista.bind("<Double-1>", lambda e: self._abrir_diario())
        botoes = ttk.Frame(caixa_diarios)
        botoes.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(botoes, text=t("sess.btn_abrir"), command=self._abrir_diario).pack(fill=tk.X)
        ttk.Button(botoes, text=t("sess.btn_worldbuilder"), command=self._para_worldbuilder).pack(fill=tk.X, pady=(4, 0))

        self._carregar()

    # ------------------------------------------------------------------
    def _carregar(self):
        self.texto.config(state=tk.NORMAL)
        self.texto.delete("1.0", tk.END)
        self.texto.insert("1.0", acoes.sessao_notas())
        self.texto.edit_reset()
        self.var_numero.set(str(acoes.sessao_proximo_numero()))
        self._atualizar_lista()
        self.lbl_estado.config(text="")

    def _atualizar_lista(self):
        self._diarios = acoes.sessao_diarios()
        self.lista.delete(0, tk.END)
        for numero, caminho in self._diarios:
            self.lista.insert(tk.END, t("sess.item_diario", numero=numero))

    def projeto_alterado(self):
        self._carregar()

    def ajustar_fonte(self, tamanho):
        self.texto.configure(font=("Segoe UI", tamanho))

    def rolar(self, unidades):
        self.texto.yview_scroll(unidades, "units")

    # --- salvamento automático ---
    def _editado(self, _evento=None):
        if self._timer:
            self.after_cancel(self._timer)
        self.lbl_estado.config(text=t("sess.salvando"), foreground=tema.AMARELO)
        self._timer = self.after(SALVAR_MS, self.salvar_agora)

    def salvar_agora(self):
        if self._timer:
            self.after_cancel(self._timer)
            self._timer = None
        if str(self.texto.cget("state")) == "disabled":
            return
        acoes.sessao_salvar_notas(self.texto.get("1.0", "end-1c"))
        self.lbl_estado.config(text=t("sess.salvo"), foreground=tema.VERDE)

    def _inserir_hora(self):
        self.texto.insert(tk.INSERT, datetime.now().strftime("[%H:%M] "))
        self.texto.focus_set()
        self._editado()

    # --- finalizar ---
    def _finalizar(self):
        notas = self.texto.get("1.0", "end-1c").strip()
        if not notas:
            self.app.toast(t("sess.vazia"))
            return
        numero = int(self.var_numero.get()) if self.var_numero.get().isdigit() else acoes.sessao_proximo_numero()
        if not messagebox.askyesno(t("sess.confirmar_titulo"), t("sess.confirmar", numero=numero), parent=self):
            return
        self.salvar_agora()
        iniciou = acoes.finalizar_sessao(notas, numero, ao_concluir=self._pronto, ao_falhar=self._falhou)
        if not iniciou:
            self.app.toast(t("sess.ja_rodando"))
            return
        self.texto.config(state=tk.DISABLED)            # as anotações ficam congeladas enquanto Silent lê
        self.btn_finalizar.config(state=tk.DISABLED)
        self.lbl_estado.config(text=t("sess.analisando"), foreground=tema.AZUL)
        self.app.toast(t("sess.toast_inicio", numero=numero))

    def _pronto(self, caminho):
        self.texto.config(state=tk.NORMAL)
        self.btn_finalizar.config(state=tk.NORMAL)
        if not caminho:                                 # parada pelo Mestre
            self.lbl_estado.config(text="")
            return
        self._carregar()
        self.app.toast(t("sess.toast_pronto"))
        self.app.pagina("editor").abrir_arquivo(caminho)
        self.app.mostrar_pagina("editor")

    def _falhou(self, erro):
        self.texto.config(state=tk.NORMAL)
        self.btn_finalizar.config(state=tk.NORMAL)
        self.lbl_estado.config(text="")
        messagebox.showerror(t("sess.erro_titulo"), t("sess.erro", erro=erro), parent=self)

    # --- diários ---
    def _diario_selecionado(self):
        selecao = self.lista.curselection()
        if not selecao or selecao[0] >= len(self._diarios):
            self.app.toast(t("sess.selecione"))
            return None
        return self._diarios[selecao[0]][1]

    def _abrir_diario(self):
        caminho = self._diario_selecionado()
        if caminho:
            self.app.pagina("editor").abrir_arquivo(caminho)
            self.app.mostrar_pagina("editor")

    def _para_worldbuilder(self):
        caminho = self._diario_selecionado()
        if caminho:
            self.app.pagina("worldbuilder").corrigir_auditoria(acoes.sessao_para_worldbuilder(caminho))
