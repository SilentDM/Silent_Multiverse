"""Página Performance Gemini: cartões dos modelos e ordem de uso."""
import tkinter as tk
from tkinter import ttk

import core.modelos_gemini as modelos
import engine.acoes as acoes
import ui.theme as tema
from core.i18n import t
from ui.widgets import PaginaBase

LARGURA_CARTAO = 340


class PaginaModelos(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.lista = []
        self._colunas = 0

        topo = ttk.Frame(self)
        topo.pack(fill=tk.X, padx=18, pady=(18, 10))
        titulo = ttk.Frame(topo)
        titulo.pack(side=tk.LEFT)
        ttk.Label(titulo, text=t("models.titulo"), font=("Segoe UI", 14, "bold"), foreground=tema.VERDE).pack(anchor=tk.W)
        ttk.Label(titulo, text=t("models.subtitulo"), font=("Segoe UI", 9), foreground=tema.SUAVE).pack(anchor=tk.W, pady=(3, 0))
        botoes = ttk.Frame(topo)
        botoes.pack(side=tk.RIGHT)
        ttk.Button(botoes, text=t("models.btn_benchmark"), command=self._benchmark).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(botoes, text=t("models.btn_atualizar"), command=self.atualizar).pack(side=tk.LEFT)

        modo = ttk.Frame(self)
        modo.pack(fill=tk.X, padx=18, pady=(0, 10))
        ttk.Label(modo, text=t("models.modo"), font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        self.var_modo = tk.StringVar(value=modelos.modo_ordenacao())
        for valor, rotulo in ((modelos.MODO_AUTOMATICO, t("models.modo_auto")), (modelos.MODO_MANUAL, t("models.modo_manual"))):
            ttk.Radiobutton(modo, text=rotulo, value=valor, variable=self.var_modo,
                            command=self._mudar_modo).pack(side=tk.LEFT, padx=(0, 15))

        self.canvas = tk.Canvas(self, bg=tema.FUNDO, highlightthickness=0, bd=0)
        barra = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.interno = ttk.Frame(self.canvas)
        self.interno.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._janela = self.canvas.create_window((0, 0), window=self.interno, anchor="nw")
        self.canvas.configure(yscrollcommand=barra.set)
        self.canvas.bind("<Configure>", self._redimensionar)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 0), pady=(0, 15))
        barra.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 15), pady=(0, 15))

    def ao_exibir(self):
        self.atualizar()

    def rolar(self, unidades):
        self.canvas.yview_scroll(unidades, "units")

    # --- dados ---
    def atualizar(self):
        if not modelos.tem_chave():
            self._mensagem(t("models.sem_chave"))
            return
        self.lista = modelos.listar()
        if not self.lista:
            self._mensagem(t("models.sem_teste"))
            return
        self._desenhar(forcar=True)

    def _benchmark(self):
        if not modelos.tem_chave():
            self.app.toast(t("models.toast_sem_chave"))
            return
        if acoes.executar_benchmark_modelos(
                ao_concluir=lambda _: (self.app.toast(t("models.toast_benchmark_ok")), self.atualizar()),
                ao_falhar=lambda e: self.app.toast(t("models.toast_benchmark_erro"))):
            self.app.toast(t("models.toast_benchmark_inicio"))

    def _mudar_modo(self):
        modelos.definir_modo(self.var_modo.get())
        self.app.toast(t("models.toast_auto") if self.var_modo.get() == modelos.MODO_AUTOMATICO else t("models.toast_manual"))
        self.atualizar()

    def _mover(self, indice, delta):
        if modelos.mover(indice, delta):
            self.atualizar()

    def _principal(self, indice):
        nome = modelos.tornar_principal(indice)
        if nome:
            self.app.toast(t("models.toast_principal", nome=nome))
            self.atualizar()

    # --- desenho ---
    def _mensagem(self, texto):
        for widget in self.interno.winfo_children():
            widget.destroy()
        tk.Label(self.interno, text=texto, bg=tema.FUNDO, fg=tema.SUAVE, font=("Segoe UI", 10),
                 justify="center", pady=40).pack(fill=tk.BOTH, expand=True)

    def _redimensionar(self, evento):
        self.canvas.itemconfig(self._janela, width=evento.width)
        if self.lista:
            self._desenhar()

    def _desenhar(self, forcar=False):
        largura = self.canvas.winfo_width() - 15
        colunas = max(1, (largura if largura >= 100 else 800) // LARGURA_CARTAO)
        if colunas == self._colunas and not forcar:
            return
        self._colunas = colunas
        for widget in self.interno.winfo_children():
            widget.destroy()
        for c in range(colunas):
            self.interno.columnconfigure(c, weight=1, minsize=LARGURA_CARTAO)
        for i, modelo in enumerate(self.lista):
            self._cartao(modelo, i, i // colunas, i % colunas)

    def _cartao(self, modelo, indice, linha, coluna):
        m = modelos.metricas(modelo)
        principal = indice == 0
        manual = self.var_modo.get() == modelos.MODO_MANUAL
        fundo = tema.CARTAO
        cartao = tk.Frame(self.interno, bg=fundo, highlightbackground=tema.VERDE if principal else "#2d2d2d", highlightthickness=1)
        cartao.grid(row=linha, column=coluna, sticky="nsew", padx=6, pady=6)
        tk.Frame(cartao, bg=tema.VERDE if principal else tema.VERDE_ESCURO, width=4).pack(side=tk.LEFT, fill=tk.Y)
        conteudo = tk.Frame(cartao, bg=fundo)
        conteudo.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        cabeca = tk.Frame(conteudo, bg=fundo)
        cabeca.pack(fill=tk.X)
        rank = t("models.principal") if principal else t("models.fallback", rank=indice + 1)
        tk.Label(cabeca, text=rank, bg=fundo, fg=tema.VERDE if principal else tema.SUAVE,
                 font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)
        if manual:
            caixa = tk.Frame(cabeca, bg=fundo)
            caixa.pack(side=tk.RIGHT)
            estilo = dict(bg="#252526", font=("Segoe UI", 7, "bold"), bd=0, padx=4, pady=0,
                          activebackground="#333333", activeforeground="#ffffff")
            if not principal:
                tk.Button(caixa, text="⭐ #1", fg=tema.AMARELO, command=lambda: self._principal(indice), **estilo).pack(side=tk.LEFT, padx=1)
                tk.Button(caixa, text="▲", fg="#ffffff", command=lambda: self._mover(indice, -1), **estilo).pack(side=tk.LEFT, padx=1)
            if indice < len(self.lista) - 1:
                tk.Button(caixa, text="▼", fg="#ffffff", command=lambda: self._mover(indice, 1), **estilo).pack(side=tk.LEFT, padx=1)

        tk.Label(conteudo, text=m["nome"], bg=fundo, fg="#ffffff", font=("Segoe UI", 11, "bold"), anchor="w").pack(fill=tk.X, pady=(4, 0))
        tk.Label(conteudo, text=m["id"], bg=fundo, fg="#666666", font=("Consolas", 8), anchor="w").pack(fill=tk.X, pady=(0, 8))

        grade = tk.Frame(conteudo, bg=fundo)
        grade.pack(fill=tk.X, pady=(4, 0))
        grade.columnconfigure(0, weight=1)
        grade.columnconfigure(1, weight=1)
        cor_taxa = tema.VERDE if m["taxa"] >= 80 else tema.AMARELO if m["taxa"] >= 50 else tema.VERMELHO
        metricas = [
            (t("models.tempo_medio"), f"{m['tempo']:.2f}s", tema.AZUL),
            (t("models.sucesso"), f"{m['taxa']:.0f}% ({m['sucessos']}/{m['tentativas']})", cor_taxa),
            (t("models.max_tokens"), f"{m['tokens']:,}", tema.TEXTO),
            (t("models.score"), f"{m['score']:,}", "#d97706"),
        ]
        for i, (rotulo, valor, cor) in enumerate(metricas):
            celula = tk.Frame(grade, bg=fundo)
            celula.grid(row=i // 2, column=i % 2, sticky="w", pady=2)
            tk.Label(celula, text=rotulo, bg=fundo, fg="#aaaaaa", font=("Segoe UI", 8)).pack(anchor=tk.W)
            tk.Label(celula, text=valor, bg=fundo, fg=cor, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
