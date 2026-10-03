"""Janela do relatório de tamanho do projeto (tokens por pasta e arquivo)."""
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import engine.token_counter as tc

COR_FUNDO = "#121212"
COR_CARTAO = "#18181c"
COR_TEXTO = "#e3e3e3"
COR_SUAVE = "#888888"
COR_VERDE = "#10b981"
COR_AMARELO = "#f59e0b"
COR_VERMELHO = "#ef4444"
COR_AZUL = "#60a5fa"


class TokenReportWindow(tk.Toplevel):
    def __init__(self, parent, analise: tc.AnaliseProjeto, log_callback=None, toast_callback=None):
        super().__init__(parent)
        self.analise = analise
        self.log_callback = log_callback or (lambda m: None)
        self.toast_callback = toast_callback or (lambda m: None)

        # Fatores de calibração (1.0 = estimativa pura; ajustados após a contagem exata)
        self.fator_mestre = 1.0
        self.fator_jogador = 1.0
        self.exato = False
        self.exato_mestre = None
        self.exato_jogador = None
        self.limite, self.desc_limite = tc.obter_limite_contexto_local()

        self.sort_col = "tok_m"
        self.sort_desc = True

        self.title(f"Tamanho do Projeto - {analise.nome_projeto}")
        self.geometry("1100x760")
        self.minsize(800, 520)
        self.configure(bg=COR_FUNDO)
        self.transient(parent)

        self._montar_cabecalho()
        self._montar_cartoes()
        self._montar_barras()
        self._montar_arvore()
        self._montar_botoes()

        self._atualizar_tudo()

    # ------------------------------------------------------------------
    # VALORES CALCULADOS
    # ------------------------------------------------------------------
    def _tok_m(self, chars: int) -> int:
        return int(round(tc.estimar_tokens(chars) * self.fator_mestre))

    def _tok_j(self, chars: int) -> int:
        return int(round(tc.estimar_tokens(chars) * self.fator_jogador))

    @property
    def total_mestre(self) -> int:
        # Após a contagem exata, o total é o valor devolvido pela API (sem arredondamentos da calibração)
        if self.exato_mestre is not None:
            return self.exato_mestre
        return self._tok_m(self.analise.chars_bundle_mestre)

    @property
    def total_jogador(self) -> int:
        if self.exato_jogador is not None:
            return self.exato_jogador
        return self._tok_j(self.analise.chars_bundle_jogador)

    def _prefixo(self) -> str:
        return "" if self.exato else "≈ "

    # ------------------------------------------------------------------
    # MONTAGEM DA INTERFACE
    # ------------------------------------------------------------------
    def _montar_cabecalho(self):
        header = tk.Frame(self, bg=COR_FUNDO)
        header.pack(fill=tk.X, padx=16, pady=(14, 6))
        tk.Label(header, text=f"📊 Tamanho do Projeto — {self.analise.nome_projeto}",
                 font=("Segoe UI", 13, "bold"), bg=COR_FUNDO, fg=COR_VERDE).pack(anchor=tk.W)
        tk.Label(header, text=str(self.analise.raiz), font=("Segoe UI", 8),
                 bg=COR_FUNDO, fg=COR_SUAVE).pack(anchor=tk.W)

    def _criar_cartao(self, parent, titulo):
        card = tk.Frame(parent, bg=COR_CARTAO, highlightbackground="#2d2d2d", highlightthickness=1)
        tk.Label(card, text=titulo, font=("Segoe UI", 8), bg=COR_CARTAO, fg=COR_SUAVE).pack(anchor=tk.W, padx=10, pady=(8, 0))
        valor = tk.Label(card, text="-", font=("Segoe UI", 13, "bold"), bg=COR_CARTAO, fg=COR_TEXTO)
        valor.pack(anchor=tk.W, padx=10)
        detalhe = tk.Label(card, text="", font=("Segoe UI", 8), bg=COR_CARTAO, fg=COR_SUAVE)
        detalhe.pack(anchor=tk.W, padx=10, pady=(0, 8))
        return card, valor, detalhe

    def _montar_cartoes(self):
        linha = tk.Frame(self, bg=COR_FUNDO)
        linha.pack(fill=tk.X, padx=12, pady=4)
        self.cartoes = {}
        for i, (chave, titulo) in enumerate([
            ("arquivos", "Arquivos .md"),
            ("disco", "Tamanho em disco"),
            ("mestre", "Tokens — contexto do Mestre"),
            ("jogador", "Tokens — contexto dos Jogadores"),
            ("limite", "Limite de contexto do provedor"),
        ]):
            card, valor, detalhe = self._criar_cartao(linha, titulo)
            card.grid(row=0, column=i, sticky="nsew", padx=4)
            linha.columnconfigure(i, weight=1)
            self.cartoes[chave] = (valor, detalhe)

    def _montar_barras(self):
        box = tk.Frame(self, bg=COR_FUNDO)
        box.pack(fill=tk.X, padx=16, pady=(8, 2))
        self.barras = {}
        for chave, rotulo in [("mestre", "Mestre"), ("jogador", "Jogadores")]:
            linha = tk.Frame(box, bg=COR_FUNDO)
            linha.pack(fill=tk.X, pady=2)
            tk.Label(linha, text=f"Uso do limite ({rotulo}):", width=22, anchor="w",
                     font=("Segoe UI", 9), bg=COR_FUNDO, fg=COR_TEXTO).pack(side=tk.LEFT)
            canvas = tk.Canvas(linha, height=22, bg=COR_CARTAO, highlightthickness=0, bd=0)
            canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
            canvas.bind("<Configure>", lambda e: self._desenhar_barras())
            self.barras[chave] = canvas

        self.lbl_nota = tk.Label(box, text="", font=("Segoe UI", 8, "italic"), bg=COR_FUNDO,
                                 fg=COR_SUAVE, justify="left", anchor="w", wraplength=1000)
        self.lbl_nota.pack(fill=tk.X, pady=(6, 0))

    def _montar_arvore(self):
        frame = tk.Frame(self, bg=COR_FUNDO)
        frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        colunas = ("tamanho", "tok_m", "tok_j", "pct", "situacao")
        self.tree = ttk.Treeview(frame, columns=colunas, show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Pasta / Arquivo", anchor="w", command=lambda: self._ordenar("nome"))
        self.tree.column("#0", width=290, anchor="w")
        larguras = {"tamanho": 85, "tok_m": 175, "tok_j": 190, "pct": 85, "situacao": 245}
        for col in colunas:
            self.tree.column(col, width=larguras[col], anchor="e" if col != "situacao" else "w")
            self.tree.heading(col, command=lambda c=col: self._ordenar(c))

        ysb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.tag_configure("pasta", font=("Segoe UI", 9, "bold"))
        self.tree.tag_configure("excluido", foreground="#6b6b6b")
        self.tree.tag_configure("oculto", foreground=COR_AMARELO)
        self.tree.tag_configure("overhead", foreground=COR_AZUL)

    def _montar_botoes(self):
        barra = tk.Frame(self, bg=COR_FUNDO)
        barra.pack(fill=tk.X, padx=16, pady=(0, 14))
        self.btn_exato = ttk.Button(barra, text="🎯 Contagem exata via API (gratuita)", command=self._iniciar_contagem_exata)
        self.btn_exato.pack(side=tk.LEFT)
        ttk.Button(barra, text="📋 Copiar resumo", command=self._copiar_resumo).pack(side=tk.LEFT, padx=6)
        ttk.Button(barra, text="Expandir tudo", command=lambda: self._expandir(True)).pack(side=tk.LEFT, padx=(18, 2))
        ttk.Button(barra, text="Recolher tudo", command=lambda: self._expandir(False)).pack(side=tk.LEFT)
        ttk.Button(barra, text="Fechar", command=self.destroy).pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    # ATUALIZAÇÃO DOS DADOS NA TELA
    # ------------------------------------------------------------------
    def _atualizar_tudo(self):
        a = self.analise
        p = self._prefixo()
        excluidos = len(a.arquivos) - a.arquivos_incluidos

        self._set_cartao("arquivos", f"{len(a.arquivos):,}",
                         f"{a.arquivos_incluidos:,} no contexto · {excluidos:,} fora")
        self._set_cartao("disco", tc.formatar_bytes(a.bytes_total), "somente arquivos .md")
        self._set_cartao("mestre", f"{p}{self.total_mestre:,}", f"{self.total_mestre / self.limite:.0%} do limite",
                         cor=self._cor_uso(self.total_mestre))
        self._set_cartao("jogador", f"{p}{self.total_jogador:,}", f"{self.total_jogador / self.limite:.0%} do limite",
                         cor=self._cor_uso(self.total_jogador))
        self._set_cartao("limite", f"{self.limite:,}", self.desc_limite)

        if self.exato:
            nota = (f"✅ Totais contados pela API ({self.desc_limite}). Os valores por arquivo são estimativas "
                    f"calibradas por esses totais (fator {self.fator_mestre:.2f}).")
        else:
            nota = (f"Valores estimados localmente (~{tc.CHARS_POR_TOKEN_ESTIMADO} caracteres por token). "
                    "Clique em '🎯 Contagem exata' para medir os totais reais com o provedor ativo, sem custo.")
        if self.total_mestre > self.limite:
            nota += (f"\n⚠️ O contexto do Mestre excede o limite em {self.total_mestre - self.limite:,} tokens: "
                     "as requisições com o mundo inteiro serão recusadas pelo provedor.")
        self.lbl_nota.config(text=nota, fg=COR_SUAVE)

        self._desenhar_barras()
        self._popular_arvore()

    def _set_cartao(self, chave, valor, detalhe, cor=COR_TEXTO):
        lbl_valor, lbl_detalhe = self.cartoes[chave]
        lbl_valor.config(text=valor, fg=cor)
        lbl_detalhe.config(text=detalhe)

    def _cor_uso(self, tokens: int) -> str:
        uso = tokens / self.limite if self.limite else 0
        if uso >= 0.9:
            return COR_VERMELHO
        if uso >= 0.6:
            return COR_AMARELO
        return COR_VERDE

    def _desenhar_barras(self):
        for chave, total in (("mestre", self.total_mestre), ("jogador", self.total_jogador)):
            canvas = self.barras[chave]
            canvas.delete("all")
            largura = max(canvas.winfo_width(), 50)
            uso = total / self.limite if self.limite else 0
            canvas.create_rectangle(0, 0, int(largura * min(uso, 1.0)), 22, fill=self._cor_uso(total), width=0)
            texto = f"{self._prefixo()}{total:,} / {self.limite:,} tokens ({uso:.0%})"
            if uso > 1:
                texto += " — EXCEDE O LIMITE"
            canvas.create_text(8, 11, text=texto, anchor="w", fill="#ffffff", font=("Segoe UI", 9, "bold"))

    # ------------------------------------------------------------------
    # ÁRVORE DE PASTAS E ARQUIVOS
    # ------------------------------------------------------------------
    def _agregar_pastas(self):
        """Soma tamanhos/tokens de cada pasta (incluindo subpastas)."""
        pastas = {}
        for arq in self.analise.arquivos:
            for pasta in arq.caminho_relativo.parents:
                if str(pasta) == ".":
                    continue
                info = pastas.setdefault(pasta, {"bytes": 0, "cm": 0, "cj": 0, "n": 0, "incl": 0})
                info["bytes"] += arq.bytes_disco
                info["cm"] += arq.chars_mestre
                info["cj"] += arq.chars_jogador
                info["n"] += 1
                info["incl"] += 0 if arq.motivo_mestre else 1
        return pastas

    def _chave_ordenacao(self, nome, bytes_, cm, cj, situacao):
        return {
            "nome": nome.lower(),
            "tamanho": bytes_,
            "tok_m": cm,
            "pct": cm,
            "tok_j": cj,
            "situacao": situacao,
        }[self.sort_col]

    def _ordenar(self, coluna):
        if self.sort_col == coluna:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = coluna
            self.sort_desc = coluna not in ("nome", "situacao")
        self._popular_arvore()

    def _popular_arvore(self):
        abertos = {self.tree.item(i, "text") for i in self._todos_itens() if self.tree.item(i, "open")}
        self.tree.delete(*self.tree.get_children())

        pastas = self._agregar_pastas()
        total_m = max(self.total_mestre, 1)

        # Filhos diretos de cada pasta (Path(".") = raiz)
        filhos = {}
        for pasta in pastas:
            filhos.setdefault(pasta.parent, []).append(("pasta", pasta))
        for arq in self.analise.arquivos:
            filhos.setdefault(arq.caminho_relativo.parent, []).append(("arquivo", arq))

        def dados(tipo, obj):
            if tipo == "pasta":
                info = pastas[obj]
                return obj.name, info["bytes"], info["cm"], info["cj"], f"{info['n']} arquivos ({info['incl']} no contexto)"
            return obj.caminho_relativo.stem, obj.bytes_disco, obj.chars_mestre, obj.chars_jogador, obj.situacao

        def inserir(parent_iid, pasta_rel):
            itens = filhos.get(pasta_rel, [])
            itens.sort(key=lambda t: (t[0] != "pasta" if self.sort_col == "nome" else 0,
                                      self._chave_ordenacao(*dados(*t))),
                       reverse=self.sort_desc)
            for tipo, obj in itens:
                nome, bytes_, cm, cj, situacao = dados(tipo, obj)
                tok_m, tok_j = self._tok_m(cm), self._tok_j(cj)
                icone = "📁 " if tipo == "pasta" else "📄 "
                if tipo == "pasta":
                    tags = ("pasta",)
                elif obj.motivo_mestre:
                    tags = ("excluido",)
                elif obj.chars_jogador < obj.chars_mestre:
                    tags = ("oculto",)
                else:
                    tags = ()
                texto = f"{icone}{nome}"
                iid = self.tree.insert(parent_iid, "end", text=texto, tags=tags, open=texto in abertos, values=(
                    tc.formatar_bytes(bytes_),
                    f"{tok_m:,}" if cm else "—",
                    f"{tok_j:,}" if cj else "—",
                    f"{tok_m / total_m:.1%}" if cm else "—",
                    situacao,
                ))
                if tipo == "pasta":
                    inserir(iid, obj)

        inserir("", Path("."))

        # Estrutura de pastas + índice + separadores (também ocupa contexto)
        om, oj = self.analise.overhead_chars_mestre, self.analise.overhead_chars_jogador
        self.tree.insert("", "end", text="⚙️ Estrutura de pastas, índice e separadores", tags=("overhead",), values=(
            "—", f"{self._tok_m(om):,}", f"{self._tok_j(oj):,}", f"{self._tok_m(om) / total_m:.1%}",
            "Gerado automaticamente no contexto",
        ))

        # Indica a coluna ordenada no cabeçalho
        titulos = {"#0": ("nome", "Pasta / Arquivo"), "tamanho": ("tamanho", "Tamanho"),
                   "tok_m": ("tok_m", "Tokens Mestre"), "tok_j": ("tok_j", "Tokens Jogadores"),
                   "pct": ("pct", "% do total"), "situacao": ("situacao", "Situação")}
        for col, (chave, titulo) in titulos.items():
            if chave in ("tok_m", "tok_j") and self.exato:
                titulo += " (calibrado)"
            elif chave in ("tok_m", "tok_j"):
                titulo += " (≈)"
            if chave == self.sort_col:
                titulo += " ▼" if self.sort_desc else " ▲"
            self.tree.heading(col, text=titulo)

    def _todos_itens(self, parent=""):
        for iid in self.tree.get_children(parent):
            yield iid
            yield from self._todos_itens(iid)

    def _expandir(self, abrir: bool):
        for iid in self._todos_itens():
            self.tree.item(iid, open=abrir)

    # ------------------------------------------------------------------
    # AÇÕES
    # ------------------------------------------------------------------
    def _iniciar_contagem_exata(self):
        self.btn_exato.config(state=tk.DISABLED, text="⏳ Contando tokens na API...")
        self.log_callback("Contando tokens exatos do contexto do mundo via API...")

        def _worker():
            try:
                r_m = tc.contar_tokens_exatos(self.analise.bundle_mestre)
                r_j = tc.contar_tokens_exatos(self.analise.bundle_jogador)
                self.after(0, lambda: self._aplicar_contagem_exata(r_m, r_j))
            except Exception as e:
                self.after(0, lambda err=str(e): self._falha_contagem_exata(err))

        threading.Thread(target=_worker, daemon=True).start()

    def _aplicar_contagem_exata(self, r_m, r_j):
        if not self.winfo_exists():
            return
        est_m = tc.estimar_tokens(self.analise.chars_bundle_mestre)
        est_j = tc.estimar_tokens(self.analise.chars_bundle_jogador)
        self.fator_mestre = r_m["tokens"] / est_m if est_m else 1.0
        self.fator_jogador = r_j["tokens"] / est_j if est_j else 1.0
        self.exato = True
        self.exato_mestre = r_m["tokens"]
        self.exato_jogador = r_j["tokens"]
        if r_m.get("limite"):
            self.limite = int(r_m["limite"])
        self.desc_limite = r_m["provedor"]
        self.btn_exato.config(state=tk.NORMAL, text="🎯 Recontar via API")
        self.log_callback(f"Contagem exata: Mestre {r_m['tokens']:,} / Jogadores {r_j['tokens']:,} tokens ({r_m['provedor']}).")
        self.toast_callback("🎯 Contagem exata concluída!")
        self._atualizar_tudo()

    def _falha_contagem_exata(self, erro: str):
        if not self.winfo_exists():
            return
        self.btn_exato.config(state=tk.NORMAL, text="🎯 Contagem exata via API (gratuita)")
        self.log_callback(f"Falha na contagem exata de tokens: {erro}")
        dica = ""
        if "too long" in erro.lower() or "exceed" in erro.lower() or "limit" in erro.lower():
            dica = " O contexto provavelmente é maior que o limite aceito pelo provedor."
        self.lbl_nota.config(text=f"❌ Não foi possível contar via API: {erro}.{dica} Os valores exibidos continuam estimados.",
                             fg=COR_VERMELHO)

    def _copiar_resumo(self):
        texto = tc.gerar_resumo_texto(self.analise, self.fator_mestre, self.fator_jogador, self.limite, self.exato,
                                     self.exato_mestre, self.exato_jogador)
        self.clipboard_clear()
        self.clipboard_append(texto)
        self.toast_callback("📋 Resumo copiado para a área de transferência!")
