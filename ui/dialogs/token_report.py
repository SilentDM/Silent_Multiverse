"""Janela do relatório de tamanho do projeto (tokens por pasta e arquivo)."""
import tkinter as tk
from tkinter import ttk

import core.tarefas as tarefas
import engine.token_counter as tc
import ui.theme as tema
from core.i18n import t

COLUNAS = ("tamanho", "tok_m", "tok_j", "pct", "situacao")
LARGURAS = {"tamanho": 85, "tok_m": 175, "tok_j": 190, "pct": 85, "situacao": 245}


class JanelaTamanhoProjeto(tk.Toplevel):
    def __init__(self, parent, analise: tc.AnaliseProjeto, toast_callback=None):
        super().__init__(parent)
        self.analise = analise
        self.toast = toast_callback or (lambda m: None)
        self.fator = 1.0
        self.exato = None            # resultado de tc.contar_contextos_exatos()
        self.limite, self.desc_limite = tc.obter_limite_contexto_local()
        self.coluna, self.decrescente = "tok_m", True

        self.title(t("relatorio.janela_titulo", projeto=analise.nome_projeto))
        self.geometry("1100x760")
        self.minsize(800, 520)
        self.configure(bg=tema.FUNDO)
        self.transient(parent)

        self._montar_cabecalho()
        self._montar_cartoes()
        self._montar_barras()
        self._montar_arvore()
        self._montar_botoes()
        self._atualizar()

    # ------------------------------------------------------------------
    # VALORES EXIBIDOS
    # ------------------------------------------------------------------
    def _tokens(self, chars: int) -> int:
        return int(round(tc.estimar_tokens(chars) * self.fator))

    @property
    def total_mestre(self):
        return self.exato["mestre"] if self.exato else self._tokens(self.analise.chars_bundle_mestre)

    @property
    def total_jogador(self):
        return self.exato["jogador"] if self.exato else self._tokens(self.analise.chars_bundle_jogador)

    def _prefixo(self):
        return "" if self.exato else "≈ "

    def _cor_uso(self, tokens):
        uso = tokens / self.limite if self.limite else 0
        return tema.VERMELHO if uso >= 0.9 else tema.AMARELO if uso >= 0.6 else tema.VERDE

    # ------------------------------------------------------------------
    # MONTAGEM
    # ------------------------------------------------------------------
    def _montar_cabecalho(self):
        topo = tk.Frame(self, bg=tema.FUNDO)
        topo.pack(fill=tk.X, padx=16, pady=(14, 6))
        tk.Label(topo, text=t("relatorio.cabecalho", projeto=self.analise.nome_projeto),
                 font=("Segoe UI", 13, "bold"), bg=tema.FUNDO, fg=tema.VERDE).pack(anchor=tk.W)
        tk.Label(topo, text=str(self.analise.raiz), font=("Segoe UI", 8), bg=tema.FUNDO, fg=tema.SUAVE).pack(anchor=tk.W)

    def _montar_cartoes(self):
        linha = tk.Frame(self, bg=tema.FUNDO)
        linha.pack(fill=tk.X, padx=12, pady=4)
        self.cartoes = {}
        for i, chave in enumerate(["arquivos", "disco", "mestre", "jogador", "limite"]):
            cartao = tk.Frame(linha, bg=tema.CARTAO, highlightbackground="#2d2d2d", highlightthickness=1)
            cartao.grid(row=0, column=i, sticky="nsew", padx=4)
            linha.columnconfigure(i, weight=1)
            tk.Label(cartao, text=t(f"relatorio.cartao_{chave}"), font=("Segoe UI", 8), bg=tema.CARTAO,
                     fg=tema.SUAVE).pack(anchor=tk.W, padx=10, pady=(8, 0))
            valor = tk.Label(cartao, text="-", font=("Segoe UI", 13, "bold"), bg=tema.CARTAO, fg=tema.TEXTO)
            valor.pack(anchor=tk.W, padx=10)
            detalhe = tk.Label(cartao, text="", font=("Segoe UI", 8), bg=tema.CARTAO, fg=tema.SUAVE)
            detalhe.pack(anchor=tk.W, padx=10, pady=(0, 8))
            self.cartoes[chave] = (valor, detalhe)

    def _montar_barras(self):
        caixa = tk.Frame(self, bg=tema.FUNDO)
        caixa.pack(fill=tk.X, padx=16, pady=(8, 2))
        self.barras = {}
        for chave in ("mestre", "jogador"):
            linha = tk.Frame(caixa, bg=tema.FUNDO)
            linha.pack(fill=tk.X, pady=2)
            tk.Label(linha, text=t(f"relatorio.uso_{chave}"), width=26, anchor="w", font=("Segoe UI", 9),
                     bg=tema.FUNDO, fg=tema.TEXTO).pack(side=tk.LEFT)
            canvas = tk.Canvas(linha, height=22, bg=tema.CARTAO, highlightthickness=0, bd=0)
            canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
            canvas.bind("<Configure>", lambda e: self._desenhar_barras())
            self.barras[chave] = canvas
        self.lbl_nota = tk.Label(caixa, text="", font=("Segoe UI", 8, "italic"), bg=tema.FUNDO, fg=tema.SUAVE,
                                 justify="left", anchor="w", wraplength=1000)
        self.lbl_nota.pack(fill=tk.X, pady=(6, 0))

    def _montar_arvore(self):
        quadro = tk.Frame(self, bg=tema.FUNDO)
        quadro.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
        self.tree = ttk.Treeview(quadro, columns=COLUNAS, show="tree headings", selectmode="browse")
        self.tree.heading("#0", command=lambda: self._ordenar("nome"))
        self.tree.column("#0", width=290, anchor="w")
        for coluna in COLUNAS:
            self.tree.column(coluna, width=LARGURAS[coluna], anchor="w" if coluna == "situacao" else "e")
            self.tree.heading(coluna, command=lambda c=coluna: self._ordenar(c))
        barra = ttk.Scrollbar(quadro, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        barra.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.tag_configure("pasta", font=("Segoe UI", 9, "bold"))
        self.tree.tag_configure("excluido", foreground="#6b6b6b")
        self.tree.tag_configure("oculto", foreground=tema.AMARELO)
        self.tree.tag_configure("overhead", foreground=tema.AZUL)

    def _montar_botoes(self):
        barra = tk.Frame(self, bg=tema.FUNDO)
        barra.pack(fill=tk.X, padx=16, pady=(0, 14))
        self.btn_exato = ttk.Button(barra, text=t("relatorio.btn_exato"), command=self._contar_exato)
        self.btn_exato.pack(side=tk.LEFT)
        ttk.Button(barra, text=t("relatorio.btn_copiar"), command=self._copiar).pack(side=tk.LEFT, padx=6)
        ttk.Button(barra, text=t("relatorio.btn_expandir"), command=lambda: self._expandir(True)).pack(side=tk.LEFT, padx=(18, 2))
        ttk.Button(barra, text=t("relatorio.btn_recolher"), command=lambda: self._expandir(False)).pack(side=tk.LEFT)
        ttk.Button(barra, text=t("comum.fechar"), command=self.destroy).pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    # ATUALIZAÇÃO
    # ------------------------------------------------------------------
    def _atualizar(self):
        a = self.analise
        p = self._prefixo()
        self._cartao("arquivos", f"{len(a.arquivos):,}",
                     t("relatorio.detalhe_arquivos", incluidos=f"{a.arquivos_incluidos:,}",
                       fora=f"{len(a.arquivos) - a.arquivos_incluidos:,}"))
        self._cartao("disco", tc.formatar_bytes(a.bytes_total), t("relatorio.detalhe_disco"))
        for chave, total in (("mestre", self.total_mestre), ("jogador", self.total_jogador)):
            self._cartao(chave, f"{p}{total:,}", t("relatorio.detalhe_pct", pct=f"{total / self.limite:.0%}"),
                         cor=self._cor_uso(total))
        self._cartao("limite", f"{self.limite:,}", self.desc_limite)

        if self.exato:
            nota = t("relatorio.nota_exata", provedor=self.desc_limite, fator=f"{self.fator:.2f}")
        else:
            nota = t("relatorio.nota_estimada", chars=tc.CHARS_POR_TOKEN_ESTIMADO)
        if self.total_mestre > self.limite:
            nota += "\n" + t("relatorio.nota_excede", excesso=f"{self.total_mestre - self.limite:,}")
        self.lbl_nota.config(text=nota, fg=tema.SUAVE)
        self._desenhar_barras()
        self._popular_arvore()

    def _cartao(self, chave, valor, detalhe, cor=tema.TEXTO):
        rotulo_valor, rotulo_detalhe = self.cartoes[chave]
        rotulo_valor.config(text=valor, fg=cor)
        rotulo_detalhe.config(text=detalhe)

    def _desenhar_barras(self):
        for chave, total in (("mestre", self.total_mestre), ("jogador", self.total_jogador)):
            canvas = self.barras[chave]
            canvas.delete("all")
            largura = max(canvas.winfo_width(), 50)
            uso = total / self.limite if self.limite else 0
            canvas.create_rectangle(0, 0, int(largura * min(uso, 1.0)), 22, fill=self._cor_uso(total), width=0)
            texto = t("relatorio.barra", prefixo=self._prefixo(), total=f"{total:,}", limite=f"{self.limite:,}", pct=f"{uso:.0%}")
            if uso > 1:
                texto += t("relatorio.barra_excede")
            canvas.create_text(8, 11, text=texto, anchor="w", fill="#ffffff", font=("Segoe UI", 9, "bold"))

    def _ordenar(self, coluna):
        if self.coluna == coluna:
            self.decrescente = not self.decrescente
        else:
            self.coluna, self.decrescente = coluna, coluna not in ("nome", "situacao")
        self._popular_arvore()

    def _popular_arvore(self):
        abertos = {self.tree.item(i, "text") for i in self._todos() if self.tree.item(i, "open")}
        self.tree.delete(*self.tree.get_children())
        total = max(self.total_mestre, 1)

        def inserir(pai, nos):
            for no in nos:
                tok_m, tok_j = self._tokens(no.chars_mestre), self._tokens(no.chars_jogador)
                if no.tipo == "pasta":
                    tags = ("pasta",)
                elif no.estado not in ("incluido", "parcial", "oculto"):
                    tags = ("excluido",)
                elif no.estado in ("parcial", "oculto"):
                    tags = ("oculto",)
                else:
                    tags = ()
                texto = ("📁 " if no.tipo == "pasta" else "📄 ") + no.nome
                iid = self.tree.insert(pai, "end", text=texto, tags=tags, open=texto in abertos, values=(
                    tc.formatar_bytes(no.bytes_disco),
                    f"{tok_m:,}" if no.chars_mestre else "—",
                    f"{tok_j:,}" if no.chars_jogador else "—",
                    f"{tok_m / total:.1%}" if no.chars_mestre else "—",
                    no.situacao,
                ))
                inserir(iid, no.filhos)

        inserir("", tc.montar_arvore_relatorio(self.analise, self.coluna, self.decrescente))
        om, oj = self.analise.overhead_chars_mestre, self.analise.overhead_chars_jogador
        self.tree.insert("", "end", text=t("relatorio.overhead"), tags=("overhead",), values=(
            "—", f"{self._tokens(om):,}", f"{self._tokens(oj):,}", f"{self._tokens(om) / total:.1%}",
            t("relatorio.overhead_situacao")))

        sufixo = t("relatorio.sufixo_calibrado") if self.exato else " (≈)"
        titulos = {"#0": ("nome", t("relatorio.col_nome")), "tamanho": ("tamanho", t("relatorio.col_tamanho")),
                   "tok_m": ("tok_m", t("relatorio.col_tok_m") + sufixo), "tok_j": ("tok_j", t("relatorio.col_tok_j") + sufixo),
                   "pct": ("pct", t("relatorio.col_pct")), "situacao": ("situacao", t("relatorio.col_situacao"))}
        for coluna, (chave, titulo) in titulos.items():
            if chave == self.coluna:
                titulo += " ▼" if self.decrescente else " ▲"
            self.tree.heading(coluna, text=titulo)

    def _todos(self, pai=""):
        for iid in self.tree.get_children(pai):
            yield iid
            yield from self._todos(iid)

    def _expandir(self, abrir):
        for iid in self._todos():
            self.tree.item(iid, open=abrir)

    # ------------------------------------------------------------------
    # AÇÕES
    # ------------------------------------------------------------------
    def _contar_exato(self):
        self.btn_exato.config(state=tk.DISABLED, text=t("relatorio.btn_contando"))
        tarefas.executar_em_segundo_plano(tc.contar_contextos_exatos, self.analise,
                                          ao_concluir=self._aplicar_exato, ao_falhar=self._falha_exato)

    def _aplicar_exato(self, resultado):
        if not self.winfo_exists():
            return
        self.exato = resultado
        self.fator = resultado["fator"]
        if resultado.get("limite"):
            self.limite = int(resultado["limite"])
        self.desc_limite = resultado["provedor"]
        self.btn_exato.config(state=tk.NORMAL, text=t("relatorio.btn_recontar"))
        self.toast(t("relatorio.toast_exato"))
        self._atualizar()

    def _falha_exato(self, erro):
        if not self.winfo_exists():
            return
        self.btn_exato.config(state=tk.NORMAL, text=t("relatorio.btn_exato"))
        self.lbl_nota.config(text=t("relatorio.nota_falha", erro=erro, dica=tc.dica_erro_contagem(erro)), fg=tema.VERMELHO)

    def _copiar(self):
        texto = tc.gerar_resumo_texto(self.analise, self.fator, self.fator, self.limite, bool(self.exato),
                                      self.exato["mestre"] if self.exato else None,
                                      self.exato["jogador"] if self.exato else None)
        self.clipboard_clear()
        self.clipboard_append(texto)
        self.toast(t("relatorio.toast_copiado"))
