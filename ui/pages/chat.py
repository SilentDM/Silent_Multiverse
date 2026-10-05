"""
Página Converse com Silent (chat local com o mundo como contexto).

Caixa de mensagem com várias linhas (Enter envia, Ctrl+Enter quebra a linha), atalhos de pedido,
anexos (arquivos do projeto, arquivos do computador e imagens) e respostas formatadas em Markdown,
com [[links]] clicáveis que abrem o arquivo no Editor.
"""
import tkinter as tk
from tkinter import ttk, filedialog

import core.atalhos_chat as atalhos
import core.markdown_simples as md
import core.silent_persona as silent
import engine.acoes as acoes
import engine.documento as documento
import ui.theme as tema
from core.i18n import t
from ui.dialogs.note import JanelaNota
from ui.dialogs.quick_open import JanelaAberturaRapida
from ui.dialogs.shortcuts import JanelaAtalhos
from ui.widgets import PaginaBase, cabecalho, texto_rolavel, anexar_texto, substituir_texto, Dica, LinhaFluida

TIPOS_IMAGEM = "*.png *.jpg *.jpeg *.webp *.gif *.bmp"
MAX_ANEXOS = 10


class PaginaChat(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("chat.titulo"), t("chat.subtitulo"))
        self._anexos = []               # preparados por silent.preparar_anexo()
        self._historico_exibido = None
        self._mensagens = []            # [(papel, texto)]; a tag "msgN" marca o texto da mensagem N
        self._tamanho = 10

        self._montar_composicao()
        self.texto = texto_rolavel(self)
        self.texto.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 8))
        self._configurar_tags()
        self.texto.bind("<Button-3>", self._menu_mensagem)
        self.texto.tag_bind("link", "<Button-1>", self._clique_link)
        self.texto.tag_bind("link", "<Enter>", lambda e: self.texto.config(cursor="hand2"))
        self.texto.tag_bind("link", "<Leave>", lambda e: self.texto.config(cursor=""))
        self.menu = tk.Menu(self, tearoff=0, bg=tema.PAINEL, fg=tema.TEXTO, activebackground=tema.VERDE_ESCURO)
        self._mensagem("sistema", t("chat.conectado"))

    # ------------------------------------------------------------------
    # MONTAGEM
    # ------------------------------------------------------------------
    def _montar_composicao(self):
        base = ttk.Frame(self)
        base.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=(0, 12))

        # Atalhos de pedido
        linha_atalhos = ttk.Frame(base)
        linha_atalhos.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(linha_atalhos, text=t("chat.atalhos"), style="Dica.TLabel").pack(side=tk.LEFT, anchor=tk.N, pady=3)
        editar = ttk.Button(linha_atalhos, text="✎", width=3, style="Atalho.TButton", command=self._editar_atalhos)
        editar.pack(side=tk.RIGHT, anchor=tk.N)
        Dica(editar, t("chat.atalhos_editar"))
        self.quadro_atalhos = LinhaFluida(linha_atalhos)
        self.quadro_atalhos.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self._exibir_atalhos()

        # Anexos (só aparece quando há algum)
        self.quadro_anexos = LinhaFluida(base)

        # Caixa de mensagem + botões
        self.linha_entrada = ttk.Frame(base)
        self.linha_entrada.pack(fill=tk.X)
        self.entrada = tk.Text(self.linha_entrada, height=4, wrap=tk.WORD, font=("Segoe UI", 10), undo=True,
                               bg=tema.PAINEL, fg=tema.TEXTO, insertbackground="white", bd=0, padx=8, pady=6,
                               highlightthickness=1, highlightbackground="#3a3a3a", highlightcolor=tema.VERDE)
        self.entrada.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entrada.bind("<Return>", self._tecla_enter)
        self.entrada.bind("<Control-Return>", self._quebrar_linha)
        self.entrada.bind("<Shift-Return>", self._quebrar_linha)
        botoes = ttk.Frame(self.linha_entrada)
        botoes.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))
        self.btn_enviar = ttk.Button(botoes, text=t("chat.enviar"), style="Primario.TButton", command=self._enviar)
        self.btn_enviar.pack(fill=tk.X)
        anexar = ttk.Menubutton(botoes, text=t("chat.anexar"))
        menu_anexar = tk.Menu(anexar, tearoff=0, bg=tema.PAINEL, fg=tema.TEXTO, activebackground=tema.VERDE_ESCURO)
        menu_anexar.add_command(label=t("chat.anexar_projeto"), command=self._anexar_do_projeto)
        menu_anexar.add_command(label=t("chat.anexar_imagem"), command=self._anexar_imagem)
        menu_anexar.add_command(label=t("chat.anexar_computador"), command=self._anexar_do_computador)
        anexar["menu"] = menu_anexar
        anexar.pack(fill=tk.X, pady=(6, 0))

        rodape = ttk.Frame(base)
        rodape.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(rodape, text=t("chat.dica_teclas"), style="Dica.TLabel").pack(side=tk.LEFT)
        ttk.Button(rodape, text=t("chat.btn_wb"), style="Ferramenta.TButton",
                   command=self._levar_ao_worldbuilder).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(rodape, text=t("chat.btn_nota"), style="Ferramenta.TButton",
                   command=self._nota_ultima_resposta).pack(side=tk.RIGHT)

    def _configurar_tags(self):
        tam = self._tamanho
        self.texto.configure(font=("Segoe UI", tam))
        self.entrada.configure(font=("Segoe UI", tam))
        tags = {
            "usuario": dict(foreground=tema.AZUL, font=("Segoe UI", tam, "bold")),
            "silent": dict(foreground="#34d399", font=("Segoe UI", tam, "bold")),
            "sistema": dict(foreground=tema.SUAVE, font=("Segoe UI", tam - 1, "italic")),
            "pensando": dict(foreground=tema.AMARELO, font=("Segoe UI", tam - 1, "italic")),
            "anexos": dict(foreground=tema.SUAVE, font=("Segoe UI", tam - 1)),
            "h1": dict(foreground=tema.VERDE, font=("Segoe UI", tam + 5, "bold"), spacing1=8, spacing3=4),
            "h2": dict(foreground=tema.VERDE, font=("Segoe UI", tam + 3, "bold"), spacing1=6, spacing3=3),
            "h3": dict(foreground="#34d399", font=("Segoe UI", tam + 1, "bold"), spacing1=4, spacing3=2),
            "negrito": dict(font=("Segoe UI", tam, "bold")),
            "italico": dict(font=("Segoe UI", tam, "italic")),
            "codigo": dict(font=("Consolas", tam), background="#2a2a2a", foreground="#fbbf24"),
            "bloco_codigo": dict(font=("Consolas", tam - 1), background="#181818", foreground="#d4d4d4",
                                 lmargin1=12, lmargin2=12),
            "tabela": dict(font=("Consolas", tam - 1), foreground="#d4d4d4"),
            "citacao": dict(foreground="#a3a3a3", font=("Segoe UI", tam, "italic"), lmargin1=16, lmargin2=16),
            "lista": dict(lmargin1=4, lmargin2=24),
            "regra": dict(foreground="#3a3a3a"),
            "link": dict(foreground=tema.AZUL_CLARO, underline=True),
        }
        for nome, opcoes in tags.items():
            self.texto.tag_config(nome, **opcoes)
        # Estilos de trecho valem por cima dos de bloco (negrito dentro de uma lista, link dentro de um título)
        for nome in ("negrito", "italico", "codigo", "link"):
            self.texto.tag_raise(nome)

    # ------------------------------------------------------------------
    # EXIBIÇÃO
    # ------------------------------------------------------------------
    def _mensagem(self, papel, texto):
        indice = len(self._mensagens)
        self._mensagens.append((papel, texto))
        marca = f"msg{indice}"
        if papel == "sistema":
            anexar_texto(self.texto, f"{t('chat.autor.' + papel)}: ", papel)
            anexar_texto(self.texto, f"{texto}\n\n", ("sistema", marca))
            return
        anexar_texto(self.texto, f"{t('chat.autor.' + papel)}\n", papel)
        if papel == "silent":
            for trecho, tags in md.segmentos(texto):
                anexar_texto(self.texto, trecho, tags + (marca,))
        else:
            anexar_texto(self.texto, texto, (marca,))
        anexar_texto(self.texto, "\n\n")

    def ao_exibir(self):
        self.recarregar_historico()
        self.after_idle(self.quadro_atalhos.organizar)
        self.entrada.focus_set()

    def projeto_alterado(self):
        self.recarregar_historico(forcar=True)

    def recarregar_historico(self, forcar=False):
        historico = silent.historico_chat()
        if historico == self._historico_exibido and not forcar:
            return
        self._historico_exibido = historico
        self._mensagens = []
        substituir_texto(self.texto, "")
        if not historico:
            self._mensagem("sistema", t("chat.sem_memoria"))
            return
        self._mensagem("sistema", t("chat.memoria_carregada"))
        for papel, conteudo in historico:
            if papel == "resumo":
                self._mensagem("sistema", t("chat.resumo_anterior", resumo=conteudo))
            else:
                self._mensagem(papel, conteudo)

    def ajustar_fonte(self, tamanho):
        self._tamanho = tamanho
        self._configurar_tags()

    def _clique_link(self, evento):
        indice = self.texto.index(f"@{evento.x},{evento.y}")
        faixa = self.texto.tag_prevrange("link", f"{indice}+1c")
        if not faixa:
            return
        nome = self.texto.get(*faixa)
        caminho = documento.resolver_link(nome)
        if not caminho:
            self.app.toast(t("chat.link_sem_arquivo", nome=nome))
            return
        self.app.mostrar_pagina("editor")
        self.app.pagina("editor").ir_para(caminho)

    # ------------------------------------------------------------------
    # ATALHOS DE PEDIDO
    # ------------------------------------------------------------------
    def _exibir_atalhos(self):
        for filho in self.quadro_atalhos.winfo_children():
            filho.destroy()
        for atalho in atalhos.listar():
            botao = ttk.Button(self.quadro_atalhos, text=atalho["nome"], style="Atalho.TButton",
                               command=lambda a=atalho: self._usar_atalho(a["texto"]))
            Dica(botao, atalho["texto"])
        self.after_idle(self.quadro_atalhos.organizar)

    def _usar_atalho(self, texto):
        """Põe o pedido pronto na caixa e seleciona o primeiro [trecho a completar]."""
        if self.entrada.get("1.0", "end-1c").strip():
            self.entrada.insert(tk.INSERT, "\n")
        inicio = self.entrada.index(tk.INSERT)
        self.entrada.insert(tk.INSERT, texto)
        self.entrada.tag_remove(tk.SEL, "1.0", tk.END)
        campo = atalhos.primeiro_campo(texto)
        if campo:
            self.entrada.tag_add(tk.SEL, f"{inicio}+{campo[0]}c", f"{inicio}+{campo[1]}c")
            self.entrada.mark_set(tk.INSERT, f"{inicio}+{campo[1]}c")
        self.entrada.see(tk.INSERT)
        self.entrada.focus_set()

    def _editar_atalhos(self):
        JanelaAtalhos(self.app, ao_salvar=self._exibir_atalhos)

    # ------------------------------------------------------------------
    # ANEXOS
    # ------------------------------------------------------------------
    def anexar_arquivo(self, caminho):
        """Anexa um arquivo à próxima mensagem (também chamado pelo Editor)."""
        if len(self._anexos) >= MAX_ANEXOS:
            self.app.toast(t("chat.limite_anexos", total=MAX_ANEXOS))
            return
        try:
            anexo = silent.preparar_anexo(caminho)
        except Exception as e:
            self.app.toast(t("chat.erro_anexo", erro=e))
            return
        self._anexos = [a for a in self._anexos if a["nome"] != anexo["nome"]] + [anexo]
        self._exibir_anexos()
        self.entrada.focus_set()
        self.app.toast(t("chat.toast_anexo", nome=anexo["nome"]))

    def _anexar_do_projeto(self):
        JanelaAberturaRapida(self.app, self.anexar_arquivo, titulo=t("chat.anexar_projeto_titulo"))

    def _anexar_imagem(self):
        for caminho in filedialog.askopenfilenames(parent=self, title=t("chat.anexar_imagem_titulo"),
                                                   filetypes=[(t("chat.tipo_imagem"), TIPOS_IMAGEM)]):
            self.anexar_arquivo(caminho)

    def _anexar_do_computador(self):
        for caminho in filedialog.askopenfilenames(
                parent=self, title=t("chat.anexar_computador_titulo"),
                filetypes=[(t("chat.tipo_texto"), "*.md *.txt"), (t("chat.tipo_imagem"), TIPOS_IMAGEM)]):
            self.anexar_arquivo(caminho)

    def _remover_anexo(self, nome):
        self._anexos = [a for a in self._anexos if a["nome"] != nome]
        self._exibir_anexos()

    def _exibir_anexos(self):
        for filho in self.quadro_anexos.winfo_children():
            filho.destroy()
        if not self._anexos:
            self.quadro_anexos.pack_forget()
            return
        for anexo in self._anexos:
            chip = tk.Frame(self.quadro_anexos, bg=tema.PAINEL, highlightthickness=1, highlightbackground="#2d2d2d")
            icone = "🖼" if anexo.get("tipo") == "imagem" else "📄"
            tk.Label(chip, text=f"{icone} {anexo['nome']}", bg=tema.PAINEL, fg=tema.TEXTO,
                     font=("Segoe UI", 9), padx=6).pack(side=tk.LEFT)
            fechar = tk.Label(chip, text="✕", bg=tema.PAINEL, fg=tema.SUAVE, font=("Segoe UI", 8, "bold"),
                              cursor="hand2", padx=4)
            fechar.pack(side=tk.LEFT)
            fechar.bind("<Button-1>", lambda e, n=anexo["nome"]: self._remover_anexo(n))
        self.quadro_anexos.pack(fill=tk.X, pady=(0, 6), before=self.linha_entrada)
        self.after_idle(self.quadro_anexos.organizar)

    # ------------------------------------------------------------------
    # NOTAS E WORLDBUILDER
    # ------------------------------------------------------------------
    def _mensagem_no_ponto(self, evento):
        indice = self.texto.index(f"@{evento.x},{evento.y}")
        for tag in self.texto.tag_names(indice):
            if tag.startswith("msg") and tag[3:].isdigit() and int(tag[3:]) < len(self._mensagens):
                return self._mensagens[int(tag[3:])]
        return None

    def _menu_mensagem(self, evento):
        mensagem = self._mensagem_no_ponto(evento)
        self.menu.delete(0, tk.END)
        if mensagem and mensagem[0] in ("silent", "usuario"):
            self.menu.add_command(label=t("chat.menu_nota"), command=lambda: self._salvar_nota(mensagem[1]))
            self.menu.add_command(label=t("chat.menu_reusar"), command=lambda: self._reusar(mensagem[1]))
        self.menu.add_command(label=t("chat.btn_wb"), command=self._levar_ao_worldbuilder)
        self.menu.post(evento.x_root, evento.y_root)

    def _reusar(self, texto):
        self.entrada.delete("1.0", tk.END)
        self.entrada.insert("1.0", texto)
        self.entrada.focus_set()

    def _nota_ultima_resposta(self):
        respostas = [texto for papel, texto in self._mensagens if papel == "silent"]
        if not respostas:
            self.app.toast(t("chat.sem_resposta_nota"))
            return
        self._salvar_nota(respostas[-1])

    def _salvar_nota(self, texto):
        JanelaNota(self.app, texto, "silent", arquivo_atual=self.app.pagina("editor").sessao.arquivo_atual)

    def _levar_ao_worldbuilder(self):
        conversa = silent.conversa_como_texto()
        if not conversa.strip():
            self.app.toast(t("chat.sem_resposta_nota"))
            return
        self.app.pagina("worldbuilder").receber_ideia(conversa)
        self.app.mostrar_pagina("worldbuilder")
        self.app.toast(t("chat.toast_wb"))

    # ------------------------------------------------------------------
    # ENVIO
    # ------------------------------------------------------------------
    def _tecla_enter(self, _evento):
        self._enviar()
        return "break"

    def _quebrar_linha(self, _evento):
        self.entrada.insert(tk.INSERT, "\n")
        self.entrada.see(tk.INSERT)
        return "break"

    def _enviar(self):
        mensagem = self.entrada.get("1.0", "end-1c").strip()
        if not mensagem:
            if self._anexos:
                self.app.toast(t("chat.escreva_pedido"))
            return
        anexos = list(self._anexos)
        if not acoes.conversar_silent(mensagem, anexos, ao_concluir=self._resposta, ao_falhar=self._falha):
            self.app.toast(t("chat.aguarde"))
            return
        self.app.salvar_editor()
        self.entrada.delete("1.0", tk.END)
        self._anexos = []
        self._exibir_anexos()
        self._mensagem("usuario", mensagem)
        if anexos:
            anexar_texto(self.texto, t("chat.anexos_enviados", nomes=", ".join(a["nome"] for a in anexos)) + "\n\n",
                         "anexos")
        anexar_texto(self.texto, f"{t('chat.autor.silent')}\n", "silent")
        anexar_texto(self.texto, t("chat.pensando") + "\n\n", "pensando")
        self.btn_enviar.config(state=tk.DISABLED)

    def _remover_pensando(self):
        faixas = self.texto.tag_ranges("pensando")
        if faixas:
            self.texto.config(state=tk.NORMAL)
            # Apaga o "Silent" + "pensando..." provisórios (a resposta é escrita no lugar)
            inicio = self.texto.tag_prevrange("silent", faixas[0])
            self.texto.delete(inicio[0] if inicio else self.texto.index(f"{faixas[0]} linestart"), tk.END)
            self.texto.config(state=tk.DISABLED)

    def _resposta(self, resposta):
        self._remover_pensando()
        self._mensagem("silent", resposta or t("chat.sem_resposta"))
        self._historico_exibido = silent.historico_chat()
        self.btn_enviar.config(state=tk.NORMAL)

    def _falha(self, erro):
        self._remover_pensando()
        self._mensagem("sistema", t("chat.erro", erro=erro))
        self.btn_enviar.config(state=tk.NORMAL)
