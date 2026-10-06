"""
Página do WorldBuilder (nível alto): 1 Ideia e Cânone → 2 Plano (checklist editável) → 3 Execução.
Só interface: o estado vem da sessão do WorldBuilder (engine.wbuilder via engine.acoes).
"""
import tkinter as tk
from tkinter import ttk, messagebox

import core.config as cfg
import core.eventos as ev
import core.tarefas as tarefas
import engine.acoes as acoes
import ui.theme as tema
from core.i18n import t
from ui.widgets import PaginaBase, cabecalho, texto_rolavel, anexar_texto, substituir_texto

PERMISSOES = [("wb_allow_create_folder", "wb.perm_folder"),
              ("wb_allow_create_file", "wb.perm_file"),
              ("wb_allow_improve_file", "wb.perm_improve"),
              ("wb_allow_generators", "wb.perm_generators")]
COLUNAS = ("ativo", "fase", "tipo", "caminho", "segredo", "status")


class PaginaWorldBuilder(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("wb.title"), t("wb.subtitle"))
        self._sessao = {}
        self._selecionado = None
        opcoes = acoes.wb_opcoes()

        topo = ttk.Frame(self)
        topo.pack(fill=tk.X, padx=15)
        topo.columnconfigure(0, weight=3)
        topo.columnconfigure(1, weight=2)

        # --- 1. Ideia e Cânone ---
        caixa_ideia = ttk.LabelFrame(topo, text=t("wb.passo1_titulo"))
        caixa_ideia.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        ttk.Label(caixa_ideia, text=t("wb.passo1_texto"), foreground=tema.SUAVE, wraplength=640,
                  justify="left").pack(anchor=tk.W, padx=10, pady=(8, 4))
        self.txt_objetivo = tk.Text(caixa_ideia, height=3, wrap=tk.WORD, font=("Segoe UI", 10), bg=tema.PAINEL,
                                    fg=tema.TEXTO, insertbackground="white", bd=0, highlightthickness=0)
        self.txt_objetivo.pack(fill=tk.X, padx=10, pady=(0, 6))
        linha = ttk.Frame(caixa_ideia)
        linha.pack(fill=tk.X, padx=10, pady=(0, 4))
        self.btn_canon = ttk.Button(linha, text=t("wb.btn_canon"), command=self._gerar_canon)
        self.btn_canon.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_abrir_canon = ttk.Button(linha, text=t("wb.btn_abrir_canon"), command=self._abrir_canon)
        self.btn_abrir_canon.pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(linha, text=t("wb.btn_nova_sessao"), command=self._nova_sessao).pack(side=tk.RIGHT)
        self.lbl_canon = ttk.Label(caixa_ideia, text="", wraplength=640, justify="left")
        self.lbl_canon.pack(anchor=tk.W, padx=10, pady=(0, 8))

        # --- Permissões e limite ---
        caixa_perm = ttk.LabelFrame(topo, text=t("wb.permissions_title"))
        caixa_perm.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        self._vars_perm = {}
        for chave, rotulo in PERMISSOES:
            var = tk.BooleanVar(value=bool(cfg.obter(chave, True)))
            self._vars_perm[chave] = var
            ttk.Checkbutton(caixa_perm, text=t(rotulo), variable=var,
                            command=lambda c=chave, r=rotulo: self._salvar_permissao(c, r)).pack(anchor=tk.W, padx=10, pady=2)
        linha_max = ttk.Frame(caixa_perm)
        linha_max.pack(anchor=tk.W, padx=10, pady=(6, 8))
        ttk.Label(linha_max, text=t("wb.max_acoes")).pack(side=tk.LEFT)
        self.var_max = tk.StringVar(value=str(opcoes["max_acoes"]))
        caixa_max = ttk.Spinbox(linha_max, from_=1, to=200, width=5, textvariable=self.var_max,
                                command=self._salvar_max)
        caixa_max.pack(side=tk.LEFT, padx=6)
        caixa_max.bind("<FocusOut>", lambda e: self._salvar_max())

        # --- 2. Plano (esquerda) e log ao vivo (direita) ---
        corpo = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        corpo.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 6))

        caixa_plano = ttk.LabelFrame(corpo, text=t("wb.passo2_titulo"))
        corpo.add(caixa_plano, weight=3)
        botoes = ttk.Frame(caixa_plano)
        botoes.pack(fill=tk.X, padx=6, pady=(6, 2))
        self.btn_plano = ttk.Button(botoes, text=t("wb.btn_plano"), command=self._gerar_plano)
        self.btn_plano.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_executar = ttk.Button(botoes, text=t("wb.btn_executar"), command=self._executar)
        self.btn_executar.pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(botoes, text=t("wb.btn_stop"), command=self._parar).pack(side=tk.LEFT)
        self.lbl_status = ttk.Label(botoes, text=t("wb.status_idle"))
        self.lbl_status.pack(side=tk.RIGHT)

        self.tree = ttk.Treeview(caixa_plano, columns=COLUNAS, show="headings", selectmode="browse", height=10)
        for coluna, largura in zip(COLUNAS, (34, 140, 140, 220, 34, 100)):
            self.tree.heading(coluna, text=t(f"wb.col_{coluna}"))
            self.tree.column(coluna, width=largura, anchor="center" if coluna in ("ativo", "segredo") else "w",
                             stretch=coluna == "caminho")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        self.tree.bind("<<TreeviewSelect>>", self._item_selecionado)
        self.tree.bind("<Button-1>", self._clique_tree, add="+")
        for estado, cor in (("executando", tema.AZUL), ("concluida", tema.VERDE), ("falhou", tema.VERMELHO),
                            ("inativo", tema.SUAVE)):
            self.tree.tag_configure(estado, foreground=cor)

        # Edição do item selecionado
        editor = ttk.Frame(caixa_plano)
        editor.pack(fill=tk.X, padx=6, pady=(0, 6))
        editor.columnconfigure(1, weight=1)
        ttk.Label(editor, text=t("wb.campo_caminho")).grid(row=0, column=0, sticky="w")
        self.var_caminho = tk.StringVar()
        ttk.Entry(editor, textvariable=self.var_caminho).grid(row=0, column=1, columnspan=3, sticky="ew", pady=2)
        ttk.Label(editor, text=t("wb.campo_objetivo")).grid(row=1, column=0, sticky="nw")
        self.txt_item = tk.Text(editor, height=3, wrap=tk.WORD, font=("Segoe UI", 9), bg=tema.PAINEL, fg=tema.TEXTO,
                                insertbackground="white", bd=0, highlightthickness=0)
        self.txt_item.grid(row=1, column=1, columnspan=3, sticky="ew", pady=2)
        ttk.Label(editor, text=t("wb.campo_template")).grid(row=2, column=0, sticky="w")
        self._templates = opcoes["templates"]
        self.combo_template = ttk.Combobox(editor, state="readonly", width=14,
                                           values=[t(f"wb.template.{n}") for n in self._templates])
        self.combo_template.grid(row=2, column=1, sticky="w", pady=2)
        self.var_segredo = tk.BooleanVar()
        ttk.Checkbutton(editor, text=t("wb.campo_segredo"), variable=self.var_segredo).grid(row=2, column=2, sticky="w")
        self.btn_salvar_item = ttk.Button(editor, text=t("wb.btn_salvar_item"), command=self._salvar_item)
        self.btn_salvar_item.grid(row=2, column=3, sticky="e")
        ttk.Label(editor, text=t("wb.campo_genero")).grid(row=3, column=0, sticky="w")
        self._generos = opcoes["generos"]
        self.combo_genero = ttk.Combobox(editor, state="readonly", width=24, values=[nome for _, nome in self._generos])
        self.combo_genero.grid(row=3, column=1, columnspan=2, sticky="w", pady=2)
        self.lbl_aviso = ttk.Label(editor, text=t("wb.plan_empty"), foreground=tema.SUAVE, wraplength=640, justify="left")
        self.lbl_aviso.grid(row=4, column=0, columnspan=4, sticky="w", pady=(4, 0))

        caixa_log = ttk.LabelFrame(corpo, text=t("wb.log_title"))
        corpo.add(caixa_log, weight=2)
        self.log = texto_rolavel(caixa_log, fonte=("Consolas", 9), width=48)
        self.log.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # --- 3. Resultado ---
        self.lbl_resumo = ttk.Label(self, text="", foreground=tema.SUAVE, wraplength=1100, justify="left")
        self.lbl_resumo.pack(fill=tk.X, padx=18, pady=(0, 10))

        ev.inscrever_evento("wb.sessao", lambda s: tarefas.na_interface(self._exibir_sessao, s))
        ev.inscrever_evento("wb.acao", lambda dados: tarefas.na_interface(self._atualizar_acao, dados))
        ev.inscrever_evento("acao.estado", lambda d: tarefas.na_interface(self._estado_acao, d))
        ev.inscrever_log(lambda msg: tarefas.na_interface(self._log_ao_vivo, msg))
        self._exibir_sessao(acoes.wb_sessao())

    # ------------------------------------------------------------------
    # SESSÃO
    # ------------------------------------------------------------------
    def projeto_alterado(self):
        self._exibir_sessao(acoes.wb_sessao())

    def receber_ideia(self, texto):
        """Preenche a ideia (ex.: uma conversa com Silent levada ao WorldBuilder)."""
        self.txt_objetivo.delete("1.0", tk.END)
        self.txt_objetivo.insert("1.0", texto)

    def _exibir_sessao(self, sessao):
        self._sessao = sessao or {}
        objetivo = self._sessao.get("objetivo") or ""
        if self.txt_objetivo.get("1.0", "end").strip() != objetivo and (objetivo or not self._rodando()):
            self.txt_objetivo.delete("1.0", tk.END)
            self.txt_objetivo.insert("1.0", objetivo)
        canon = self._sessao.get("canon")
        if self._da_auditoria():
            self.lbl_canon.config(text=t("wb.origem_auditoria", data=self._sessao.get("auditoria_data") or ""),
                                  foreground=tema.AZUL_CLARO)
            self.btn_abrir_canon.config(text=t("wb.btn_ver_relatorio"))
        elif canon:
            self.lbl_canon.config(text=t("wb.canon_pronto", caminho=canon), foreground=tema.VERDE)
            self.btn_abrir_canon.config(text=t("wb.btn_abrir_canon"))
        else:
            self.lbl_canon.config(text=t("wb.canon_ausente"), foreground=tema.SUAVE)
            self.btn_abrir_canon.config(text=t("wb.btn_abrir_canon"))
        self._exibir_plano(self._sessao.get("plano") or [])
        self._exibir_resumo(self._sessao.get("resumo"))
        self._atualizar_botoes()

    def _exibir_plano(self, plano):
        self.tree.delete(*self.tree.get_children())
        for i, item in enumerate(plano):
            self.tree.insert("", "end", iid=str(i), values=self._valores(item), tags=self._tags(item))
        self._selecionado = None
        if plano:
            ativos = sum(1 for item in plano if item.get("ativo"))
            self.lbl_aviso.config(text=t("wb.plan_count", total=len(plano), ativos=ativos), foreground=tema.SUAVE)
        else:
            self.lbl_aviso.config(text=t("wb.plan_empty"), foreground=tema.SUAVE)

    @staticmethod
    def _valores(item):
        return ("☑" if item.get("ativo") else "☐", t(f"wb.fase.{item.get('fase', 3)}"), t(f"wb.tipo.{item.get('type')}"),
                item.get("path", ""), "🤫" if item.get("segredo") else "", t(f"wb.estado.{item.get('estado', 'pendente')}"))

    @staticmethod
    def _tags(item):
        if item.get("estado") in ("executando", "concluida", "falhou"):
            return (item["estado"],)
        return () if item.get("ativo") else ("inativo",)

    def _exibir_resumo(self, resumo):
        if not resumo:
            self.lbl_resumo.config(text="")
            return
        texto = t("wb.resumo", concluidas=resumo.get("concluidas", 0), falhas=resumo.get("falhas", 0))
        links = resumo.get("links_sem_arquivo") or []
        if links:
            texto += "\n" + t("wb.resumo_links", total=len(links), nomes=", ".join(links[:15]))
        if resumo.get("interrompido"):
            texto += "\n" + t("wb.resumo_interrompido")
        self.lbl_resumo.config(text=texto, foreground=tema.TEXTO)

    def _rodando(self):
        return acoes.em_execucao("worldbuilder")

    def _atualizar_botoes(self):
        rodando = self._rodando()
        tem_canon = bool(self._sessao.get("canon")) or self._da_auditoria()
        tem_plano = any(item.get("ativo") and item.get("estado") != "concluida" for item in self._sessao.get("plano") or [])
        self.btn_canon.config(state=tk.DISABLED if rodando else tk.NORMAL)
        self.btn_abrir_canon.config(state=tk.NORMAL if tem_canon else tk.DISABLED)
        self.btn_plano.config(state=tk.NORMAL if tem_canon and not rodando else tk.DISABLED)
        self.btn_executar.config(state=tk.NORMAL if tem_plano and not rodando else tk.DISABLED)
        self.btn_salvar_item.config(state=tk.DISABLED if rodando else tk.NORMAL)

    def _estado_acao(self, dados):
        if dados.get("acao") == "worldbuilder":
            self._atualizar_botoes()

    # ------------------------------------------------------------------
    # BOTÕES
    # ------------------------------------------------------------------
    def _iniciar(self, iniciou):
        if not iniciou:
            self.app.toast(t("wb.ja_rodando"))
            return
        substituir_texto(self.log, "")
        self.lbl_status.config(text=t("wb.status_running"), foreground=tema.AZUL)
        self._atualizar_botoes()

    def _gerar_canon(self):
        if self._sessao.get("canon") and not messagebox.askyesno(t("wb.refazer_canon_titulo"), t("wb.refazer_canon")):
            return
        self.app.salvar_editor()
        objetivo = self.txt_objetivo.get("1.0", "end").strip()
        self._iniciar(acoes.wb_gerar_canon(objetivo, ao_concluir=self._canon_pronto, ao_falhar=self._falhou))

    def _canon_pronto(self, caminho):
        self._concluido(None)
        self.app.toast(t("wb.toast_canon"))
        self.app.pagina("editor").atualizar_arvore()
        self._abrir_canon()

    def _da_auditoria(self):
        return self._sessao.get("origem") == "auditoria" and bool(self._sessao.get("auditoria"))

    def corrigir_auditoria(self, relatorio):
        """Chamado pela Auditoria de Lore: monta o plano de correção (o Mestre revisa antes de executar)."""
        if self._rodando():
            self.app.toast(t("wb.ja_rodando"))
            return
        if acoes.wb_tem_plano_pendente() and not messagebox.askyesno(t("wb.auditoria_substituir_titulo"),
                                                                     t("wb.auditoria_substituir")):
            return
        self.app.mostrar_pagina("worldbuilder")
        self._iniciar(acoes.wb_gerar_plano_auditoria(
            relatorio, ao_concluir=lambda _: (self._concluido(None), self.app.toast(t("wb.toast_plano_auditoria"))),
            ao_falhar=self._falhou))

    def _abrir_canon(self):
        if self._da_auditoria():
            from ui.dialogs.audit_report import JanelaAuditoria
            JanelaAuditoria(self.app.root, self._sessao.get("auditoria"), toast=self.app.toast,
                            ao_corrigir=self.corrigir_auditoria)
            return
        caminho = acoes.wb_caminho_canon()
        if not caminho:
            self.app.toast(t("wb.canon_ausente"))
            return
        self.app.mostrar_pagina("editor")
        self.app.pagina("editor").abrir_arquivo(caminho)

    def _gerar_plano(self):
        self.app.salvar_editor()          # o plano lê o cânone do disco, com as edições do Mestre
        self._iniciar(acoes.wb_gerar_plano(ao_concluir=lambda _: (self._concluido(None), self.app.toast(t("wb.toast_plano"))),
                                           ao_falhar=self._falhou))

    def _executar(self):
        ativos = sum(1 for item in self._sessao.get("plano") or [] if item.get("ativo") and item.get("estado") != "concluida")
        if not messagebox.askyesno(t("wb.confirmar_titulo"), t("wb.confirmar", total=ativos)):
            return
        self.app.salvar_editor()
        self._iniciar(acoes.wb_executar(ao_concluir=self._execucao_concluida, ao_falhar=self._falhou))

    def _execucao_concluida(self, _resumo):
        self._concluido(None)
        self.app.toast(t("wb.toast_done"))
        self.app.pagina("editor").atualizar_arvore()

    def _nova_sessao(self):
        if self._rodando():
            self.app.toast(t("wb.ja_rodando"))
            return
        if messagebox.askyesno(t("wb.nova_sessao_titulo"), t("wb.nova_sessao")):
            self._exibir_sessao(acoes.wb_nova_sessao())
            substituir_texto(self.log, "")

    def _parar(self):
        acoes.parar("worldbuilder")
        self.app.toast(t("actions.toast_stopping"))

    def _concluido(self, _resultado):
        self.lbl_status.config(text=t("wb.status_done"), foreground=tema.TEXTO)
        self._exibir_sessao(acoes.wb_sessao())

    def _falhou(self, erro):
        self.lbl_status.config(text=t("wb.status_failed"), foreground=tema.VERMELHO)
        self.app.toast(t("wb.toast_failed"))
        anexar_texto(self.log, t("wb.erro", erro=erro) + "\n")
        self._exibir_sessao(acoes.wb_sessao())

    def _salvar_permissao(self, chave, rotulo):
        habilitado = bool(self._vars_perm[chave].get())
        cfg.atualizar_configuracoes({chave: habilitado})
        estado = t("comum.habilitado") if habilitado else t("comum.desabilitado")
        self.app.toast(t("wb.toast_permissao", permissao=t(rotulo), estado=estado))

    def _salvar_max(self):
        self.var_max.set(str(acoes.wb_definir_max_acoes(self.var_max.get())))

    # ------------------------------------------------------------------
    # PLANO: SELEÇÃO, MARCAR/DESMARCAR E EDIÇÃO
    # ------------------------------------------------------------------
    def _clique_tree(self, evento):
        if self.tree.identify_column(evento.x) != "#1" or self._rodando():
            return
        iid = self.tree.identify_row(evento.y)
        if iid:
            item = (self._sessao.get("plano") or [])[int(iid)]
            if item.get("estado") != "concluida":
                self._atualizar_item(int(iid), ativo=not item.get("ativo"))

    def _item_selecionado(self, _evento=None):
        selecao = self.tree.selection()
        plano = self._sessao.get("plano") or []
        if not selecao or int(selecao[0]) >= len(plano):
            return
        self._selecionado = int(selecao[0])
        item = plano[self._selecionado]
        self.var_caminho.set(item.get("path", ""))
        self.txt_item.delete("1.0", tk.END)
        self.txt_item.insert("1.0", item.get("objective", ""))
        template = item.get("template", "nenhum")
        self.combo_template.current(self._templates.index(template) if template in self._templates else len(self._templates) - 1)
        self.var_segredo.set(bool(item.get("segredo")))
        ids = [ident for ident, _ in self._generos]
        self.combo_genero.current(ids.index(item.get("genero", "")) if item.get("genero", "") in ids else 0)
        self.lbl_aviso.config(text=item.get("aviso") or t("wb.item_ok"),
                              foreground=tema.AMARELO if item.get("aviso") else tema.SUAVE)

    def _salvar_item(self):
        if self._selecionado is None:
            self.app.toast(t("wb.selecione_item"))
            return
        indice = self.combo_template.current()
        self._atualizar_item(self._selecionado, path=self.var_caminho.get().strip(),
                             objective=self.txt_item.get("1.0", "end").strip(),
                             template=self._templates[indice] if indice >= 0 else None,
                             segredo=bool(self.var_segredo.get()),
                             genero=self._generos[max(self.combo_genero.current(), 0)][0])
        self.app.toast(t("wb.toast_item"))

    def _atualizar_item(self, indice, **campos):
        try:
            item = acoes.wb_atualizar_item(indice, **campos)
        except Exception as e:
            self.app.toast(str(e))
            return
        self._sessao = acoes.wb_sessao()
        iid = str(indice)
        if self.tree.exists(iid):
            self.tree.item(iid, values=self._valores(item), tags=self._tags(item))
        if self._selecionado == indice:
            self.lbl_aviso.config(text=item.get("aviso") or t("wb.item_ok"),
                                  foreground=tema.AMARELO if item.get("aviso") else tema.SUAVE)
        self._atualizar_botoes()

    # ------------------------------------------------------------------
    # EXECUÇÃO AO VIVO
    # ------------------------------------------------------------------
    def _atualizar_acao(self, dados):
        iid = str(dados["indice"])
        plano = self._sessao.get("plano") or []
        if not self.tree.exists(iid) or int(iid) >= len(plano):
            return
        plano[int(iid)]["estado"] = dados["estado"]
        self.tree.item(iid, values=self._valores(plano[int(iid)]), tags=self._tags(plano[int(iid)]))
        self.tree.see(iid)

    def _log_ao_vivo(self, mensagem):
        if self._rodando():
            anexar_texto(self.log, str(mensagem).strip() + "\n")
