"""
Página Requisições: o passo entre o pedido de nível médio e a IA.

Mostra o arquivo inteiro e as opções do pedido (estilo nos 4 eixos, diretrizes extras,
referências, modo, profundidade, público, dados de mesa, segredo, criatividade, presets).
Abre com os padrões do projeto; o que for trocado vale só para este pedido.
Só interface: a Requisição é montada e executada por engine.acoes.
"""
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox

import engine.acoes as acoes
import engine.arquivos as arq
import ui.theme as tema
from core.i18n import t
from ui.widgets import PaginaBase, cabecalho, texto_rolavel, substituir_texto, ajuda, rotulo_com_ajuda

EIXOS = ("genero", "tom", "clima", "escrita")
AJUDA_COMBOS = {"req.profundidade": "ajuda.req.profundidade", "req.publico": "ajuda.req.publico",
                "req.criatividade": "ajuda.req.criatividade", "req.modo": "ajuda.req.modo"}


class PaginaRequisicoes(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("req.titulo"), t("req.subtitulo"))
        self.req = None
        self._refs = []                      # [(caminho, motivo, marcado)]
        self._opcoes = acoes.opcoes_requisicao()

        topo = ttk.Frame(self)
        topo.pack(fill=tk.X, padx=15, pady=(0, 6))
        self.lbl_alvo = ttk.Label(topo, text=t("req.vazio"), font=("Segoe UI", 11, "bold"), foreground=tema.VERDE)
        self.lbl_alvo.pack(side=tk.LEFT)
        ttk.Button(topo, text=t("req.preset_excluir"), command=self._excluir_preset).pack(side=tk.RIGHT)
        ttk.Button(topo, text=t("req.preset_salvar"), command=self._salvar_preset).pack(side=tk.RIGHT, padx=4)
        self.combo_preset = ttk.Combobox(topo, state="readonly", width=24)
        self.combo_preset.pack(side=tk.RIGHT)
        self.combo_preset.bind("<<ComboboxSelected>>", lambda e: self._aplicar_preset())
        ajuda(topo, t("ajuda.req.predefinicao")).pack(side=tk.RIGHT, padx=(0, 6))
        ttk.Label(topo, text=t("req.preset")).pack(side=tk.RIGHT, padx=(0, 4))

        corpo = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        corpo.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 6))
        caixa_arquivo = ttk.LabelFrame(corpo, text=t("req.arquivo"))
        corpo.add(caixa_arquivo, weight=3)
        self.txt_arquivo = texto_rolavel(caixa_arquivo, fonte=("Consolas", 9))
        self.txt_arquivo.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        opcoes = ttk.LabelFrame(corpo, text=t("req.opcoes"))
        corpo.add(opcoes, weight=2)
        opcoes.columnconfigure(1, weight=1)
        opcoes.columnconfigure(3, weight=1)
        linha = 0

        rotulo_com_ajuda(opcoes, t("req.objetivo"), t("ajuda.req.objetivo")).grid(row=linha, column=0, columnspan=4, sticky="w", padx=6, pady=(6, 0))
        linha += 1
        self.txt_objetivo = self._texto(opcoes, 3)
        self.txt_objetivo.grid(row=linha, column=0, columnspan=4, sticky="ew", padx=6)
        linha += 1

        self.combos = {}
        for i, eixo in enumerate(EIXOS):
            r, c = linha + i // 2, (i % 2) * 2
            if i == 0:                    # um "?" só, explicando os quatro eixos
                rotulo = rotulo_com_ajuda(opcoes, t(f"req.eixo.{eixo}"), t("ajuda.req.eixos"))
            else:
                rotulo = ttk.Label(opcoes, text=t(f"req.eixo.{eixo}"))
            rotulo.grid(row=r, column=c, sticky="w", padx=6, pady=3)
            combo = ttk.Combobox(opcoes, state="readonly", values=[n for _, n in self._opcoes["eixos"][eixo]])
            combo.grid(row=r, column=c + 1, sticky="ew", padx=(0, 6), pady=3)
            self.combos[eixo] = combo
        linha += 2

        rotulo_com_ajuda(opcoes, t("req.extras"), t("ajuda.req.extras")).grid(row=linha, column=0, columnspan=4, sticky="w", padx=6, pady=(6, 0))
        linha += 1
        self.txt_extras = self._texto(opcoes, 3)
        self.txt_extras.grid(row=linha, column=0, columnspan=4, sticky="ew", padx=6)
        linha += 1

        self.combo_prof = self._combo_lista(opcoes, linha, 0, "req.profundidade", self._opcoes["profundidades"], "req.prof")
        self.combo_publico = self._combo_lista(opcoes, linha, 2, "req.publico", self._opcoes["publicos"], "req.pub")
        linha += 1
        self.combo_criatividade = self._combo_lista(opcoes, linha, 0, "req.criatividade", self._opcoes["criatividades"], "req.cri")
        self.combo_modo = self._combo_lista(opcoes, linha, 2, "req.modo", self._opcoes["modos"], "req.mod")
        linha += 1
        rotulo_com_ajuda(opcoes, t("req.nivel"), t("ajuda.req.mesa")).grid(row=linha, column=0, sticky="w", padx=6, pady=3)
        self.var_nivel = tk.StringVar(value="0")
        ttk.Spinbox(opcoes, from_=0, to=20, width=5, textvariable=self.var_nivel).grid(row=linha, column=1, sticky="w")
        ttk.Label(opcoes, text=t("req.jogadores")).grid(row=linha, column=2, sticky="w", padx=6)
        self.var_jogadores = tk.StringVar(value="0")
        ttk.Spinbox(opcoes, from_=0, to=10, width=5, textvariable=self.var_jogadores).grid(row=linha, column=3, sticky="w")
        linha += 1
        self.var_segredo = tk.BooleanVar()
        ttk.Checkbutton(opcoes, text=t("req.segredo"), variable=self.var_segredo).grid(row=linha, column=0, columnspan=2, sticky="w", padx=6, pady=3)
        self.var_criatura = tk.StringVar(value="npc")
        self.frame_criatura = ttk.Frame(opcoes)
        self.frame_criatura.grid(row=linha, column=2, columnspan=2, sticky="w")
        for valor in ("npc", "monstro"):
            ttk.Radiobutton(self.frame_criatura, text=t(f"req.criatura.{valor}"), value=valor,
                            variable=self.var_criatura).pack(side=tk.LEFT, padx=(0, 8))
        ajuda(self.frame_criatura, t("ajuda.req.segredo")).pack(side=tk.LEFT)
        linha += 1

        cab_refs = ttk.Frame(opcoes)
        cab_refs.grid(row=linha, column=0, columnspan=4, sticky="ew", padx=6, pady=(6, 0))
        ttk.Label(cab_refs, text=t("req.referencias")).pack(side=tk.LEFT)
        ajuda(cab_refs, t("ajuda.req.referencias")).pack(side=tk.LEFT, padx=(3, 0))
        ttk.Button(cab_refs, text=t("req.ref_adicionar"), command=self._adicionar_referencia).pack(side=tk.RIGHT)
        linha += 1
        self.tree_refs = ttk.Treeview(opcoes, columns=("ativo", "arquivo", "motivo"), show="headings", height=5)
        for coluna, largura in (("ativo", 30), ("arquivo", 200), ("motivo", 140)):
            self.tree_refs.heading(coluna, text=t(f"req.col_{coluna}"),
                                   command=self._alternar_todas_refs if coluna == "ativo" else "")
            self.tree_refs.column(coluna, width=largura, anchor="center" if coluna == "ativo" else "w", stretch=coluna == "arquivo")
        self.tree_refs.grid(row=linha, column=0, columnspan=4, sticky="nsew", padx=6, pady=2)
        self.tree_refs.bind("<Button-1>", self._clique_ref)
        opcoes.rowconfigure(linha, weight=1)
        linha += 1

        linha_tokens = ttk.Frame(opcoes)
        linha_tokens.grid(row=linha, column=0, columnspan=4, sticky="ew", padx=6, pady=(6, 0))
        self.lbl_tokens = ttk.Label(linha_tokens, text="", foreground=tema.SUAVE)
        self.lbl_tokens.pack(side=tk.LEFT)
        ajuda(linha_tokens, t("ajuda.req.tokens")).pack(side=tk.LEFT, padx=(3, 0))
        linha += 1
        rodape = ttk.Frame(opcoes)
        rodape.grid(row=linha, column=0, columnspan=4, sticky="ew", padx=6, pady=8)
        ttk.Button(rodape, text=t("req.cancelar"), command=self._cancelar).pack(side=tk.RIGHT)
        self.btn_enviar = ttk.Button(rodape, text=t("req.enviar"), command=self._enviar)
        self.btn_enviar.pack(side=tk.RIGHT, padx=4)
        ttk.Button(rodape, text=t("req.calcular"), command=self._atualizar_tokens).pack(side=tk.RIGHT)
        self._habilitar(False)

    # ------------------------------------------------------------------
    @staticmethod
    def _texto(parent, altura):
        return tk.Text(parent, height=altura, wrap=tk.WORD, font=("Segoe UI", 9), bg=tema.PAINEL, fg=tema.TEXTO,
                       insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#3a3a3a",
                       highlightcolor=tema.VERDE)

    @staticmethod
    def _combo_lista(parent, linha, coluna, rotulo, valores, prefixo):
        rotulo_com_ajuda(parent, t(rotulo), t(AJUDA_COMBOS[rotulo])).grid(row=linha, column=coluna, sticky="w", padx=6, pady=3)
        combo = ttk.Combobox(parent, state="readonly", values=[t(f"{prefixo}.{v}") for v in valores])
        combo.grid(row=linha, column=coluna + 1, sticky="ew", padx=(0, 6), pady=3)
        combo.valores = list(valores)
        return combo

    def _habilitar(self, ativo):
        self.btn_enviar.config(state=tk.NORMAL if ativo else tk.DISABLED)

    # ------------------------------------------------------------------
    # ABRIR UMA REQUISIÇÃO (chamado pelo Editor)
    # ------------------------------------------------------------------
    def abrir(self, tipo, caminho):
        self.req = acoes.nova_requisicao(tipo, caminho)
        self.lbl_alvo.config(text=t(f"req.tipo.{tipo}", nome=arq.nome(caminho)))
        try:
            conteudo = arq.ler_texto(caminho)
        except Exception as e:
            conteudo = str(e)
        substituir_texto(self.txt_arquivo, conteudo)
        self._refs = [(c, motivo, False) for c, motivo in acoes.sugerir_referencias(caminho)]
        self._preencher()
        self.combo_preset["values"] = acoes.presets_requisicao()
        self.combo_preset.set("")
        self._habilitar(True)
        self._atualizar_tokens()
        self.app.requisicao_aberta(arq.nome(caminho))

    def definir_objetivo(self, texto: str):
        """Preenche o objetivo (ex.: ao aplicar uma nota recém-salva)."""
        if self.req:
            self.req.objetivo = texto
            self.txt_objetivo.delete("1.0", tk.END)
            self.txt_objetivo.insert("1.0", texto)

    def _preencher(self):
        req = self.req
        self.txt_objetivo.delete("1.0", tk.END)
        self.txt_objetivo.insert("1.0", req.objetivo)
        for eixo in EIXOS:
            ids = [i for i, _ in self._opcoes["eixos"][eixo]]
            valor = getattr(req, eixo)
            if valor in ids:
                self.combos[eixo].current(ids.index(valor))
        self.txt_extras.delete("1.0", tk.END)
        self.txt_extras.insert("1.0", req.diretrizes_extras)
        for combo, valor in ((self.combo_prof, req.profundidade), (self.combo_publico, req.publico),
                             (self.combo_criatividade, req.criatividade), (self.combo_modo, req.modo)):
            combo.current(combo.valores.index(valor) if valor in combo.valores else 0)
        self.combo_modo.config(state="readonly" if req.tipo == "melhorar" else tk.DISABLED)
        self.var_nivel.set(str(req.nivel_grupo))
        self.var_jogadores.set(str(req.jogadores))
        self.var_segredo.set(bool(req.segredo))
        self.var_criatura.set(req.criatura)
        for filho in self.frame_criatura.winfo_children():
            filho.config(state=tk.NORMAL if req.tipo == "ficha" else tk.DISABLED)
        self._exibir_refs()

    def _ler_campos(self):
        """Copia os widgets para a Requisição."""
        req = self.req
        req.objetivo = self.txt_objetivo.get("1.0", "end").strip()
        for eixo in EIXOS:
            indice = self.combos[eixo].current()
            if indice >= 0:
                setattr(req, eixo, self._opcoes["eixos"][eixo][indice][0])
        req.diretrizes_extras = self.txt_extras.get("1.0", "end").strip()
        req.profundidade = self.combo_prof.valores[max(self.combo_prof.current(), 0)]
        req.publico = self.combo_publico.valores[max(self.combo_publico.current(), 0)]
        req.criatividade = self.combo_criatividade.valores[max(self.combo_criatividade.current(), 0)]
        req.modo = self.combo_modo.valores[max(self.combo_modo.current(), 0)]
        req.nivel_grupo = int(self.var_nivel.get()) if self.var_nivel.get().isdigit() else 0
        req.jogadores = int(self.var_jogadores.get()) if self.var_jogadores.get().isdigit() else 0
        req.segredo = bool(self.var_segredo.get())
        req.criatura = self.var_criatura.get()
        req.referencias = [c for c, _, marcado in self._refs if marcado]
        return req

    # ------------------------------------------------------------------
    # REFERÊNCIAS
    # ------------------------------------------------------------------
    def _exibir_refs(self):
        self.tree_refs.delete(*self.tree_refs.get_children())
        if not self._refs:
            self.tree_refs.insert("", "end", iid="vazio", values=("", t("req.ref_nenhuma"), ""))
        for i, (caminho, motivo, marcado) in enumerate(self._refs):
            self.tree_refs.insert("", "end", iid=str(i), values=("☑" if marcado else "☐", arq.nome(caminho), motivo))

    def _clique_ref(self, evento):
        iid = self.tree_refs.identify_row(evento.y)
        if iid and iid != "vazio":
            caminho, motivo, marcado = self._refs[int(iid)]
            self._refs[int(iid)] = (caminho, motivo, not marcado)
            self._exibir_refs()

    def _alternar_todas_refs(self):
        """O ✔ do cabeçalho marca todas as referências (ou desmarca, se todas já estão marcadas)."""
        if not self._refs:
            return
        marcar = not all(marcado for _, _, marcado in self._refs)
        self._refs = [(caminho, motivo, marcar) for caminho, motivo, _ in self._refs]
        self._exibir_refs()

    def _adicionar_referencia(self):
        if not self.req:
            return
        caminho = filedialog.askopenfilename(parent=self, title=t("req.ref_adicionar"),
                                             initialdir=acoes.projeto_ativo()[1], filetypes=[("Markdown", "*.md")])
        if caminho:
            self._refs.append((caminho, t("req.ref_manual"), True))
            self._exibir_refs()

    # ------------------------------------------------------------------
    # PRESETS, TOKENS E ENVIO
    # ------------------------------------------------------------------
    def _aplicar_preset(self):
        if self.req and self.combo_preset.get():
            self._ler_campos()
            acoes.aplicar_preset_requisicao(self.combo_preset.get(), self.req)
            self._preencher()
            self.app.toast(t("req.toast_preset", nome=self.combo_preset.get()))

    def _salvar_preset(self):
        if not self.req:
            return
        nome = simpledialog.askstring(t("req.preset_salvar"), t("req.preset_nome"), parent=self)
        if nome and nome.strip():
            acoes.salvar_preset_requisicao(nome.strip(), self._ler_campos())
            self.combo_preset["values"] = acoes.presets_requisicao()
            self.combo_preset.set(nome.strip())
            self.app.toast(t("req.toast_preset_salvo", nome=nome.strip()))

    def _excluir_preset(self):
        nome = self.combo_preset.get()
        if nome and messagebox.askyesno(t("req.preset_excluir"), t("req.preset_confirmar", nome=nome), parent=self):
            acoes.excluir_preset_requisicao(nome)
            self.combo_preset["values"] = acoes.presets_requisicao()
            self.combo_preset.set("")

    def _atualizar_tokens(self):
        if self.req:
            self.lbl_tokens.config(text=t("req.tokens", total=f"{acoes.estimar_tokens_requisicao(self._ler_campos()):,}"))

    def _enviar(self):
        if not self.req:
            return
        req = self._ler_campos()
        editor = self.app.pagina("editor")
        if req.tipo == "conselho":
            editor.enviar_conselho(req.caminho, requisicao=req)
        else:
            editor.executar_requisicao(req)
            self.app.mostrar_pagina("editor")
        self._limpar()

    def _cancelar(self):
        self._limpar()
        self.app.mostrar_pagina("editor")

    def _limpar(self):
        self.req = None
        self.lbl_alvo.config(text=t("req.vazio"))
        substituir_texto(self.txt_arquivo, "")
        self._refs = []
        self._exibir_refs()
        self.lbl_tokens.config(text="")
        self._habilitar(False)
        self.app.requisicao_aberta(None)
