"""
Página Editor: árvore do projeto + editor de Markdown com pré-visualização.

Toda a lógica vive em engine.arquivos (operações de arquivo), engine.editor_session
(estado do arquivo aberto), engine.markdown_spans (destaques) e engine.acoes
(ações de IA). Aqui ficam só widgets, menus, arrastar-e-soltar e o timer de auto-save.
"""
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, simpledialog, scrolledtext

import core.config as cfg
import core.sistema as sistema
import engine.acoes as acoes
import engine.arquivos as arq
import engine.editor_session as es
import engine.markdown_spans as ms
import engine.preview_renderer as prev
import ui.theme as tema
from core.i18n import t
from ui.dialogs.history import JanelaHistorico
from ui.dialogs.new_file import DialogoNovoArquivo
from ui.widgets import PaginaBase, cabecalho

try:
    from tkinterweb import HtmlFrame
    TEM_PREVIEW = True
except ImportError:
    TEM_PREVIEW = False

AUTOSAVE_MS = 5000
CORES_TAGS = {
    "md_h1": (15, "bold", tema.VERDE), "md_h2": (13, "bold", "#34d399"), "md_h3": (12, "bold", tema.AZUL),
    "md_bold": (12, "bold", "#ffffff"), "md_italic": (12, "italic", "#cbd5e1"),
    "md_wikilink": (12, "bold underline", tema.AZUL_CLARO), "md_todo": (12, "bold", tema.LARANJA),
    "md_quote": (12, "italic", "#94a3b8"),
}


