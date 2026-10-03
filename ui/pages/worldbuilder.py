"""Página do WorldBuilder: objetivo, permissões, plano de ações e log ao vivo."""
import tkinter as tk
from tkinter import ttk

import core.config as cfg
import core.eventos as ev
import core.tarefas as tarefas
import engine.acoes as acoes
import ui.theme as tema
from core.i18n import t
from ui.widgets import PaginaBase, cabecalho, texto_rolavel, anexar_texto, substituir_texto

PERMISSOES = [("wb_allow_create_folder", "wb.perm_folder"),
              ("wb_allow_create_file", "wb.perm_file"),
              ("wb_allow_improve_file", "wb.perm_improve")]


class PaginaWorldBuilder(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("wb.title"), t("wb.subtitle"))
        self._plano = []

        topo = ttk.Frame(self)
        topo.pack(fill=tk.X, padx=15)
        topo.columnconfigure(0, weight=3)
        topo.columnconfigure(1, weight=2)

        # --- Objetivo + executar/parar ---
        caixa_obj = ttk.LabelFrame(topo, text=t("wb.goal_box"))
        caixa_obj.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        ttk.Label(caixa_obj, text=t("wb.goal_label")).pack(anchor=tk.W, padx=10, pady=(10, 2))
        self.objetivo = tk.StringVar(value=acoes.objetivo_padrao_worldbuilder())
        ttk.Entry(caixa_obj, textvariable=self.objetivo).pack(fill=tk.X, padx=10, pady=(0, 8))
        botoes = ttk.Frame(caixa_obj)
        botoes.pack(fill=tk.X, padx=10, pady=(0, 6))
        self.btn_executar = ttk.Button(botoes, text=t("wb.btn_run"), command=self._executar)
        self.btn_executar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Button(botoes, text=t("wb.btn_stop"), command=self._parar).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.lbl_status = ttk.Label(caixa_obj, text=t("wb.status_idle"))
        self.lbl_status.pack(anchor=tk.W, padx=10, pady=(0, 10))

        # --- Permissões do agente ---
        caixa_perm = ttk.LabelFrame(topo, text=t("wb.permissions_title"))
        caixa_perm.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        self._vars_perm = {}
        for chave, rotulo in PERMISSOES:
            linha = ttk.Frame(caixa_perm)
            linha.pack(fill=tk.X, padx=10, pady=4)
            ttk.Label(linha, text=t(rotulo), width=30, anchor="w").pack(side=tk.LEFT)
            var = tk.BooleanVar(value=bool(cfg.obter(chave, True)))
            self._vars_perm[chave] = var
            for valor, texto in ((False, t("comum.desabilitado")), (True, t("comum.habilitado"))):
                ttk.Radiobutton(linha, text=texto, value=valor, variable=var,
                                command=lambda c=chave, r=rotulo: self._salvar_permissao(c, r)).pack(side=tk.LEFT, padx=(0, 12))

        # --- Plano (esquerda) e log ao vivo (direita) ---
        corpo = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        corpo.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        caixa_plano = ttk.LabelFrame(corpo, text=t("wb.plan_title"))
        corpo.add(caixa_plano, weight=3)
        colunas = ("prioridade", "tipo", "caminho", "status")
        self.tree = ttk.Treeview(caixa_plano, columns=colunas, show="headings", selectmode="browse")
        for coluna, largura in zip(colunas, (70, 110, 300, 110)):
            self.tree.heading(coluna, text=t(f"wb.col_{coluna}"))
            self.tree.column(coluna, width=largura, anchor="w")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tree.bind("<<TreeviewSelect>>", self._mostrar_objetivo)
        self.lbl_objetivo = ttk.Label(caixa_plano, text=t("wb.plan_empty"), wraplength=520, foreground=tema.SUAVE)
        self.lbl_objetivo.pack(fill=tk.X, padx=8, pady=(0, 8))
        for estado, cor in (("executando", tema.AZUL), ("concluida", tema.VERDE), ("falhou", tema.VERMELHO)):
            self.tree.tag_configure(estado, foreground=cor)

        caixa_log = ttk.LabelFrame(corpo, text=t("wb.log_title"))
        corpo.add(caixa_log, weight=2)
        self.log = texto_rolavel(caixa_log, fonte=("Consolas", 9))
        self.log.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        ev.inscrever_evento("wb.plano", lambda acoes_plano: tarefas.na_interface(self._exibir_plano, acoes_plano))
        ev.inscrever_evento("wb.acao", lambda dados: tarefas.na_interface(self._atualizar_acao, dados))
        ev.inscrever_log(lambda msg: tarefas.na_interface(self._log_ao_vivo, msg))

    # --- permissões ---
    def _salvar_permissao(self, chave, rotulo):
        habilitado = bool(self._vars_perm[chave].get())
        cfg.atualizar_configuracoes({chave: habilitado})
        estado = t("comum.habilitado") if habilitado else t("comum.desabilitado")
        self.app.toast(t("wb.toast_permissao", permissao=t(rotulo), estado=estado))

    # --- execução ---
    def _executar(self):
        self.app.salvar_editor()
        self.tree.delete(*self.tree.get_children())
        self._plano = []
        self.lbl_objetivo.config(text=t("wb.plan_waiting"))
        substituir_texto(self.log, "")
        iniciou = acoes.executar_worldbuilder(self.objetivo.get(), ao_concluir=self._concluido, ao_falhar=self._falhou)
        if not iniciou:
            self.app.toast(t("wb.ja_rodando"))
            return
        self.btn_executar.config(state=tk.DISABLED)
        self.lbl_status.config(text=t("wb.status_running"), foreground=tema.AZUL)
        self.app.toast(t("wb.toast_start"))

    def _parar(self):
        acoes.parar_tudo()
        self.app.toast(t("actions.toast_stopping"))

    def _concluido(self, _resultado):
        self.btn_executar.config(state=tk.NORMAL)
        self.lbl_status.config(text=t("wb.status_done"), foreground=tema.TEXTO)
        self.app.toast(t("wb.toast_done"))
        self.app.pagina("editor").atualizar_arvore()

    def _falhou(self, erro):
        self.btn_executar.config(state=tk.NORMAL)
        self.lbl_status.config(text=t("wb.status_failed"), foreground=tema.VERMELHO)
        self.app.toast(t("wb.toast_failed"))

    # --- plano e log ---
    def _exibir_plano(self, acoes_plano):
        self._plano = list(acoes_plano or [])
        self.tree.delete(*self.tree.get_children())
        for i, acao in enumerate(self._plano):
            self.tree.insert("", "end", iid=str(i), values=(
                acao.get("priority", ""), acao.get("type", ""), acao.get("path", ""), t("wb.estado.pendente")))
        self.lbl_objetivo.config(text=t("wb.plan_count", total=len(self._plano)) if self._plano else t("wb.plan_none"))

    def _atualizar_acao(self, dados):
        iid = str(dados["indice"])
        if not self.tree.exists(iid):
            return
        valores = list(self.tree.item(iid, "values"))
        valores[3] = t(f"wb.estado.{dados['estado']}")
        self.tree.item(iid, values=valores, tags=(dados["estado"],))
        self.tree.see(iid)

    def _mostrar_objetivo(self, _evento=None):
        selecao = self.tree.selection()
        if selecao and int(selecao[0]) < len(self._plano):
            acao = self._plano[int(selecao[0])]
            self.lbl_objetivo.config(text=t("wb.objective_of", objetivo=acao.get("objective", ""),
                                            template=acao.get("template", "")), foreground=tema.TEXTO)

    def _log_ao_vivo(self, mensagem):
        if acoes.em_execucao("worldbuilder"):
            anexar_texto(self.log, str(mensagem).strip() + "\n")
