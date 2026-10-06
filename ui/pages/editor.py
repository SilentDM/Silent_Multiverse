"""
Página Editor: árvore do projeto + editor de Markdown com abas, busca, formatação,
pré-visualização (sozinha ou lado a lado) e um painel lateral do documento.

Toda a lógica vive em engine.arquivos (operações de arquivo), engine.editor_session
(estado do arquivo aberto), engine.markdown_spans (destaques), engine.documento
(sumário, links quebrados, autocompletar, citado por, estado dos arquivos) e engine.acoes
(ações de IA). Aqui ficam só widgets, menus, atalhos, arrastar-e-soltar e timers.
"""
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk, messagebox, simpledialog, scrolledtext

import core.config as cfg
import core.sistema as sistema
import core.tarefas as tarefas
import engine.acoes as acoes
import engine.arquivos as arq
import engine.documento as documento
import engine.editor_session as es
import engine.markdown_spans as ms
import engine.preview_renderer as prev
import ui.theme as tema
from core.i18n import t, tc
from ui.dialogs.history import JanelaHistorico
from ui.dialogs.new_file import DialogoNovoArquivo
from ui.dialogs.quick_open import JanelaAberturaRapida
from ui.widgets import PaginaBase, cabecalho, ajuda, caixa_com_ajuda

try:
    from tkinterweb import HtmlFrame
    TEM_PREVIEW = True
except ImportError:
    TEM_PREVIEW = False

AUTOSAVE_MS = 5000
PREVIEW_MS = 700            # atraso da pré-visualização lado a lado enquanto se digita
PAINEL_MS = 900             # atraso do sumário enquanto se digita
VIGIA_MS = 2500             # intervalo da atualização automática da árvore
MAX_ABAS = 10
MODOS = ("editar", "visualizar", "lado")
CORES_TAGS = {
    "md_h1": (15, "bold", tema.VERDE), "md_h2": (13, "bold", "#34d399"), "md_h3": (12, "bold", tema.AZUL),
    "md_bold": (12, "bold", "#ffffff"), "md_italic": (12, "italic", "#cbd5e1"),
    "md_wikilink": (12, "bold underline", tema.AZUL_CLARO), "md_todo": (12, "bold", tema.LARANJA),
    "md_quote": (12, "italic", "#94a3b8"), "md_link_quebrado": (12, "bold underline", tema.VERMELHO),
}
TECLAS_NAVEGACAO = {"Up", "Down", "Left", "Right", "Return", "Tab", "Escape", "Home", "End", "Prior", "Next",
                    "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"}


