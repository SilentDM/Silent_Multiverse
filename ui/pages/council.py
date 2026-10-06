"""Página do Conselho: deliberação em 4 painéis e consolidação final do arquivo."""
import tkinter as tk
from pathlib import Path
from tkinter import ttk, scrolledtext

import core.tarefas as tarefas
import engine.council_engine as ce
import ui.theme as tema
from core.i18n import t
from ui.widgets import PaginaBase, cabecalho, ajuda, caixa_com_ajuda

PAINEIS = [("arquiteto", tema.TEXTO), ("cronista", tema.TEXTO), ("npcs", tema.AMARELO), ("tatico_caos", tema.AZUL_CLARO)]


class PaginaConselho(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("cons.titulo"), t("cons.subtitulo"))
        self.arquivo = None
        self.requisicao = None

        controle = caixa_com_ajuda(self, t("cons.controle"), t("ajuda.cons.controle"))
        controle.pack(fill=tk.X, padx=15, pady=(0, 10))
        linha1 = ttk.Frame(controle)
        linha1.pack(fill=tk.X, padx=10, pady=6)
        ttk.Label(linha1, text=t("cons.arquivo_alvo"), font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.lbl_arquivo = ttk.Label(linha1, text=t("cons.nenhum_arquivo"), font=("Segoe UI", 9, "bold"), foreground=tema.VERDE)
        self.lbl_arquivo.pack(side=tk.LEFT, padx=(0, 15))
        ttk.Label(linha1, text=t("cons.diretriz")).pack(side=tk.LEFT, padx=(0, 2))
        ajuda(linha1, t("ajuda.cons.diretriz")).pack(side=tk.LEFT, padx=(0, 6))
        self.diretriz = ttk.Entry(linha1, font=("Segoe UI", 10))
        self.diretriz.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        linha2 = ttk.Frame(controle)
        linha2.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.btn_fase1 = ttk.Button(linha2, text=t("cons.btn_fase1"), command=self._fase1)
        self.btn_fase1.pack(side=tk.LEFT, padx=(0, 10))
        self.btn_fase2 = ttk.Button(linha2, text=t("cons.btn_fase2"), command=self._fase2, state=tk.DISABLED)
        self.btn_fase2.pack(side=tk.LEFT)
        self.lbl_status = ttk.Label(linha2, text=t("cons.pronto"), font=("Segoe UI", 9, "italic"), foreground=tema.SUAVE)
        self.lbl_status.pack(side=tk.RIGHT)
        ajuda(linha2, t("ajuda.cons.fontes")).pack(side=tk.LEFT, padx=(10, 0))
        self.lbl_fontes = ttk.Label(controle, text="", font=("Segoe UI", 9), foreground=tema.AZUL_CLARO)
        self.lbl_fontes.pack(anchor=tk.W, padx=10, pady=(0, 6))

        grade = ttk.Frame(self)
        grade.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        for i in range(2):
            grade.columnconfigure(i, weight=1)
            grade.rowconfigure(i, weight=1)
        self.paineis = {}
        for i, (chave, cor) in enumerate(PAINEIS):
            caixa = ttk.LabelFrame(grade, text=t(f"cons.painel_{chave}"))
            caixa.grid(row=i // 2, column=i % 2, sticky="nsew", padx=4, pady=4)
            texto = scrolledtext.ScrolledText(caixa, wrap=tk.WORD, font=("Consolas", 9), bg=tema.CARTAO, fg=cor,
                                              insertbackground="white", bd=0)
            texto.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
            self.paineis[chave] = texto

    def _status(self, chave, cor=tema.TEXTO, **variaveis):
        self.lbl_status.config(text=t(chave, **variaveis), foreground=cor)

    def _preencher(self, valores: dict):
        for chave, texto in self.paineis.items():
            texto.delete("1.0", tk.END)
            texto.insert("1.0", valores.get(chave, ""))

    # --- chamado pelo Editor ---
    def carregar_arquivo(self, caminho, requisicao=None):
        self.arquivo = Path(caminho)
        self.requisicao = requisicao
        self.lbl_arquivo.config(text=self.arquivo.name)
        self.diretriz.delete(0, tk.END)
        self.diretriz.insert(0, (requisicao.objetivo if requisicao else "") or ce.diretriz_padrao(self.arquivo.name))
        self.lbl_fontes.config(text="")
        self._preencher({})
        self.btn_fase2.config(state=tk.DISABLED)
        self._status("cons.carregado")

    # --- fase 1 ---
    def _fase1(self):
        if not self.arquivo or not self.arquivo.is_file():
            self.app.toast(t("cons.selecione"))
            return
        diretriz = self.diretriz.get().strip() or ce.diretriz_vazia()
        self.btn_fase1.config(state=tk.DISABLED)
        self.btn_fase2.config(state=tk.DISABLED)
        self._status("cons.deliberando", tema.AZUL)
        self._preencher({chave: t("cons.consultando") for chave in self.paineis})
        self.app.toast(t("cons.toast_inicio"))

        def _ok(resultados):
            self._preencher({"arquiteto": resultados["arquiteto"], "cronista": resultados["cronista"],
                             "npcs": resultados["npcs"], "tatico_caos": resultados["tatico_caos"]})
            fontes = resultados.get("fontes")
            self.lbl_fontes.config(text=t("cons.fontes", fontes=fontes) if fontes else t("cons.sem_fontes"))
            self.btn_fase1.config(state=tk.NORMAL)
            self.btn_fase2.config(state=tk.NORMAL)
            self._status("cons.deliberado", tema.VERDE)
            self.app.toast(t("cons.toast_deliberado"))

        def _erro(e):
            self._status("cons.erro_fase1", tema.VERMELHO)
            self.btn_fase1.config(state=tk.NORMAL)

        tarefas.executar_em_segundo_plano(ce.executar_deliberacao_paineis, self.arquivo, diretriz,
                                          requisicao=self.requisicao, ao_concluir=_ok, ao_falhar=_erro)

    # --- fase 2 ---
    def _fase2(self):
        if not self.arquivo:
            return
        textos = {chave: texto.get("1.0", tk.END).strip() for chave, texto in self.paineis.items()}
        self.btn_fase1.config(state=tk.DISABLED)
        self.btn_fase2.config(state=tk.DISABLED)
        self._status("cons.consolidando", tema.AMARELO)
        self.app.toast(t("cons.toast_consolidando"))
        arquivo = self.arquivo

        def _ok(_sucesso):
            self._status("cons.consolidado", tema.VERDE)
            self.btn_fase1.config(state=tk.NORMAL)
            self.btn_fase2.config(state=tk.NORMAL)
            self.app.toast(t("cons.toast_consolidado", nome=arquivo.name))
            editor = self.app.pagina("editor")
            self.app.mostrar_pagina("editor")
            editor.atualizar_arvore()
            editor.recarregar_arquivo(str(arquivo))

        def _erro(e):
            self._status("cons.erro_fase2", tema.VERMELHO)
            self.btn_fase1.config(state=tk.NORMAL)
            self.btn_fase2.config(state=tk.NORMAL)

        tarefas.executar_em_segundo_plano(
            ce.sintetizar_e_salvar_arquivo_canonica, arquivo,
            texto_arquiteto=textos["arquiteto"], texto_cronista=textos["cronista"], texto_npcs=textos["npcs"],
            texto_tatico_caos=textos["tatico_caos"], diretriz_original=self.diretriz.get().strip(),
            requisicao=self.requisicao, ao_concluir=_ok, ao_falhar=_erro)
