"""Página Converse com Silent (chat local com o mundo como contexto)."""
import tkinter as tk
from tkinter import ttk

import core.silent_persona as silent
import core.tarefas as tarefas
import ui.theme as tema
from core.i18n import t
from ui.dialogs.note import JanelaNota
from ui.widgets import PaginaBase, cabecalho, texto_rolavel, anexar_texto, substituir_texto


class PaginaChat(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("chat.titulo"), t("chat.subtitulo"))
        self._anexo = None
        self._historico_exibido = None
        self._mensagens = []            # [(papel, texto)]; a tag "msgN" marca o texto da mensagem N

        entrada = ttk.Frame(self)
        entrada.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=(0, 15))
        self.entrada = ttk.Entry(entrada, font=("Segoe UI", 10))
        self.entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entrada.bind("<Return>", lambda e: self._enviar())
        ttk.Button(entrada, text=t("chat.btn_wb"), command=self._levar_ao_worldbuilder).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(entrada, text=t("chat.btn_nota"), command=self._nota_ultima_resposta).pack(side=tk.RIGHT, padx=(5, 0))
        self.btn_enviar = ttk.Button(entrada, text=t("chat.enviar"), command=self._enviar)
        self.btn_enviar.pack(side=tk.RIGHT)

        self.texto = texto_rolavel(self)
        self.texto.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        self.texto.tag_config("usuario", foreground=tema.AZUL, font=("Segoe UI", 10, "bold"))
        self.texto.tag_config("silent", foreground="#34d399", font=("Segoe UI", 10, "bold"))
        self.texto.tag_config("sistema", foreground=tema.SUAVE, font=("Segoe UI", 9, "italic"))
        self.texto.tag_config("pensando", foreground=tema.AMARELO, font=("Segoe UI", 9, "italic"))
        self.texto.bind("<Button-3>", self._menu_mensagem)
        self.menu = tk.Menu(self, tearoff=0, bg=tema.PAINEL, fg=tema.TEXTO, activebackground=tema.VERDE_ESCURO)
        self._mensagem("sistema", t("chat.conectado"))

    # --- exibição ---
    def _mensagem(self, papel, texto):
        indice = len(self._mensagens)
        self._mensagens.append((papel, texto))
        anexar_texto(self.texto, f"{t('chat.autor.' + papel)}: ", papel)
        anexar_texto(self.texto, f"{texto}\n\n", f"msg{indice}")

    def ao_exibir(self):
        self.recarregar_historico()

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
        self.texto.configure(font=("Segoe UI", tamanho))

    # --- notas e WorldBuilder ---
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
        self.menu.add_command(label=t("chat.btn_wb"), command=self._levar_ao_worldbuilder)
        self.menu.post(evento.x_root, evento.y_root)

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

    # --- anexar arquivo (chamado pelo Editor) ---
    def anexar_arquivo(self, caminho):
        try:
            self._anexo = silent.preparar_anexo(caminho)
        except Exception as e:
            self.app.toast(t("chat.erro_anexo", erro=e))
            return
        self.entrada.delete(0, tk.END)
        self.entrada.insert(0, t("chat.prefixo_anexo", nome=self._anexo["nome"]))
        self.entrada.focus_set()
        self.app.toast(t("chat.toast_anexo", nome=self._anexo["nome"]))

    # --- envio ---
    def _enviar(self):
        mensagem = self.entrada.get().strip()
        if not mensagem:
            return
        self.entrada.delete(0, tk.END)
        self._mensagem("usuario", mensagem)
        anexar_texto(self.texto, f"{t('chat.autor.silent')}: ", "silent")
        anexar_texto(self.texto, t("chat.pensando") + "\n\n", "pensando")
        self.btn_enviar.config(state=tk.DISABLED)
        self.app.salvar_editor()
        anexo, self._anexo = self._anexo, None
        tarefas.executar_em_segundo_plano(silent.conversar, mensagem, anexo,
                                          ao_concluir=self._resposta, ao_falhar=self._falha)

    def _remover_pensando(self):
        faixas = self.texto.tag_ranges("pensando")
        if faixas:
            self.texto.config(state=tk.NORMAL)
            self.texto.delete(self.texto.index(f"{faixas[0]} linestart"), tk.END)
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