class PaginaEditor(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("editor.titulo"), t("editor.subtitulo"))
        self.sessao = es.SessaoEditor()
        self.timer_autosave = None
        self._timer_preview = None
        self._timer_painel = None
        self.area_transferencia = None      # {"caminho": str, "recortar": bool}
        self.modo = "editar"
        self._arraste = None
        self._fantasma = None
        self.tamanho_fonte = 12
        self._abas = []                     # caminhos abertos em abas
        self._posicoes = {}                 # caminho -> (cursor, rolagem) ao trocar de aba
        self._assinatura = None
        self._popup = None                  # autocompletar de [[

        self.painel = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.painel.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        self._montar_arvore(self.painel)
        self._montar_editor(self.painel)
        self._montar_lateral(self.painel)
        self._montar_menus()
        self._configurar_atalhos()
        self.atualizar_arvore()
        self._atualizar_barra()
        self.after(VIGIA_MS, self._vigiar_projeto)

    # ==================================================================
    # MONTAGEM
    # ==================================================================
    def _montar_arvore(self, painel):
        quadro = ttk.LabelFrame(painel)
        painel.add(quadro, weight=1)
        busca = ttk.Frame(quadro)
        busca.pack(fill=tk.X, padx=5, pady=(5, 2))
        ttk.Label(busca, text="🔍").pack(side=tk.LEFT, padx=(2, 4))
        self.var_busca = tk.StringVar()
        entrada = ttk.Entry(busca, textvariable=self.var_busca, font=("Segoe UI", 9))
        entrada.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entrada.bind("<KeyRelease>", lambda e: self.atualizar_arvore())
        ttk.Button(busca, text="✕", width=3, command=self._limpar_busca).pack(side=tk.LEFT, padx=(2, 0))
        ttk.Button(busca, text="⟳", width=3, command=self.atualizar_arvore).pack(side=tk.LEFT, padx=(2, 0))

        self.tree = ttk.Treeview(quadro, selectmode="browse", show="tree")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        barra = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=barra.set)
        barra.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.column("#0", width=225)
        self.tree.tag_configure("rascunho", foreground=tema.SUAVE)
        self.tree.tag_configure("processando", foreground=tema.AMARELO)
        legenda = ttk.Frame(quadro)
        legenda.pack(fill=tk.X, padx=6, pady=(2, 6))
        ajuda(legenda, t("ajuda.editor.arvore")).pack(side=tk.LEFT, anchor=tk.N, padx=(0, 4))
        ttk.Label(legenda, text=t("editor.legenda_arvore"), style="Dica.TLabel", wraplength=220,
                  justify="left").pack(side=tk.LEFT, fill=tk.X)

        self.tree.bind("<<TreeviewSelect>>", self._selecionado)
        self.tree.bind("<Double-1>", self._duplo_clique)
        self.tree.bind("<Button-3>", self._menu_arvore)
        self.tree.bind("<F2>", lambda e: self._renomear_selecionado())
        self.tree.bind("<ButtonPress-1>", self._arraste_inicio)
        self.tree.bind("<B1-Motion>", self._arraste_movimento)
        self.tree.bind("<ButtonRelease-1>", self._arraste_fim)

    def _montar_editor(self, painel):
        quadro = ttk.Frame(painel)
        painel.add(quadro, weight=3)

        # --- barra principal ---
        topo = ttk.Frame(quadro)
        topo.pack(fill=tk.X, padx=5, pady=(5, 2))
        ttk.Button(topo, text="◀", width=3, style="Ferramenta.TButton", command=self._voltar).pack(side=tk.LEFT)
        ttk.Button(topo, text="▶", width=3, style="Ferramenta.TButton", command=self._avancar).pack(side=tk.LEFT, padx=(2, 8))

        ttk.Button(topo, text="☰", width=3, style="Ferramenta.TButton", command=self._alternar_lateral).pack(side=tk.RIGHT)
        ajuda(topo, t("ajuda.editor.modos")).pack(side=tk.RIGHT, padx=2)
        ttk.Button(topo, text="🌐", width=3, style="Ferramenta.TButton", command=self._abrir_no_navegador).pack(side=tk.RIGHT, padx=2)
        self.botoes_modo = {}
        for modo in reversed(MODOS):
            botao = ttk.Button(topo, text=t(f"editor.modo.{modo}"), style="Ferramenta.TButton", width=len(t(f"editor.modo.{modo}")) + 2,
                               command=lambda m=modo: self._definir_modo(m))
            botao.pack(side=tk.RIGHT)
            self.botoes_modo[modo] = botao
        self.menu_ia = tk.Menu(self, tearoff=0, bg=tema.PAINEL, fg=tema.TEXTO, activebackground=tema.VERDE_ESCURO,
                               activeforeground="white", postcommand=self._preparar_menu_ia)
        ajuda(topo, t("ajuda.editor.ia")).pack(side=tk.RIGHT, padx=(2, 8))
        ttk.Menubutton(topo, text=t("editor.btn_ia"), menu=self.menu_ia).pack(side=tk.RIGHT)
        ttk.Button(topo, text="🔎", width=4, style="Ferramenta.TButton",
                   command=lambda: self._abrir_busca(False)).pack(side=tk.RIGHT, padx=(0, 4))
        # O título vem por último: se faltar espaço, é ele que encolhe (e não os botões)
        self.lbl_titulo = ttk.Label(topo, text=t("editor.titulo_vazio"), font=("Segoe UI", 10, "bold"),
                                    foreground=tema.VERDE, anchor="w")
        self.lbl_titulo.pack(side=tk.LEFT)
        self.lbl_estado = ttk.Label(topo, text="", font=("Segoe UI", 9), foreground=tema.SUAVE)
        self.lbl_estado.pack(side=tk.LEFT, padx=(8, 10), after=self.lbl_titulo)

        # --- abas dos arquivos abertos ---
        self.barra_abas = ttk.Frame(quadro)
        self.barra_abas.pack(fill=tk.X, padx=5, pady=(2, 0))

        # --- formatação ---
        formato = ttk.Frame(quadro)
        formato.pack(fill=tk.X, padx=5, pady=(4, 2))
        botoes = [("H1", lambda: self._titulo(1)), ("H2", lambda: self._titulo(2)), ("H3", lambda: self._titulo(3)), None,
                  ("B", lambda: self._envolver("**", "**")), ("I", lambda: self._envolver("*", "*")), None,
                  ("[[ ]]", lambda: self._envolver("[[", "]]")), ("•", lambda: self._prefixo_linha("- ")),
                  ("❝", lambda: self._prefixo_linha("> ")), ("―", lambda: self._inserir("\n---\n")), None,
                  (t("editor.fmt_todo"), self._inserir_todo), (t("editor.fmt_secreto"), self._inserir_secao_secreta)]
        for item in botoes:
            if item is None:
                ttk.Separator(formato, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=2)
                continue
            texto, comando = item
            ttk.Button(formato, text=texto, style="Ferramenta.TButton", width=max(4, len(texto) + 2),
                       command=comando).pack(side=tk.LEFT, padx=1)
        ajuda(formato, t("ajuda.editor.formatacao")).pack(side=tk.LEFT, padx=(4, 0))

        # --- buscar e substituir (aparece com Ctrl+F / Ctrl+H) ---
        self.barra_busca = ttk.Frame(quadro)
        self.var_procurar, self.var_substituir = tk.StringVar(), tk.StringVar()
        ttk.Button(self.barra_busca, text="✕", width=4, style="Ferramenta.TButton", command=self._fechar_busca).pack(side=tk.RIGHT)
        ttk.Label(self.barra_busca, text="🔎").pack(side=tk.LEFT, padx=(2, 4))
        self.entrada_procurar = ttk.Entry(self.barra_busca, textvariable=self.var_procurar, width=20)
        self.entrada_procurar.pack(side=tk.LEFT)
        self.entrada_procurar.bind("<Return>", lambda e: self._procurar(1))
        self.entrada_procurar.bind("<Shift-Return>", lambda e: self._procurar(-1))
        self.entrada_procurar.bind("<Escape>", lambda e: self._fechar_busca())
        self.var_procurar.trace_add("write", lambda *_: self._marcar_ocorrencias())
        ttk.Button(self.barra_busca, text="↑", width=3, style="Ferramenta.TButton", command=lambda: self._procurar(-1)).pack(side=tk.LEFT, padx=(2, 0))
        ttk.Button(self.barra_busca, text="↓", width=3, style="Ferramenta.TButton", command=lambda: self._procurar(1)).pack(side=tk.LEFT)
        self.lbl_ocorrencias = ttk.Label(self.barra_busca, text="", style="Dica.TLabel", width=14)
        self.lbl_ocorrencias.pack(side=tk.LEFT, padx=6)
        self.entrada_substituir = ttk.Entry(self.barra_busca, textvariable=self.var_substituir, width=16)
        self.entrada_substituir.pack(side=tk.LEFT, padx=(8, 2))
        self.entrada_substituir.bind("<Escape>", lambda e: self._fechar_busca())
        ttk.Button(self.barra_busca, text=t("editor.substituir"), style="Ferramenta.TButton", command=self._substituir).pack(side=tk.LEFT, padx=1)
        ttk.Button(self.barra_busca, text=t("editor.substituir_tudo"), style="Ferramenta.TButton", command=self._substituir_tudo).pack(side=tk.LEFT, padx=1)

        # --- texto e pré-visualização ---
        self.area = ttk.PanedWindow(quadro, orient=tk.HORIZONTAL)
        self.area.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2, 5))
        self.editor = scrolledtext.ScrolledText(
            self.area, wrap=tk.WORD, font=("Consolas", 12), undo=True, bg=tema.PAINEL, fg=tema.TEXTO,
            insertbackground="white", selectbackground=tema.VERDE_ESCURO, selectforeground="white", bd=0,
            highlightthickness=0, padx=8, pady=6)
        self.area.add(self.editor.frame, weight=1)
        self.editor.config(state=tk.DISABLED)
        self.html = HtmlFrame(self.area, messages_enabled=False) if TEM_PREVIEW else None
        self._configurar_tags(self.tamanho_fonte)

        self.editor.bind("<KeyRelease>", self._tecla)
        self.editor.bind("<Control-s>", self._salvar_manual)
        self.editor.bind("<Control-S>", self._salvar_manual)
        self.editor.bind("<Button-3>", self._menu_editor)
        self.editor.bind("<Button-1>", lambda e: self._fechar_autocompletar(), add="+")
        self.editor.bind("<FocusOut>", lambda e: self.after(150, self._fechar_autocompletar_se_sem_foco))
        for tecla, delta in (("<Down>", 1), ("<Up>", -1)):
            self.editor.bind(tecla, lambda e, d=delta: self._mover_autocompletar(d))
        for tecla in ("<Return>", "<Tab>"):
            self.editor.bind(tecla, self._confirmar_autocompletar)
        self.editor.bind("<Escape>", lambda e: self._fechar_autocompletar() or self._fechar_busca())
        self.editor.tag_bind("md_wikilink", "<Enter>", lambda e: self.editor.config(cursor="hand2"))
        self.editor.tag_bind("md_wikilink", "<Leave>", lambda e: self.editor.config(cursor="xterm"))
        self.editor.tag_bind("md_wikilink", "<Button-1>", self._clique_wikilink)

    def _montar_lateral(self, painel):
        self.lateral = ttk.Frame(painel)
        painel.add(self.lateral, weight=1)
        self.lateral_visivel = True
        estilo_lista = dict(bg=tema.PAINEL, fg=tema.TEXTO, font=("Segoe UI", 9), borderwidth=0, highlightthickness=0,
                            activestyle="none", selectbackground=tema.VERDE_ESCURO)
        self.listas = {}
        for chave, altura in (("sumario", 12), ("citado", 7), ("notas", 6)):
            caixa = caixa_com_ajuda(self.lateral, t(f"editor.lateral.{chave}"), t(f"ajuda.editor.{chave}"))
            caixa.pack(fill=tk.BOTH, expand=chave == "sumario", padx=(4, 0), pady=(0, 8))
            lista = tk.Listbox(caixa, height=altura, width=24, **estilo_lista)
            lista.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            lista.bind("<<ListboxSelect>>", lambda e, c=chave: self._clique_lateral(c))
            self.listas[chave] = lista
        self._dados_lateral = {"sumario": [], "citado": [], "notas": []}

    def _configurar_tags(self, tamanho):
        for tag, (rel, estilo, cor) in CORES_TAGS.items():
            tamanho_tag = tamanho + (rel - 12)
            fonte = ("Consolas", tamanho_tag) + tuple(estilo.split())
            self.editor.tag_configure(tag, font=fonte, foreground=cor)
        # Visão geral da pasta selecionada
        self.editor.tag_configure("pasta_titulo", font=("Segoe UI", tamanho + 6, "bold"), foreground=tema.VERDE,
                                  spacing3=2)
        self.editor.tag_configure("pasta_info", font=("Segoe UI", tamanho - 1), foreground=tema.SUAVE)
        self.editor.tag_configure("pasta_secao", font=("Segoe UI", tamanho + 1, "bold"), foreground=tema.VERDE,
                                  spacing1=14, spacing3=4)
        self.editor.tag_configure("pasta_numero", font=("Segoe UI", tamanho, "bold"), foreground=tema.TEXTO)
        self.editor.tag_configure("pasta_rotulo", font=("Segoe UI", tamanho - 1), foreground=tema.SUAVE)
        self.editor.tag_configure("pasta_galho", font=("Consolas", tamanho), foreground="#4a4a4a")
        self.editor.tag_configure("pasta_pasta", font=("Segoe UI", tamanho, "bold"), foreground=tema.AZUL)
        self.editor.tag_configure("pasta_arquivo", font=("Segoe UI", tamanho), foreground=tema.TEXTO)
        self.editor.tag_configure("pasta_rascunho", foreground=tema.SUAVE)
        self.editor.tag_configure("pasta_marca", font=("Segoe UI", tamanho - 1), foreground=tema.AMARELO)
        self.editor.tag_configure("pasta_vazia", font=("Segoe UI", tamanho - 1, "italic"), foreground=tema.SUAVE)
        self.editor.tag_configure("pasta_link", font=("Segoe UI", tamanho), foreground=tema.VERMELHO)
        self.editor.tag_configure("pasta_clicavel", underline=False)
        self.editor.tag_raise("pasta_rascunho")
        self.editor.tag_configure("md_todo", background="#2a1205")
        self.editor.tag_configure("busca", background="#5b4a12")
        self.editor.tag_configure("busca_atual", background=tema.AMARELO, foreground="#000000")
        self.editor.tag_raise("md_link_quebrado")
        self.editor.tag_raise("busca")
        self.editor.tag_raise("busca_atual")

    def _montar_menus(self):
        opcoes = dict(tearoff=0, bg=tema.PAINEL, fg=tema.TEXTO, activebackground=tema.VERDE_ESCURO, activeforeground="white")
        self.menu_arvore = tk.Menu(self, **opcoes)
        self.menu_editor = tk.Menu(self, **opcoes)
        self.menu_editor.add_command(label=t("editor.menu_todo"), command=self._inserir_todo)
        self.menu_editor.add_command(label=t("editor.menu_secreto"), command=self._inserir_secao_secreta)
        self.menu_editor.add_separator()
        self.menu_editor.add_command(label=t("editor.menu_recortar"), command=lambda: self.editor.event_generate("<<Cut>>"))
        self.menu_editor.add_command(label=t("editor.menu_copiar"), command=lambda: self.editor.event_generate("<<Copy>>"))
        self.menu_editor.add_command(label=t("editor.menu_colar"), command=lambda: self.editor.event_generate("<<Paste>>"))
        self.menu_editor.add_separator()
        self.menu_editor.add_command(label=t("editor.menu_selecionar_tudo"), command=lambda: self.editor.tag_add("sel", "1.0", "end"))

    def _configurar_atalhos(self):
        atalhos = {
            "<Control-f>": lambda e: self._abrir_busca(False), "<Control-h>": lambda e: self._abrir_busca(True),
            "<Control-p>": lambda e: self._abertura_rapida(), "<Control-w>": lambda e: self._fechar_aba(self.sessao.arquivo_atual),
            "<Control-Tab>": lambda e: self._proxima_aba(1), "<Control-Shift-Tab>": lambda e: self._proxima_aba(-1),
            "<F3>": lambda e: self._procurar(1), "<Shift-F3>": lambda e: self._procurar(-1),
            "<Alt-Left>": lambda e: self._voltar(), "<Alt-Right>": lambda e: self._avancar(),
        }
        for widget in (self, self.editor, self.tree):
            for sequencia, funcao in atalhos.items():
                widget.bind(sequencia, lambda e, f=funcao: (f(e), "break")[1])
            try:
                widget.bind("<Button-8>", lambda e: self._voltar())
                widget.bind("<Button-9>", lambda e: self._avancar())
            except tk.TclError:
                pass
        for sequencia, funcao in {"<Control-b>": lambda: self._envolver("**", "**"),
                                  "<Control-i>": lambda: self._envolver("*", "*"),
                                  "<Control-k>": lambda: self._envolver("[[", "]]")}.items():
            self.editor.bind(sequencia, lambda e, f=funcao: (f(), "break")[1])

    def ajustar_fonte(self, tamanho):
        self.tamanho_fonte = tamanho
        self.editor.configure(font=("Consolas", tamanho))
        self._configurar_tags(tamanho)

    # ==================================================================
    # ÁRVORE (com estado dos arquivos e atualização automática)
    # ==================================================================
    def atualizar_arvore(self):
        abertas = {self.tree.item(i, "values")[0] for i in self._todos() if self.tree.item(i, "open") and self.tree.item(i, "values")}
        rolagem = self.tree.yview()[0]
        self.tree.delete(*self.tree.get_children())
        self._itens = {}
        consulta = self.var_busca.get().strip()
        permitidos = arq.buscar(consulta) if consulta else None
        raiz = arq.montar_arvore(permitidos)
        rotulo = raiz.nome + (t("editor.filtrado") if consulta else "")
        iid = self.tree.insert("", "end", text=rotulo, open=True, values=[raiz.caminho])
        self._itens[arq.absoluto(raiz.caminho)] = iid
        self._inserir_nos(iid, raiz.filhos, abertas, bool(consulta))
        self.tree.yview_moveto(rolagem)
        if self.sessao.arquivo_atual in self._itens:
            item = self._itens[self.sessao.arquivo_atual]
            self.tree.selection_set(item)
        self._assinatura = documento.assinatura_projeto()
        if self.sessao.precisa_recarregar():
            self.recarregar_arquivo(self.sessao.arquivo_atual)

    def _inserir_nos(self, pai, nos, abertas, abrir_tudo):
        for no in nos:
            if no.pasta:
                texto, tags = "📁 " + no.nome, ()
            else:
                estado = documento.estado(no.caminho)
                marcas = "".join(m for chave, m in (("segredo", " 🤫"), ("rascunho", " ✎"), ("todo", " ⏳"),
                                                    ("notas", " 🗒")) if estado[chave])
                processando = acoes.arquivo_em_processamento(no.caminho)
                texto = "📄 " + no.nome + marcas + (" ⚙" if processando else "")
                tags = ("processando",) if processando else ("rascunho",) if estado["rascunho"] else ()
            iid = self.tree.insert(pai, "end", text=texto, values=[no.caminho], tags=tags,
                                   open=abrir_tudo or no.caminho in abertas)
            self._itens[arq.absoluto(no.caminho)] = iid
            if no.filhos:
                self._inserir_nos(iid, no.filhos, abertas, abrir_tudo)

    def _vigiar_projeto(self):
        """Atualiza a árvore sozinha quando algo muda na pasta (outro programa, a IA, o Obsidian...)."""
        try:
            if self._arraste is None and self.winfo_ismapped():
                if documento.assinatura_projeto() != self._assinatura:
                    self.atualizar_arvore()
        except Exception:
            pass
        self.after(VIGIA_MS, self._vigiar_projeto)

    def _todos(self, pai=""):
        for iid in self.tree.get_children(pai):
            yield iid
            yield from self._todos(iid)

    def _limpar_busca(self):
        self.var_busca.set("")
        self.atualizar_arvore()

    def _caminho_item(self, iid):
        valores = self.tree.item(iid, "values")
        return valores[0] if valores else None

    def selecionar_caminho(self, caminho):
        item = self._itens.get(arq.absoluto(caminho))
        if item:
            self.tree.selection_set(item)
            self.tree.see(item)

    def projeto_alterado(self):
        self.sessao.fechar()
        self._abas, self._posicoes = [], {}
        documento.invalidar()
        self._mostrar_aviso(t("editor.titulo_vazio"), "")
        self.atualizar_arvore()

    # ==================================================================
    # ABRIR / SALVAR
    # ==================================================================
    def _mostrar_aviso(self, titulo, texto, cor=tema.SUAVE):
        """Editor bloqueado exibindo uma mensagem (arquivo em processamento, pasta selecionada...)."""
        self.lbl_titulo.config(text=titulo, foreground=cor)
        self.editor.config(state=tk.NORMAL)
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", texto)
        self.editor.config(state=tk.DISABLED)
        self.app.atualizar_estatisticas(None)
        self._atualizar_barra()
        self._atualizar_lateral()

    # ------------------------------------------------------------------
    # VISÃO GERAL DA PASTA SELECIONADA (gerada na hora, sem IA)
    # ------------------------------------------------------------------
    def _mostrar_pasta(self, caminho):
        resumo = documento.resumo_pasta(caminho)
        self._mostrar_aviso(t("editor.diretorio", nome=arq.nome(caminho)), "")
        self._caminhos_pasta = []
        ed = self.editor
        ed.config(state=tk.NORMAL)

        def escrever(texto, *tags):
            ed.insert(tk.END, texto, tags)

        def clicavel(texto, caminho_alvo, *tags):
            self._caminhos_pasta.append(caminho_alvo)
            escrever(texto, *tags, "pasta_clicavel", f"pasta_abrir_{len(self._caminhos_pasta) - 1}")

        escrever(f"📁 {resumo['nome']}\n", "pasta_titulo")
        escrever(f"{resumo['relativo'] or t('editor.pasta.raiz')}\n", "pasta_info")

        totais, estados = resumo["totais"], resumo["estados"]
        escrever(t("editor.pasta.numeros") + "\n", "pasta_secao")
        numeros = [(totais["arquivos"], "arquivos"), (totais["subpastas"], "subpastas"),
                   (self._milhar(totais["palavras"]), "palavras"), ("~" + self._milhar(totais["tokens"]), "tokens")]
        if totais["imagens"]:
            numeros.append((totais["imagens"], "imagens"))
        for i, (valor, rotulo) in enumerate(numeros):
            escrever(("    " if i else "") + str(valor), "pasta_numero")
            escrever(f" {t('editor.pasta.' + rotulo)}", "pasta_rotulo")
        escrever("\n")
        marcas = [(estados["segredo"], "🤫", "segredo"), (estados["rascunho"], "✎", "rascunho"),
                  (estados["todo"], "⏳", "todo"), (estados["notas"], "🗒", "notas")]
        marcas = [(n, icone, chave) for n, icone, chave in marcas if n]
        for i, (n, icone, chave) in enumerate(marcas):
            escrever(("    " if i else "") + f"{icone} {n}", "pasta_numero")
            escrever(f" {t('editor.pasta.estado.' + chave)}", "pasta_rotulo")
        if marcas:
            escrever("\n")

        escrever(t("editor.pasta.conteudo") + "\n", "pasta_secao")
        itens = resumo["itens"]
        if not itens:
            escrever(t("editor.pasta.vazia") + "\n", "pasta_vazia")
        ultimos = []                              # para cada nível aberto: o item atual é o último dos irmãos?
        for i, (nivel, tipo, nome, caminho_item, estado, palavras) in enumerate(itens):
            if tipo == "mais":
                escrever(t("editor.pasta.mais") + "\n", "pasta_vazia")
                continue
            ultimo = not any(n == nivel for n, *_ in itens[i + 1:self._fim_do_grupo(itens, i)])
            del ultimos[nivel:]
            galho = "".join("   " if fim else "│  " for fim in ultimos) + ("└─ " if ultimo else "├─ ")
            ultimos.append(ultimo)
            escrever(galho, "pasta_galho")
            if tipo == "pasta":
                clicavel(f"{nome}/", caminho_item, "pasta_pasta")
            elif tipo == "vazia":
                escrever(t("editor.pasta.subpasta_vazia"), "pasta_vazia")
            else:
                tags = ("pasta_arquivo", "pasta_rascunho") if estado["rascunho"] else ("pasta_arquivo",)
                clicavel(nome, caminho_item, *tags)
                sinais = "".join(s for chave, s in (("segredo", " 🤫"), ("rascunho", " ✎"), ("todo", " ⏳"),
                                                    ("notas", " 🗒")) if estado[chave])
                if sinais:
                    escrever(sinais, "pasta_marca")
                escrever(f"   {t('editor.pasta.n_palavras', n=self._milhar(palavras))}", "pasta_rotulo")
            escrever("\n")

        if resumo["recentes"]:
            escrever(t("editor.pasta.recentes") + "\n", "pasta_secao")
            for caminho_item, nome, quando in resumo["recentes"]:
                escrever("•  ", "pasta_galho")
                clicavel(nome, caminho_item, "pasta_arquivo")
                escrever(f"   {datetime.fromtimestamp(quando).strftime(t('editor.pasta.formato_data'))}\n", "pasta_rotulo")

        if resumo["sem_arquivo"]:
            escrever(t("editor.pasta.sem_arquivo") + "\n", "pasta_secao")
            escrever(t("editor.pasta.sem_arquivo_dica") + "\n", "pasta_rotulo")
            escrever("   ".join(f"[[{nome}]]" for nome in resumo["sem_arquivo"][:40]) + "\n", "pasta_link")

        escrever("\n" + t("editor.pasta.dica") + "\n", "pasta_info")
        ed.tag_bind("pasta_clicavel", "<Button-1>", self._clique_pasta)
        ed.tag_bind("pasta_clicavel", "<Enter>", lambda e: ed.config(cursor="hand2"))
        ed.tag_bind("pasta_clicavel", "<Leave>", lambda e: ed.config(cursor="xterm"))
        ed.config(state=tk.DISABLED)

    @staticmethod
    def _milhar(numero):
        return f"{numero:,}".replace(",", t("editor.pasta.sep_milhar"))

    @staticmethod
    def _fim_do_grupo(itens, i):
        """Índice onde termina o grupo de irmãos do item i (o próximo item de nível menor)."""
        nivel = itens[i][0]
        for j in range(i + 1, len(itens)):
            if itens[j][0] < nivel:
                return j
        return len(itens)

    def _clique_pasta(self, evento):
        indice = self.editor.index(f"@{evento.x},{evento.y}")
        for tag in self.editor.tag_names(indice):
            if tag.startswith("pasta_abrir_"):
                caminho = self._caminhos_pasta[int(tag[len("pasta_abrir_"):])]
                self.selecionar_caminho(caminho)
                self.ir_para(caminho)
                return "break"

    def _exibir_texto(self, texto):
        self.editor.config(state=tk.NORMAL)
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", texto)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self._destacar()
        self.app.atualizar_estatisticas(ms.estatisticas(texto))
        self.lbl_titulo.config(text=self.sessao.nome_atual, foreground=tema.VERDE)
        self._adicionar_aba(self.sessao.arquivo_atual)
        posicao = self._posicoes.get(self.sessao.arquivo_atual)
        if posicao:
            self.editor.mark_set("insert", posicao[0])
            self.editor.yview_moveto(posicao[1])
        self._atualizar_barra()
        self._atualizar_preview()
        self._atualizar_lateral(com_citacoes=True)

    def _texto_editor(self):
        return self.editor.get("1.0", tk.END)

    def _cancelar_autosave(self):
        if self.timer_autosave:
            self.after_cancel(self.timer_autosave)
            self.timer_autosave = None

    def salvar_agora(self):
        """Salva o arquivo aberto (se possível). Devolve o resultado de SessaoEditor.salvar."""
        self._cancelar_autosave()
        if not self.sessao.arquivo_atual or str(self.editor.cget("state")) == "disabled":
            return None
        resultado = self.sessao.salvar(self._texto_editor())
        mensagem = es.mensagem_salvamento(resultado, self.sessao.nome_atual)
        if mensagem:
            self.app.paginas["log"].adicionar(mensagem)
        if resultado == es.ALTERADO_EXTERNAMENTE:
            self.app.toast(t("editor.toast_atualizado_ia", nome=self.sessao.nome_atual))
        if resultado == es.SALVO:
            self.editor.edit_modified(False)
        self._atualizar_estado_salvo()
        return resultado

    def _guardar_posicao(self):
        if self.sessao.arquivo_atual and str(self.editor.cget("state")) != "disabled":
            self._posicoes[self.sessao.arquivo_atual] = (self.editor.index("insert"), self.editor.yview()[0])

    def _abrir(self, caminho, registrar_historico=True):
        if self.sessao.em_processamento(caminho):
            self.sessao.fechar()
            self._mostrar_aviso(t("editor.bloqueado_titulo"), t("editor.bloqueado_texto", nome=arq.nome(caminho)), tema.AMARELO)
            return
        try:
            texto = self.sessao.abrir(caminho, registrar_historico)
        except arq.ErroOperacao as e:
            self.app.toast(str(e))
            return
        self._exibir_texto(texto)

    def ir_para(self, caminho, registrar_historico=True):
        """Abre um arquivo vindo da árvore, das abas, da abertura rápida, do painel lateral ou de um link."""
        if not caminho or (self.sessao.eh_atual(caminho) and not self.sessao.em_processamento(caminho)):
            return
        anterior = self.sessao.arquivo_atual
        editado = bool(self.editor.edit_modified())
        self._guardar_posicao()
        salvo = self.salvar_agora() == es.SALVO if anterior else False
        if arq.eh_arquivo(caminho):
            self._abrir(caminho, registrar_historico)
            self.selecionar_caminho(caminho)
        else:
            self.sessao.fechar()
            self._mostrar_pasta(caminho)
        # Expander automático do arquivo que acabou de ser editado e deixado
        if anterior and salvo and editado and acoes.deve_auto_expandir(anterior):
            self._executar_ia("expander", anterior, "")

    def abrir_arquivo(self, caminho):
        """Abre um arquivo no editor a partir de outra página (ex.: o Cânone do WorldBuilder)."""
        if not caminho or not arq.eh_arquivo(caminho):
            return
        self.atualizar_arvore()
        self.ir_para(caminho)

    def _historico(self, caminho):
        """Janela com as versões anteriores do arquivo; ao restaurar, o editor relê o arquivo."""
        if self.sessao.eh_atual(caminho):
            self.salvar_agora()
        JanelaHistorico(self.app.root, caminho, toast_callback=self.app.toast,
                        ao_restaurar=lambda c: self.recarregar_arquivo(c) if self.sessao.eh_atual(c) else None)

    def recarregar_arquivo(self, caminho):
        """Relê o arquivo do disco (após a IA alterá-lo) e o exibe."""
        if not caminho or not arq.eh_arquivo(caminho):
            return
        self._cancelar_autosave()
        self._guardar_posicao()
        self._abrir(caminho, registrar_historico=False)
        self.selecionar_caminho(caminho)

    def _selecionado(self, _evento=None):
        selecao = self.tree.selection()
        if selecao:
            self.ir_para(self._caminho_item(selecao[0]))

    def _tecla(self, evento=None):
        if str(self.editor.cget("state")) == "disabled":
            return
        self._destacar()
        self.app.atualizar_estatisticas(ms.estatisticas(self._texto_editor()))
        self._cancelar_autosave()
        self.timer_autosave = self.after(AUTOSAVE_MS, self._autosave)
        self._atualizar_estado_salvo()
        if self.modo == "lado":
            self._agendar("_timer_preview", PREVIEW_MS, self._atualizar_preview)
        self._agendar("_timer_painel", PAINEL_MS, self._atualizar_lateral)
        if evento is None or getattr(evento, "keysym", "") not in TECLAS_NAVEGACAO:
            self._verificar_autocompletar()

    def _agendar(self, atributo, atraso, funcao):
        if getattr(self, atributo):
            self.after_cancel(getattr(self, atributo))
        setattr(self, atributo, self.after(atraso, lambda: (setattr(self, atributo, None), funcao())))

    def _autosave(self):
        self.timer_autosave = None
        if self.salvar_agora() == es.ALTERADO_EXTERNAMENTE:
            self.recarregar_arquivo(self.sessao.arquivo_atual)

    def _salvar_manual(self, _evento=None):
        caminho = self.sessao.arquivo_atual
        if not caminho or str(self.editor.cget("state")) == "disabled":
            return "break"
        resultado = self.salvar_agora()
        if resultado == es.SALVO:
            self.app.toast(t("editor.toast_salvo", nome=arq.nome(caminho)))
            if acoes.deve_auto_expandir(caminho):
                self._executar_ia("expander", caminho, "")
        elif resultado == es.ALTERADO_EXTERNAMENTE:
            self.recarregar_arquivo(caminho)
        return "break"

    def _destacar(self):
        for tag in ms.TAGS + ["md_link_quebrado"]:
            self.editor.tag_remove(tag, "1.0", tk.END)
        texto = self._texto_editor()
        for tag, inicio, fim in ms.destaques(texto):
            self.editor.tag_add(tag, f"1.0 + {inicio} chars", f"1.0 + {fim} chars")
        for inicio, fim in documento.links_quebrados(texto):
            self.editor.tag_add("md_link_quebrado", f"1.0 + {inicio} chars", f"1.0 + {fim} chars")

    # ==================================================================
    # BARRA, ESTADO DE SALVAMENTO E MODOS
    # ==================================================================
    def _atualizar_barra(self):
        for modo, botao in self.botoes_modo.items():
            botao.configure(style="FerramentaAtiva.TButton" if modo == self.modo else "Ferramenta.TButton")
        self._atualizar_estado_salvo()
        self._desenhar_abas()

    def _atualizar_estado_salvo(self):
        if not self.sessao.arquivo_atual or str(self.editor.cget("state")) == "disabled":
            self.lbl_estado.config(text="")
        elif self.editor.edit_modified():
            self.lbl_estado.config(text=t("editor.estado_alterado"), foreground=tema.AMARELO)
        else:
            self.lbl_estado.config(text=t("editor.estado_salvo"), foreground=tema.SUAVE)

    def _definir_modo(self, modo):
        if modo != "editar" and self.html is None:
            self.app.toast(t("editor.sem_tkinterweb"))
            return
        if modo == "visualizar":
            self.salvar_agora()
        self.modo = modo
        paineis = [str(p) for p in self.area.panes()]
        quer = {"editar": [self.editor.frame], "visualizar": [self.html], "lado": [self.editor.frame, self.html]}[modo]
        for widget in (self.editor.frame, self.html):
            if widget is not None and str(widget) in paineis and widget not in quer:
                self.area.forget(widget)
        for widget in quer:
            if str(widget) not in [str(p) for p in self.area.panes()]:
                self.area.add(widget, weight=1)
        self._atualizar_barra()
        self._atualizar_preview()
        if modo != "visualizar":
            self.editor.focus_set()

    def _atualizar_preview(self):
        if self.html is None or self.modo == "editar":
            return
        if not self.sessao.arquivo_atual:
            self.html.load_html("")
            return
        self.html.load_html(prev.gerar_html_string_preview(self._texto_editor().rstrip("\n"), Path(self.sessao.arquivo_atual)))

    def _abrir_no_navegador(self):
        if not self.sessao.arquivo_atual:
            self.app.toast(t("editor.selecione_arquivo"))
            return
        self.salvar_agora()
        try:
            sistema.abrir_no_sistema(prev.gerar_preview_documento(Path(self.sessao.arquivo_atual)))
        except Exception as e:
            self.app.toast(t("editor.erro_preview", erro=e))

    # ==================================================================
    # ABAS
    # ==================================================================
    def _adicionar_aba(self, caminho):
        if not caminho or caminho in self._abas:
            self._desenhar_abas()
            return
        self._abas.append(caminho)
        while len(self._abas) > MAX_ABAS:
            antiga = next(c for c in self._abas if c != caminho)
            self._abas.remove(antiga)
            self._posicoes.pop(antiga, None)
        self._desenhar_abas()

    def _desenhar_abas(self):
        for filho in self.barra_abas.winfo_children():
            filho.destroy()
        for caminho in self._abas:
            atual = self.sessao.eh_atual(caminho)
            aba = tk.Frame(self.barra_abas, bg=tema.PAINEL if atual else tema.FUNDO,
                           highlightthickness=1, highlightbackground=tema.VERDE if atual else "#2d2d2d")
            aba.pack(side=tk.LEFT, padx=(0, 2))
            rotulo = tk.Label(aba, text=arq.nome(caminho).removesuffix(".md"), bg=aba["bg"], cursor="hand2",
                              fg=tema.VERDE if atual else tema.TEXTO, font=("Segoe UI", 9, "bold" if atual else "normal"),
                              padx=8, pady=3)
            rotulo.pack(side=tk.LEFT)
            fechar = tk.Label(aba, text="×", bg=aba["bg"], fg=tema.SUAVE, cursor="hand2", font=("Segoe UI", 10), padx=4)
            fechar.pack(side=tk.LEFT)
            rotulo.bind("<Button-1>", lambda e, c=caminho: self.ir_para(c))
            rotulo.bind("<Button-2>", lambda e, c=caminho: self._fechar_aba(c))
            fechar.bind("<Button-1>", lambda e, c=caminho: self._fechar_aba(c))

    def _fechar_aba(self, caminho):
        if not caminho or caminho not in self._abas:
            return
        indice = self._abas.index(caminho)
        era_atual = self.sessao.eh_atual(caminho)
        if era_atual:
            self.salvar_agora()
        self._abas.remove(caminho)
        self._posicoes.pop(caminho, None)
        if era_atual:
            if self._abas:
                self.sessao.fechar()
                self.ir_para(self._abas[min(indice, len(self._abas) - 1)], registrar_historico=False)
            else:
                self._cancelar_autosave()
                self.sessao.fechar()
                self._mostrar_aviso(t("editor.titulo_vazio"), "")
        self._desenhar_abas()

    def _proxima_aba(self, delta):
        if len(self._abas) < 2 or self.sessao.arquivo_atual not in self._abas:
            return
        indice = (self._abas.index(self.sessao.arquivo_atual) + delta) % len(self._abas)
        self.ir_para(self._abas[indice])

    def _remapear_abas(self, origem, destino):
        self._abas = [arq.remapear_caminho(c, origem, destino) for c in self._abas]
        self._posicoes = {arq.remapear_caminho(c, origem, destino): p for c, p in self._posicoes.items()}

    # ==================================================================
    # PAINEL LATERAL (Sumário · Citado por · Notas do Mestre)
    # ==================================================================
    def _alternar_lateral(self):
        if self.lateral_visivel:
            self.painel.forget(self.lateral)
        else:
            self.painel.add(self.lateral, weight=1)
            self._atualizar_lateral(com_citacoes=True)
        self.lateral_visivel = not self.lateral_visivel

    def _atualizar_lateral(self, com_citacoes=False):
        if not self.lateral_visivel:
            return
        caminho = self.sessao.arquivo_atual
        aberto = bool(caminho) and str(self.editor.cget("state")) != "disabled"
        sumario = documento.sumario(self._texto_editor()) if aberto else []
        self._dados_lateral["sumario"] = sumario
        self._preencher_lista("sumario", ["   " * (nivel - 1) + titulo for nivel, titulo, _ in sumario],
                              t("editor.lateral.vazio_sumario"))
        if not com_citacoes:
            return
        notas = acoes.notas_do_arquivo(caminho) if aberto else []
        self._dados_lateral["notas"] = notas
        self._preencher_lista("notas", [n["titulo"] for n in notas], t("editor.lateral.vazio_notas"))
        self._dados_lateral["citado"] = []
        self._preencher_lista("citado", [], t("editor.lateral.carregando") if aberto else t("editor.lateral.vazio_citado"))
        if aberto:
            tarefas.executar_em_segundo_plano(documento.citado_por, caminho,
                                              ao_concluir=lambda lista, c=caminho: self._mostrar_citacoes(c, lista))

    def _mostrar_citacoes(self, caminho, lista):
        if not self.sessao.eh_atual(caminho):
            return
        self._dados_lateral["citado"] = lista
        self._preencher_lista("citado", [Path(c).stem for c in lista], t("editor.lateral.vazio_citado"))

    def _preencher_lista(self, chave, itens, vazio):
        lista = self.listas[chave]
        lista.delete(0, tk.END)
        for item in itens:
            lista.insert(tk.END, item)
        if not itens:
            lista.insert(tk.END, vazio)
            lista.itemconfig(0, foreground=tema.SUAVE)

    def _clique_lateral(self, chave):
        selecao = self.listas[chave].curselection()
        dados = self._dados_lateral[chave]
        if not selecao or selecao[0] >= len(dados):
            return
        item = dados[selecao[0]]
        if chave == "sumario":
            self._ir_para_linha(item[2])
        elif chave == "citado":
            self.ir_para(item)
        else:
            posicao = self.editor.search("### " + item["titulo"], "1.0", tk.END)
            if posicao:
                self._ir_para_linha(int(posicao.split(".")[0]))

    def _ir_para_linha(self, linha):
        if self.modo == "visualizar":
            self._definir_modo("editar")
        self.editor.mark_set("insert", f"{linha}.0")
        self.editor.see(f"{linha}.0")
        self.editor.yview(f"{linha}.0")
        self.editor.focus_set()

    # ==================================================================
    # BUSCAR E SUBSTITUIR
    # ==================================================================
    def _abrir_busca(self, substituir):
        if not self.barra_busca.winfo_ismapped():
            self.barra_busca.pack(fill=tk.X, padx=5, pady=(2, 2), before=self.area)
        selecao = self.editor.tag_ranges("sel")
        if selecao:
            self.var_procurar.set(self.editor.get(*selecao)[:80])
        (self.entrada_substituir if substituir and self.var_procurar.get() else self.entrada_procurar).focus_set()
        self.entrada_procurar.select_range(0, tk.END)
        self._marcar_ocorrencias()

    def _fechar_busca(self):
        if self.barra_busca.winfo_ismapped():
            self.barra_busca.pack_forget()
            self.editor.tag_remove("busca", "1.0", tk.END)
            self.editor.tag_remove("busca_atual", "1.0", tk.END)
            self.editor.focus_set()

    def _marcar_ocorrencias(self):
        self.editor.tag_remove("busca", "1.0", tk.END)
        self.editor.tag_remove("busca_atual", "1.0", tk.END)
        termo = self.var_procurar.get()
        if not termo:
            self.lbl_ocorrencias.config(text="")
            return 0
        total, inicio = 0, "1.0"
        while True:
            posicao = self.editor.search(termo, inicio, tk.END, nocase=True)
            if not posicao:
                break
            fim = f"{posicao}+{len(termo)}c"
            self.editor.tag_add("busca", posicao, fim)
            inicio, total = fim, total + 1
        self.lbl_ocorrencias.config(text=t("editor.ocorrencias", total=total))
        return total

    def _procurar(self, direcao):
        termo = self.var_procurar.get()
        if not termo:
            self._abrir_busca(False)
            return
        if direcao > 0:
            inicio = self.editor.index("busca_atual.last") if self.editor.tag_ranges("busca_atual") else self.editor.index("insert")
            posicao = self.editor.search(termo, inicio, tk.END, nocase=True) or self.editor.search(termo, "1.0", tk.END, nocase=True)
        else:
            inicio = self.editor.index("busca_atual.first") if self.editor.tag_ranges("busca_atual") else self.editor.index("insert")
            posicao = self.editor.search(termo, inicio, "1.0", nocase=True, backwards=True) or \
                self.editor.search(termo, tk.END, "1.0", nocase=True, backwards=True)
        self.editor.tag_remove("busca_atual", "1.0", tk.END)
        if posicao:
            fim = f"{posicao}+{len(termo)}c"
            self.editor.tag_add("busca_atual", posicao, fim)
            self.editor.mark_set("insert", fim)
            self.editor.see(posicao)

    def _substituir(self):
        if str(self.editor.cget("state")) == "disabled" or not self.var_procurar.get():
            return
        if not self.editor.tag_ranges("busca_atual"):
            self._procurar(1)
            return
        self.editor.delete("busca_atual.first", "busca_atual.last")
        self.editor.insert("insert", self.var_substituir.get())
        self._tecla()
        self._marcar_ocorrencias()
        self._procurar(1)

    def _substituir_tudo(self):
        if str(self.editor.cget("state")) == "disabled":
            return
        termo, novo = self.var_procurar.get(), self.var_substituir.get()
        if not termo:
            return
        total, inicio = 0, "1.0"
        self.editor.edit_separator()
        while True:
            posicao = self.editor.search(termo, inicio, tk.END, nocase=True)
            if not posicao:
                break
            self.editor.delete(posicao, f"{posicao}+{len(termo)}c")
            self.editor.insert(posicao, novo)
            inicio, total = f"{posicao}+{len(novo)}c", total + 1
        self.editor.edit_separator()
        self._tecla()
        self._marcar_ocorrencias()
        self.app.toast(t("editor.toast_substituidos", total=total))

    # ==================================================================
    # FORMATAÇÃO
    # ==================================================================
    def _pode_editar(self):
        return str(self.editor.cget("state")) != "disabled" and self.modo != "visualizar"

    def _envolver(self, antes, depois):
        if not self._pode_editar():
            return
        selecao = self.editor.tag_ranges("sel")
        if selecao:
            texto = self.editor.get(*selecao)
            self.editor.delete(*selecao)
            self.editor.insert(selecao[0], f"{antes}{texto}{depois}")
        else:
            self.editor.insert("insert", antes + depois)
            self.editor.mark_set("insert", f"insert-{len(depois)}c")
        self.editor.focus_set()
        self._tecla()

    def _prefixo_linha(self, prefixo):
        if not self._pode_editar():
            return
        inicio = self.editor.index("insert linestart")
        if self.editor.get(inicio, f"{inicio}+{len(prefixo)}c") != prefixo:
            self.editor.insert(inicio, prefixo)
        self.editor.focus_set()
        self._tecla()

    def _titulo(self, nivel):
        if not self._pode_editar():
            return
        inicio = self.editor.index("insert linestart")
        linha = self.editor.get(inicio, f"{inicio} lineend")
        sem_cerquilhas = linha.lstrip("#").lstrip()
        self.editor.delete(inicio, f"{inicio} lineend")
        self.editor.insert(inicio, "#" * nivel + " " + sem_cerquilhas)
        self.editor.focus_set()
        self._tecla()

    def _inserir(self, texto):
        if self._pode_editar():
            self.editor.insert("insert", texto)
            self.editor.focus_set()
            self._tecla()

    def _inserir_todo(self):
        if self._pode_editar():
            self._inserir("<-- TODO: ")
            self.app.toast(t("editor.toast_todo"))

    def _inserir_secao_secreta(self):
        if self._pode_editar():
            self._inserir(f"\n### {t('editor.fmt_titulo_secreto')} {tc('marcador.secao_secreta')}\n")

    # ==================================================================
    # AUTOCOMPLETAR DE [[LINKS]]
    # ==================================================================
    def _prefixo_link(self):
        """Texto digitado depois de um [[ ainda aberto na linha atual (ou None)."""
        antes = self.editor.get("insert linestart", "insert")
        abre = antes.rfind("[[")
        if abre < 0 or "]]" in antes[abre:] or "|" in antes[abre:]:
            return None
        return antes[abre + 2:]

    def _verificar_autocompletar(self):
        prefixo = self._prefixo_link()
        if prefixo is None or len(prefixo) > 60:
            self._fechar_autocompletar()
            return
        sugestoes = documento.sugerir_links(prefixo)
        if not sugestoes:
            self._fechar_autocompletar()
            return
        if self._popup is None:
            self._popup = tk.Toplevel(self)
            self._popup.overrideredirect(True)
            self._popup.attributes("-topmost", True)
            self._lista_popup = tk.Listbox(self._popup, bg="#252526", fg=tema.TEXTO, font=("Segoe UI", 10), height=8,
                                           borderwidth=1, relief="solid", highlightthickness=0, activestyle="none",
                                           selectbackground=tema.VERDE_ESCURO)
            self._lista_popup.pack()
            self._lista_popup.bind("<Double-1>", lambda e: self._confirmar_autocompletar())
        self._lista_popup.delete(0, tk.END)
        for nome in sugestoes:
            self._lista_popup.insert(tk.END, nome)
        self._lista_popup.selection_set(0)
        caixa = self.editor.bbox("insert")
        if caixa:
            x = self.editor.winfo_rootx() + caixa[0]
            y = self.editor.winfo_rooty() + caixa[1] + caixa[3] + 2
            self._popup.geometry(f"+{x}+{y}")

    def _fechar_autocompletar(self):
        if self._popup is not None:
            self._popup.destroy()
            self._popup = None

    def _fechar_autocompletar_se_sem_foco(self):
        if self.focus_get() is not self.editor:
            self._fechar_autocompletar()

    def _mover_autocompletar(self, delta):
        if self._popup is None:
            return None
        atual = self._lista_popup.curselection()
        novo = max(0, min(self._lista_popup.size() - 1, (atual[0] if atual else 0) + delta))
        self._lista_popup.selection_clear(0, tk.END)
        self._lista_popup.selection_set(novo)
        self._lista_popup.see(novo)
        return "break"

    def _confirmar_autocompletar(self, _evento=None):
        if self._popup is None:
            return None
        selecao = self._lista_popup.curselection()
        prefixo = self._prefixo_link()
        if selecao and prefixo is not None:
            nome = self._lista_popup.get(selecao[0])
            self.editor.delete(f"insert-{len(prefixo)}c", "insert")
            fechado = self.editor.get("insert", "insert+2c") == "]]"
            self.editor.insert("insert", nome + ("" if fechado else "]]"))
            if fechado:
                self.editor.mark_set("insert", "insert+2c")
        self._fechar_autocompletar()
        self._tecla()
        return "break"

    # ==================================================================
    # NAVEGAÇÃO
    # ==================================================================
    def _voltar(self):
        self._guardar_posicao()
        self.salvar_agora()
        destino = self.sessao.voltar()
        if destino:
            self._abrir(destino, registrar_historico=False)
            self.selecionar_caminho(destino)
        else:
            self.app.toast(t("editor.inicio_historico"))
        return "break"

    def _avancar(self):
        self._guardar_posicao()
        self.salvar_agora()
        destino = self.sessao.avancar()
        if destino:
            self._abrir(destino, registrar_historico=False)
            self.selecionar_caminho(destino)
        else:
            self.app.toast(t("editor.fim_historico"))
        return "break"

    def _abertura_rapida(self):
        JanelaAberturaRapida(self.app, self.ir_para)

    def _clique_wikilink(self, evento):
        indice = self.editor.index(f"@{evento.x},{evento.y}")
        faixa = self.editor.tag_prevrange("md_wikilink", f"{indice}+1c")
        alvo = ms.alvo_wikilink(self.editor.get(*faixa)) if faixa else None
        if not alvo:
            return
        caminho = arq.resolver_wikilink(alvo)
        if caminho:
            self.ir_para(caminho)
            return
        if messagebox.askyesno(t("editor.criar_wikilink_titulo"), t("editor.criar_wikilink", alvo=alvo), parent=self):
            pasta = arq.pasta_de(self.sessao.arquivo_atual) if self.sessao.arquivo_atual else acoes.projeto_ativo()[1]
            novo = arq.criar_por_wikilink(alvo, pasta, self.sessao.nome_atual)
            documento.invalidar()
            self.atualizar_arvore()
            self._destacar()
            self.ir_para(novo)
            self.app.toast(t("editor.toast_criado", nome=arq.nome(novo)))

    # ==================================================================
    # MENUS
    # ==================================================================
    def _preparar_menu_ia(self):
        """Menu ✨ IA da barra: as mesmas ações do botão direito, para o arquivo aberto."""
        m = self.menu_ia
        m.delete(0, tk.END)
        caminho = self.sessao.arquivo_atual
        estado = tk.NORMAL if caminho and arq.eh_markdown(caminho) else tk.DISABLED
        itens = (("editor.menu_melhorar", lambda: self._acao_ia("melhorar", caminho)),
                 ("editor.menu_aventura", lambda: self._acao_ia("aventura", caminho)),
                 ("editor.menu_conhecimento", lambda: self._acao_ia("conhecimento", caminho)),
                 ("editor.menu_ficha", lambda: self._acao_ia("ficha", caminho)),
                 ("editor.menu_conselho", lambda: self._enviar_conselho(caminho)),
                 None,                                          # separador
                 ("editor.menu_perguntar_silent", lambda: self._perguntar_silent(caminho)),
                 ("editor.menu_historico", lambda: self._historico(caminho)))
        for item in itens:
            if item is None:
                m.add_separator()
            else:
                rotulo, comando = item
                m.add_command(label=t(rotulo), command=comando, state=estado)

    def _menu_editor(self, evento):
        if str(self.editor.cget("state")) == "disabled":
            return
        self.editor.focus_set()
        if not self.editor.tag_ranges("sel"):
            self.editor.mark_set("insert", f"@{evento.x},{evento.y}")
        self.menu_editor.post(evento.x_root, evento.y_root)

    def _menu_arvore(self, evento):
        iid = self.tree.identify_row(evento.y)
        if not iid:
            return
        self.tree.selection_set(iid)
        caminho = self._caminho_item(iid)
        if not caminho:
            return
        m = self.menu_arvore
        m.delete(0, tk.END)
        eh_md = arq.eh_markdown(caminho)
        if eh_md:
            m.add_command(label=t("editor.menu_perguntar_silent"), command=lambda: self._perguntar_silent(caminho))
            m.add_separator()
        if arq.eh_pasta(caminho):
            m.add_command(label=t("editor.menu_novo_arquivo"), command=lambda: self._novo_arquivo(caminho))
            m.add_command(label=t("editor.menu_nova_pasta"), command=lambda: self._nova_pasta(caminho))
            m.add_separator()
        m.add_command(label=t("editor.menu_excluir"), command=lambda: self._excluir(caminho))
        m.add_command(label=t("editor.menu_renomear"), command=lambda: self._renomear(caminho))
        m.add_separator()
        m.add_command(label=t("editor.menu_copiar_item"), command=lambda: self._copiar(caminho, False))
        m.add_command(label=t("editor.menu_recortar_item"), command=lambda: self._copiar(caminho, True))
        pode_colar = bool(self.area_transferencia and arq.existe(self.area_transferencia["caminho"]))
        m.add_command(label=t("editor.menu_colar_item"), command=lambda: self._colar(caminho),
                      state=tk.NORMAL if pode_colar else tk.DISABLED)
        m.add_command(label=t("editor.menu_duplicar"), command=lambda: self._duplicar(caminho))
        m.add_separator()
        m.add_command(label=t("editor.menu_revelar"), command=lambda: sistema.revelar_no_explorer(caminho))
        if eh_md:
            m.add_separator()
            m.add_command(label=t("editor.menu_melhorar"), command=lambda: self._acao_ia("melhorar", caminho))
            m.add_command(label=t("editor.menu_aventura"), command=lambda: self._acao_ia("aventura", caminho))
            m.add_command(label=t("editor.menu_conhecimento"), command=lambda: self._acao_ia("conhecimento", caminho))
            m.add_command(label=t("editor.menu_ficha"), command=lambda: self._acao_ia("ficha", caminho))
            m.add_command(label=t("editor.menu_conselho"), command=lambda: self._enviar_conselho(caminho))
            m.add_separator()
            m.add_command(label=t("editor.menu_historico"), command=lambda: self._historico(caminho))
        m.post(evento.x_root, evento.y_root)

    def _duplo_clique(self, _evento=None):
        selecao = self.tree.selection()
        caminho = self._caminho_item(selecao[0]) if selecao else None
        if caminho and arq.eh_arquivo(caminho):
            if self.sessao.em_processamento(caminho):
                self.app.toast(t("editor.toast_bloqueado", nome=arq.nome(caminho)))
                return
            sistema.abrir_no_sistema(caminho)

    # ==================================================================
    # OPERAÇÕES DE ARQUIVO
    # ==================================================================
    def _executar_operacao(self, funcao, *args):
        """Roda uma operação de engine.arquivos exibindo erros esperados como aviso."""
        try:
            return funcao(*args)
        except arq.ErroOperacao as e:
            messagebox.showerror(t("comum.erro"), str(e), parent=self)
        except OSError as e:
            messagebox.showerror(t("comum.erro"), t("editor.erro_operacao", erro=e), parent=self)
        return None

    def _antes_de_mover(self):
        """Salva o editor antes de mover/renomear algo (para não perder o que foi digitado)."""
        self._guardar_posicao()
        self.salvar_agora()

    def _depois_de_mover(self, origem, destino):
        self.sessao.acompanhar_movimento(origem, destino)
        self._remapear_abas(origem, destino)
        documento.invalidar()
        if self.sessao.arquivo_atual:
            self.lbl_titulo.config(text=self.sessao.nome_atual)
        self.atualizar_arvore()
        self._desenhar_abas()
        # Mantém o foco no arquivo aberto (selecionar a pasta movida fecharia o editor)
        self.selecionar_caminho(self.sessao.arquivo_atual or destino)

    def _novo_arquivo(self, pasta):
        dialogo = DialogoNovoArquivo(self, arq.listar_templates())
        if not dialogo.nome:
            return
        caminho = self._executar_operacao(arq.criar_arquivo, pasta, dialogo.nome, dialogo.template)
        if caminho:
            documento.invalidar()
            self.atualizar_arvore()
            self.ir_para(caminho)
            self.app.toast(t("editor.toast_criado", nome=arq.nome(caminho)))

    def _nova_pasta(self, pasta):
        nome = simpledialog.askstring(t("editor.nova_pasta_titulo"), t("editor.nova_pasta"), parent=self)
        if nome:
            caminho = self._executar_operacao(arq.criar_pasta, pasta, nome)
            if caminho:
                self.atualizar_arvore()
                self.selecionar_caminho(caminho)

    def _renomear_selecionado(self):
        selecao = self.tree.selection()
        if selecao and self._caminho_item(selecao[0]):
            self._renomear(self._caminho_item(selecao[0]))
        return "break"

    def _renomear(self, caminho):
        novo_nome = simpledialog.askstring(t("editor.renomear_titulo"), t("editor.renomear", nome=arq.nome(caminho)),
                                           initialvalue=arq.nome(caminho), parent=self)
        if not novo_nome:
            return
        self._antes_de_mover()
        novo = self._executar_operacao(arq.renomear, caminho, novo_nome)
        if novo and novo != caminho:
            self._depois_de_mover(caminho, novo)
            self.app.toast(t("editor.toast_renomeado", antigo=arq.nome(caminho), novo=arq.nome(novo)))

    def _excluir(self, caminho):
        if not messagebox.askyesno(t("editor.excluir_titulo"), t("editor.excluir", nome=arq.nome(caminho)), parent=self):
            return
        if arq.esta_dentro(caminho, self.sessao.arquivo_atual):
            self._cancelar_autosave()
            self.sessao.fechar()
            self._mostrar_aviso(t("editor.titulo_vazio"), "")
        self._executar_operacao(arq.excluir, caminho)
        if not arq.existe(caminho):
            self._abas = [c for c in self._abas if not arq.esta_dentro(caminho, c)]
            documento.invalidar()
            self.app.toast(t("editor.toast_excluido", nome=arq.nome(caminho)))
        self.atualizar_arvore()
        self._desenhar_abas()

    def _copiar(self, caminho, recortar):
        self.area_transferencia = {"caminho": caminho, "recortar": recortar}
        chave = "editor.toast_recortado" if recortar else "editor.toast_copiado"
        self.app.toast(t(chave, nome=arq.nome(caminho)))

    def _colar(self, alvo):
        if not self.area_transferencia:
            return
        origem, recortar = self.area_transferencia["caminho"], self.area_transferencia["recortar"]
        if recortar:
            self._antes_de_mover()
        destino = self._executar_operacao(arq.colar, origem, alvo, recortar)
        if not destino:
            return
        if recortar:
            self.area_transferencia = None
            self._depois_de_mover(origem, destino)
        else:
            documento.invalidar()
            self.atualizar_arvore()
            self.selecionar_caminho(destino)
        self.app.toast(t("editor.toast_colado", nome=arq.nome(destino)))

    def _duplicar(self, caminho):
        novo = self._executar_operacao(arq.duplicar, caminho)
        if novo:
            documento.invalidar()
            self.atualizar_arvore()
            self.selecionar_caminho(novo)
            self.app.toast(t("editor.toast_duplicado", nome=arq.nome(novo)))

    # ==================================================================
    # ARRASTAR E SOLTAR (reordenar na mesma pasta ou mover para outra)
    # ==================================================================
    def _arraste_inicio(self, evento):
        iid = self.tree.identify_row(evento.y)
        self._arraste = {"iid": iid, "caminho": self._caminho_item(iid), "iniciado": False} if iid else None

    def _arraste_movimento(self, evento):
        if not self._arraste or not self._arraste["caminho"]:
            return
        if not self._arraste["iniciado"]:
            self._arraste["iniciado"] = True
            self._fantasma = tk.Toplevel(self)
            self._fantasma.overrideredirect(True)
            self._fantasma.attributes("-topmost", True)
            self._fantasma.attributes("-alpha", 0.75)
            tk.Label(self._fantasma, text=self.tree.item(self._arraste["iid"], "text"), bg=tema.VERDE_ESCURO, fg="#ffffff",
                     font=("Segoe UI", 9, "bold"), padx=8, pady=4).pack()
        self._fantasma.geometry(f"+{evento.x_root + 12}+{evento.y_root + 12}")
        alvo = self.tree.identify_row(evento.y)
        if alvo and alvo != self._arraste["iid"]:
            self.tree.selection_set(alvo)

    def _arraste_fim(self, evento):
        if self._fantasma is not None:
            self._fantasma.destroy()
            self._fantasma = None
        arraste, self._arraste = self._arraste, None
        if not arraste or not arraste["iniciado"]:
            return
        alvo_iid = self.tree.identify_row(evento.y)
        if not alvo_iid or alvo_iid == arraste["iid"]:
            return
        origem = arraste["caminho"]
        alvo = self._caminho_item(alvo_iid)
        pai = self.tree.parent(arraste["iid"])
        if pai == self.tree.parent(alvo_iid):
            # Mesma pasta: só reordena (ordem livre salva em logs/folder_orders.json)
            self.tree.move(arraste["iid"], pai, self.tree.index(alvo_iid))
            nomes = [arq.nome(self._caminho_item(c)) for c in self.tree.get_children(pai)]
            arq.salvar_ordem(arq.pasta_de(origem), nomes)
            self.app.toast(t("editor.toast_ordem"))
            return
        self._antes_de_mover()
        destino = self._executar_operacao(arq.mover_para, origem, alvo)
        if destino and not arq.mesmo_caminho(destino, origem):
            self._depois_de_mover(origem, destino)
            self.app.toast(t("editor.toast_movido", nome=arq.nome(origem), pasta=arq.nome(arq.pasta_de(destino))))

    # ==================================================================
    # IA SOBRE O ARQUIVO E INTEGRAÇÃO COM OUTRAS PÁGINAS
    # ==================================================================
    def _acao_ia(self, tipo, caminho):
        if not caminho:
            return
        if acoes.arquivo_em_processamento(caminho):
            self.app.toast(t("editor.toast_ja_processando", nome=arq.nome(caminho)))
            return
        if cfg.obter("abrir_requisicoes", True):
            self.salvar_agora()
            self.app.abrir_requisicao(tipo, caminho)
            return
        texto = simpledialog.askstring(t(f"editor.ia_{tipo}_titulo"), t(f"editor.ia_{tipo}_pergunta", nome=arq.nome(caminho)), parent=self)
        if texto is None:
            return
        self._executar_ia(tipo, caminho, texto)

    def executar_requisicao(self, req):
        """Chamado pela aba Requisições: roda o pedido com as opções escolhidas."""
        if acoes.arquivo_em_processamento(req.caminho):
            self.app.toast(t("editor.toast_ja_processando", nome=arq.nome(req.caminho)))
            return
        self._executar_ia(req.tipo, req.caminho, req.objetivo, requisicao=req)

    def _executar_ia(self, tipo, caminho, texto, requisicao=None):
        nome = arq.nome(caminho)
        estava_aberto = self.sessao.eh_atual(caminho)
        if estava_aberto:
            self._guardar_posicao()
            self.salvar_agora()
            self.sessao.fechar()
            self._mostrar_aviso(t("editor.processando_titulo"), t(f"editor.processando_{tipo}", nome=nome), tema.AMARELO)

        def _fim(sucesso):
            chave = "editor.toast_ia_ok" if sucesso else "editor.toast_ia_sem_mudanca"
            self.app.toast(t(chave, nome=nome))
            self.atualizar_arvore()
            if estava_aberto:
                self.recarregar_arquivo(caminho)

        def _erro(e):
            self.app.toast(t("editor.toast_ia_erro", nome=nome))
            self.atualizar_arvore()
            if estava_aberto:
                self.recarregar_arquivo(caminho)

        if acoes.executar_acao_arquivo(tipo, caminho, texto, ao_concluir=_fim, ao_falhar=_erro, requisicao=requisicao):
            self.app.toast(t(f"editor.toast_ia_inicio_{tipo}", nome=nome))
            self.atualizar_arvore()
        else:
            self.app.toast(t("editor.toast_ja_processando", nome=nome))

    def _perguntar_silent(self, caminho):
        if not caminho:
            return
        self.salvar_agora()
        self.app.pagina("chat").anexar_arquivo(caminho)
        self.app.mostrar_pagina("chat")

    def _enviar_conselho(self, caminho):
        if not caminho:
            return
        if cfg.obter("abrir_requisicoes", True):
            self.salvar_agora()
            self.app.abrir_requisicao("conselho", caminho)
            return
        self.enviar_conselho(caminho)

    def enviar_conselho(self, caminho, requisicao=None):
        if self.sessao.eh_atual(caminho):
            self.salvar_agora()
            self.sessao.fechar()
            self._mostrar_aviso(t("editor.conselho_titulo"), t("editor.conselho_texto", nome=arq.nome(caminho)))
        self.app.pagina("council").carregar_arquivo(caminho, requisicao=requisicao)
        self.app.mostrar_pagina("council")
        self.app.toast(t("editor.toast_conselho", nome=arq.nome(caminho)))