class PaginaEditor(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("editor.titulo"), t("editor.subtitulo"))
        self.sessao = es.SessaoEditor()
        self.timer_autosave = None
        self.area_transferencia = None      # {"caminho": str, "recortar": bool}
        self.modo_preview = False
        self._arraste = None
        self._fantasma = None
        self.tamanho_fonte = 12

        painel = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        painel.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        self._montar_arvore(painel)
        self._montar_editor(painel)
        self._montar_menus()
        self.atualizar_arvore()

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
        ttk.Button(busca, text="✕", width=3, command=self._limpar_busca).pack(side=tk.RIGHT, padx=(2, 0))

        self.tree = ttk.Treeview(quadro, selectmode="browse", show="tree")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        barra = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=barra.set)
        barra.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Button(quadro, text=t("editor.atualizar_arvore"), command=self.atualizar_arvore).pack(fill=tk.X, padx=5, pady=5)

        self.tree.bind("<<TreeviewSelect>>", self._selecionado)
        self.tree.bind("<Double-1>", self._duplo_clique)
        self.tree.bind("<Button-3>", self._menu_arvore)
        self.tree.bind("<F2>", lambda e: self._renomear_selecionado())
        self.tree.bind("<ButtonPress-1>", self._arraste_inicio)
        self.tree.bind("<B1-Motion>", self._arraste_movimento)
        self.tree.bind("<ButtonRelease-1>", self._arraste_fim)

    def _montar_editor(self, painel):
        quadro = ttk.Frame(painel)
        painel.add(quadro, weight=2)
        topo = ttk.Frame(quadro)
        topo.pack(fill=tk.X, padx=5, pady=(5, 2))
        ttk.Button(topo, text=t("editor.voltar"), width=9, command=self._voltar).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(topo, text=t("editor.avancar"), width=9, command=self._avancar).pack(side=tk.LEFT, padx=(0, 8))
        self.lbl_titulo = ttk.Label(topo, text=t("editor.titulo_vazio"), font=("Segoe UI", 9, "bold"),
                                    foreground=tema.VERDE, anchor="center")
        self.lbl_titulo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(topo, text=t("editor.btn_navegador"), width=10, command=self._abrir_no_navegador).pack(side=tk.RIGHT, padx=(2, 0))
        self.btn_preview = ttk.Button(topo, text=t("editor.btn_visualizar"), width=13, command=self._alternar_preview)
        self.btn_preview.pack(side=tk.RIGHT, padx=2)

        self.area = ttk.Frame(quadro)
        self.area.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2, 5))
        self.editor = scrolledtext.ScrolledText(
            self.area, wrap=tk.WORD, font=("Consolas", 12), undo=True, bg=tema.PAINEL, fg=tema.TEXTO,
            insertbackground="white", selectbackground=tema.VERDE_ESCURO, selectforeground="white", bd=0, highlightthickness=0)
        self.editor.pack(fill=tk.BOTH, expand=True)
        self.editor.config(state=tk.DISABLED)
        self.html = HtmlFrame(self.area, messages_enabled=False) if TEM_PREVIEW else None
        self._configurar_tags(self.tamanho_fonte)

        self.editor.bind("<KeyRelease>", self._tecla)
        self.editor.bind("<Control-s>", self._salvar_manual)
        self.editor.bind("<Control-S>", self._salvar_manual)
        self.editor.bind("<Button-3>", self._menu_editor)
        self.editor.tag_bind("md_wikilink", "<Enter>", lambda e: self.editor.config(cursor="hand2"))
        self.editor.tag_bind("md_wikilink", "<Leave>", lambda e: self.editor.config(cursor="xterm"))
        self.editor.tag_bind("md_wikilink", "<Button-1>", self._clique_wikilink)
        for widget in (self, self.editor, self.tree):
            widget.bind("<Alt-Left>", lambda e: self._voltar())
            widget.bind("<Alt-Right>", lambda e: self._avancar())
            try:
                widget.bind("<Button-8>", lambda e: self._voltar())
                widget.bind("<Button-9>", lambda e: self._avancar())
            except tk.TclError:
                pass

    def _configurar_tags(self, tamanho):
        for tag, (rel, estilo, cor) in CORES_TAGS.items():
            tamanho_tag = tamanho + (rel - 12)
            fonte = ("Consolas", tamanho_tag) + tuple(estilo.split())
            self.editor.tag_configure(tag, font=fonte, foreground=cor)
        self.editor.tag_configure("md_todo", background="#2a1205")

    def _montar_menus(self):
        opcoes = dict(tearoff=0, bg=tema.PAINEL, fg=tema.TEXTO, activebackground=tema.VERDE_ESCURO, activeforeground="white")
        self.menu_arvore = tk.Menu(self, **opcoes)
        self.menu_editor = tk.Menu(self, **opcoes)
        self.menu_editor.add_command(label=t("editor.menu_todo"), command=self._inserir_todo)
        self.menu_editor.add_separator()
        self.menu_editor.add_command(label=t("editor.menu_recortar"), command=lambda: self.editor.event_generate("<<Cut>>"))
        self.menu_editor.add_command(label=t("editor.menu_copiar"), command=lambda: self.editor.event_generate("<<Copy>>"))
        self.menu_editor.add_command(label=t("editor.menu_colar"), command=lambda: self.editor.event_generate("<<Paste>>"))
        self.menu_editor.add_separator()
        self.menu_editor.add_command(label=t("editor.menu_selecionar_tudo"), command=lambda: self.editor.tag_add("sel", "1.0", "end"))

    def ajustar_fonte(self, tamanho):
        self.tamanho_fonte = tamanho
        self.editor.configure(font=("Consolas", tamanho))
        self._configurar_tags(tamanho)

    # ==================================================================
    # ÁRVORE
    # ==================================================================
    def atualizar_arvore(self):
        abertas = {self.tree.item(i, "values")[0] for i in self._todos() if self.tree.item(i, "open") and self.tree.item(i, "values")}
        self.tree.delete(*self.tree.get_children())
        self._itens = {}
        consulta = self.var_busca.get().strip()
        permitidos = arq.buscar(consulta) if consulta else None
        raiz = arq.montar_arvore(permitidos)
        rotulo = raiz.nome + (t("editor.filtrado") if consulta else "")
        iid = self.tree.insert("", "end", text=rotulo, open=True, values=[raiz.caminho])
        self._itens[arq.absoluto(raiz.caminho)] = iid
        self._inserir_nos(iid, raiz.filhos, abertas, bool(consulta))
        if self.sessao.arquivo_atual in self._itens:
            item = self._itens[self.sessao.arquivo_atual]
            self.tree.selection_set(item)
            self.tree.see(item)
        if self.sessao.precisa_recarregar():
            self.recarregar_arquivo(self.sessao.arquivo_atual)

    def _inserir_nos(self, pai, nos, abertas, abrir_tudo):
        for no in nos:
            icone = "📁 " if no.pasta else "📄 "
            iid = self.tree.insert(pai, "end", text=icone + no.nome, values=[no.caminho],
                                   open=abrir_tudo or no.caminho in abertas)
            self._itens[arq.absoluto(no.caminho)] = iid
            if no.filhos:
                self._inserir_nos(iid, no.filhos, abertas, abrir_tudo)

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

    def _exibir_texto(self, texto):
        self.editor.config(state=tk.NORMAL)
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", texto)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self._destacar()
        self.app.atualizar_estatisticas(ms.estatisticas(texto))
        nome = self.sessao.nome_atual
        if self.modo_preview and self.html is not None:
            self.lbl_titulo.config(text=t("editor.visualizando", nome=nome), foreground=tema.AZUL_CLARO)
            self.html.load_html(prev.gerar_html_string_preview(texto, Path(self.sessao.arquivo_atual)))
        else:
            self.lbl_titulo.config(text=t("editor.editando", nome=nome), foreground=tema.VERDE)

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
        return resultado

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

    def abrir_arquivo(self, caminho):
        """Abre um arquivo no editor a partir de outra página (ex.: o Cânone do WorldBuilder)."""
        if not caminho or not arq.eh_arquivo(caminho):
            return
        self.salvar_agora()
        self.atualizar_arvore()
        self._abrir(caminho)
        self.selecionar_caminho(caminho)

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
        self._abrir(caminho, registrar_historico=False)
        self.selecionar_caminho(caminho)

    def _selecionado(self, _evento=None):
        selecao = self.tree.selection()
        if not selecao:
            return
        caminho = self._caminho_item(selecao[0])
        if not caminho:
            return
        if self.sessao.eh_atual(caminho) and not self.sessao.em_processamento(caminho):
            return

        anterior = self.sessao.arquivo_atual
        editado = bool(self.editor.edit_modified())
        salvo = self.salvar_agora() == es.SALVO if anterior else False

        if arq.eh_arquivo(caminho):
            self._abrir(caminho)
        else:
            self.sessao.fechar()
            self._mostrar_aviso(t("editor.diretorio", nome=arq.nome(caminho)),
                                t("editor.diretorio_texto", nome=arq.nome(caminho)))

        # Expander automático do arquivo que acabou de ser editado e deixado
        if anterior and salvo and editado and acoes.deve_auto_expandir(anterior):
            self._executar_ia("expander", anterior, "")

    def _tecla(self, _evento=None):
        if str(self.editor.cget("state")) == "disabled":
            return
        self._destacar()
        self.app.atualizar_estatisticas(ms.estatisticas(self._texto_editor()))
        self._cancelar_autosave()
        self.timer_autosave = self.after(AUTOSAVE_MS, self._autosave)

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
        for tag in ms.TAGS:
            self.editor.tag_remove(tag, "1.0", tk.END)
        for tag, inicio, fim in ms.destaques(self._texto_editor()):
            self.editor.tag_add(tag, f"1.0 + {inicio} chars", f"1.0 + {fim} chars")

    # ==================================================================
    # NAVEGAÇÃO
    # ==================================================================
    def _voltar(self):
        self.salvar_agora()
        destino = self.sessao.voltar()
        if destino:
            self._abrir(destino, registrar_historico=False)
            self.selecionar_caminho(destino)
            self.app.toast(t("editor.toast_voltar", nome=arq.nome(destino)))
        else:
            self.app.toast(t("editor.inicio_historico"))
        return "break"

    def _avancar(self):
        self.salvar_agora()
        destino = self.sessao.avancar()
        if destino:
            self._abrir(destino, registrar_historico=False)
            self.selecionar_caminho(destino)
            self.app.toast(t("editor.toast_avancar", nome=arq.nome(destino)))
        else:
            self.app.toast(t("editor.fim_historico"))
        return "break"

    def _clique_wikilink(self, evento):
        indice = self.editor.index(f"@{evento.x},{evento.y}")
        faixa = self.editor.tag_prevrange("md_wikilink", f"{indice}+1c")
        alvo = ms.alvo_wikilink(self.editor.get(*faixa)) if faixa else None
        if not alvo:
            return
        caminho = arq.resolver_wikilink(alvo)
        if caminho:
            self.salvar_agora()
            self.selecionar_caminho(caminho)
            self.app.toast(t("editor.toast_navegando", nome=arq.nome(caminho)))
            return
        if messagebox.askyesno(t("editor.criar_wikilink_titulo"), t("editor.criar_wikilink", alvo=alvo), parent=self):
            pasta = arq.pasta_de(self.sessao.arquivo_atual) if self.sessao.arquivo_atual else acoes.projeto_ativo()[1]
            novo = arq.criar_por_wikilink(alvo, pasta, self.sessao.nome_atual)
            self.atualizar_arvore()
            self.selecionar_caminho(novo)
            self.app.toast(t("editor.toast_criado", nome=arq.nome(novo)))

    # ==================================================================
    # PRÉ-VISUALIZAÇÃO
    # ==================================================================
    def _alternar_preview(self):
        if self.html is None:
            self.app.toast(t("editor.sem_tkinterweb"))
            return
        if not self.sessao.arquivo_atual:
            self.app.toast(t("editor.selecione_arquivo"))
            return
        self.modo_preview = not self.modo_preview
        if self.modo_preview:
            self.salvar_agora()
            self.editor.pack_forget()
            self.html.pack(fill=tk.BOTH, expand=True)
            self.btn_preview.config(text=t("editor.btn_editar"))
        else:
            self.html.pack_forget()
            self.editor.pack(fill=tk.BOTH, expand=True)
            self.btn_preview.config(text=t("editor.btn_visualizar"))
            self.editor.focus_set()
        self._exibir_texto(self._texto_editor().rstrip("\n"))

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
    # MENUS
    # ==================================================================
    def _menu_editor(self, evento):
        if str(self.editor.cget("state")) == "disabled":
            return
        self.editor.focus_set()
        if not self.editor.tag_ranges("sel"):
            self.editor.mark_set("insert", f"@{evento.x},{evento.y}")
        self.menu_editor.post(evento.x_root, evento.y_root)

    def _inserir_todo(self):
        if str(self.editor.cget("state")) != "disabled":
            self.editor.insert("insert", "<-- TODO: ")
            self._tecla()
            self.app.toast(t("editor.toast_todo"))

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
        self.salvar_agora()

    def _depois_de_mover(self, origem, destino):
        if self.sessao.acompanhar_movimento(origem, destino):
            self.lbl_titulo.config(text=t("editor.editando", nome=self.sessao.nome_atual))
        self.atualizar_arvore()
        # Mantém o foco no arquivo aberto (selecionar a pasta movida fecharia o editor)
        self.selecionar_caminho(self.sessao.arquivo_atual or destino)

    def _novo_arquivo(self, pasta):
        dialogo = DialogoNovoArquivo(self, arq.listar_templates())
        if not dialogo.nome:
            return
        caminho = self._executar_operacao(arq.criar_arquivo, pasta, dialogo.nome, dialogo.template)
        if caminho:
            self.atualizar_arvore()
            self.selecionar_caminho(caminho)
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
            self.app.toast(t("editor.toast_excluido", nome=arq.nome(caminho)))
        self.atualizar_arvore()

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
            self.atualizar_arvore()
            self.selecionar_caminho(destino)
        self.app.toast(t("editor.toast_colado", nome=arq.nome(destino)))

    def _duplicar(self, caminho):
        novo = self._executar_operacao(arq.duplicar, caminho)
        if novo:
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
        else:
            self.app.toast(t("editor.toast_ja_processando", nome=nome))

    def _perguntar_silent(self, caminho):
        self.salvar_agora()
        self.app.pagina("chat").anexar_arquivo(caminho)
        self.app.mostrar_pagina("chat")

    def _enviar_conselho(self, caminho):
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
