"""Página Converse com Ao (chat local com o mundo como contexto)."""
import tkinter as tk
from tkinter import ttk

import core.ao_persona as ao
import core.tarefas as tarefas
import ui.theme as tema
from core.i18n import t
from ui.widgets import PaginaBase, cabecalho, texto_rolavel, anexar_texto, substituir_texto


class PaginaChat(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("chat.titulo"), t("chat.subtitulo"))
        self._anexo = None
        self._historico_exibido = None

        entrada = ttk.Frame(self)
        entrada.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=(0, 15))
        self.entrada = ttk.Entry(entrada, font=("Segoe UI", 10))
        self.entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entrada.bind("<Return>", lambda e: self._enviar())
        self.btn_enviar = ttk.Button(entrada, text=t("chat.enviar"), command=self._enviar)
        self.btn_enviar.pack(side=tk.RIGHT)

        self.texto = texto_rolavel(self)
        self.texto.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        self.texto.tag_config("usuario", foreground=tema.AZUL, font=("Segoe UI", 10, "bold"))
        self.texto.tag_config("ao", foreground="#34d399", font=("Segoe UI", 10, "bold"))
        self.texto.tag_config("sistema", foreground=tema.SUAVE, font=("Segoe UI", 9, "italic"))
        self.texto.tag_config("pensando", foreground=tema.AMARELO, font=("Segoe UI", 9, "italic"))
        self._mensagem("sistema", t("chat.conectado"))

    # --- exibição ---
    def _mensagem(self, papel, texto):
        anexar_texto(self.texto, f"{t('chat.autor.' + papel)}: ", papel)
        anexar_texto(self.texto, f"{texto}\n\n")

    def ao_exibir(self):
        self.recarregar_historico()

    def projeto_alterado(self):
        self.recarregar_historico(forcar=True)

    def recarregar_historico(self, forcar=False):
        historico = ao.historico_chat()
        if historico == self._historico_exibido and not forcar:
            return
        self._historico_exibido = historico
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

    # --- anexar arquivo (chamado pelo Editor) ---
    def anexar_arquivo(self, caminho):
        try:
            self._anexo = ao.preparar_anexo(caminho)
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
        anexar_texto(self.texto, f"{t('chat.autor.ao')}: ", "ao")
        anexar_texto(self.texto, t("chat.pensando") + "\n\n", "pensando")
        self.btn_enviar.config(state=tk.DISABLED)
        self.app.salvar_editor()
        anexo, self._anexo = self._anexo, None
        tarefas.executar_em_segundo_plano(ao.conversar, mensagem, anexo,
                                          ao_concluir=self._resposta, ao_falhar=self._falha)

    def _remover_pensando(self):
        faixas = self.texto.tag_ranges("pensando")
        if faixas:
            self.texto.config(state=tk.NORMAL)
            self.texto.delete(self.texto.index(f"{faixas[0]} linestart"), tk.END)
            self.texto.config(state=tk.DISABLED)

    def _resposta(self, resposta):
        self._remover_pensando()
        self._mensagem("ao", resposta or t("chat.sem_resposta"))
        self._historico_exibido = ao.historico_chat()
        self.btn_enviar.config(state=tk.NORMAL)

    def _falha(self, erro):
        self._remover_pensando()
        self._mensagem("sistema", t("chat.erro", erro=erro))
        self.btn_enviar.config(state=tk.NORMAL)
