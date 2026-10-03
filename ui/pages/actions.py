"""Página Ações: Expander, contexto, auditoria, livro, tamanho, backup e memórias."""
import tkinter as tk
from tkinter import ttk, messagebox

import core.eventos as ev
import core.tarefas as tarefas
import engine.acoes as acoes
from core.i18n import t
from ui.dialogs.audit_report import JanelaAuditoria
from ui.dialogs.token_report import JanelaTamanhoProjeto
from ui.widgets import PaginaBase, GradeRolavel, cabecalho

# Ação (engine.acoes) -> chave do botão que fica desabilitado enquanto ela roda
BOTOES_POR_ACAO = {
    "expander": "expander", "contexto": "contexto", "auditoria": "auditoria",
    "livro": "livro", "tamanho": "tamanho", "backup": "backup",
}


class PaginaAcoes(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("actions.title"), t("actions.subtitle"))
        self.grade = GradeRolavel(self)
        self.grade.pack(fill=tk.BOTH, expand=True)
        self.botoes = {}
        self.status = {}

        caixa = self.grade.nova_caixa(t("actions.stop_title"))
        ttk.Button(caixa, text=t("actions.stop_all"), command=self._parar).pack(fill=tk.X, padx=10, pady=10)

        caixa = self.grade.nova_caixa(t("actions.expander_title"))
        self._botao(caixa, "expander", t("actions.expander_btn"), self._expander)
        self._status(caixa, "expander")
        self._botao(caixa, "contexto", t("actions.rebuild_ctx_btn"), self._contexto)

        caixa = self.grade.nova_caixa(t("actions.audit_title"))
        self._botao(caixa, "auditoria", t("actions.audit_btn"), self._auditoria)
        self._status(caixa, "auditoria")

        caixa = self.grade.nova_caixa(t("actions.export_title"))
        self._botao(caixa, "livro", t("actions.export_btn"), self._livro)
        self._botao(caixa, "tamanho", t("actions.size_btn"), self._tamanho)

        caixa = self.grade.nova_caixa(t("actions.mgmt_title"))
        self._botao(caixa, "backup", t("actions.backup_btn"), self._backup)
        self._botao(caixa, "memorias", t("actions.del_memories_btn"), self._excluir_memorias)
        self._botao(caixa, "dados", t("actions.open_data_btn"), acoes.abrir_pasta_dados)

        self.grade.organizar()
        ev.inscrever_evento("acao.estado", lambda d: tarefas.na_interface(self._estado_acao, d))

    # --- montagem ---
    def _botao(self, caixa, chave, texto, comando):
        botao = ttk.Button(caixa, text=texto, command=comando)
        botao.pack(fill=tk.X, padx=10, pady=(8, 4))
        self.botoes[chave] = botao

    def _status(self, caixa, chave):
        rotulo = ttk.Label(caixa, text=t("actions.status_idle"))
        rotulo.pack(anchor=tk.W, padx=10, pady=(0, 8))
        self.status[chave] = rotulo

    def rolar(self, unidades):
        self.grade.rolar(unidades)

    def _estado_acao(self, dados):
        chave = BOTOES_POR_ACAO.get(dados["acao"])
        if not chave:
            return
        self.botoes[chave].config(state=tk.DISABLED if dados["rodando"] else tk.NORMAL)
        if chave in self.status and dados["rodando"]:
            self.status[chave].config(text=t("actions.status_running"), foreground="#60a5fa")

    def _fim(self, chave, texto, ok=True):
        if chave in self.status:
            self.status[chave].config(text=t("actions.status_text", status=texto),
                                      foreground="#e3e3e3" if ok else "#ef4444")

    # --- ações ---
    def _parar(self):
        acoes.parar_tudo()
        self.app.toast(t("actions.toast_stopping"))

    def _expander(self):
        self.app.salvar_editor()
        if acoes.executar_expander(
                ao_concluir=lambda _: (self._fim("expander", t("actions.done")), self.app.toast(t("actions.toast_expander_ok")),
                                       self.app.pagina("editor").atualizar_arvore()),
                ao_falhar=lambda e: (self._fim("expander", t("actions.failed"), False), self.app.toast(t("actions.toast_expander_erro")))):
            self.app.toast(t("actions.toast_expander_start"))

    def _contexto(self):
        if acoes.reconstruir_contexto(
                ao_concluir=lambda _: self.app.toast(t("actions.toast_ctx_ok")),
                ao_falhar=lambda e: self.app.toast(t("actions.toast_ctx_erro"))):
            self.app.toast(t("actions.toast_ctx_start"))

    def _auditoria(self):
        self.app.salvar_editor()

        def _concluir(relatorio):
            if relatorio is None:
                self._fim("auditoria", t("actions.cancelled"))
                return
            self._fim("auditoria", t("actions.done"))
            self.app.toast(t("actions.toast_audit_ok"))
            JanelaAuditoria(self.app.root, relatorio, toast=self.app.toast)

        if acoes.executar_auditoria(ao_concluir=_concluir,
                                    ao_falhar=lambda e: (self._fim("auditoria", t("actions.failed"), False),
                                                         self.app.toast(t("actions.toast_audit_erro")))):
            self.app.toast(t("actions.toast_audit_start"))

    def _livro(self):
        if acoes.compilar_livro(
                ao_concluir=lambda caminho: self.app.toast(t("actions.toast_book_ok")),
                ao_falhar=lambda e: self.app.toast(t("actions.toast_book_erro", erro=e))):
            self.app.toast(t("actions.toast_book_start"))

    def _tamanho(self):
        self.app.salvar_editor()
        acoes.analisar_tamanho(
            ao_concluir=lambda analise: JanelaTamanhoProjeto(self.app.root, analise, toast_callback=self.app.toast),
            ao_falhar=lambda e: messagebox.showerror(t("actions.size_error_title"), str(e)))

    def _backup(self):
        def _ok(resultado):
            caminho, total = resultado
            self.app.toast(t("actions.toast_backup_ok", nome=caminho.name))
            messagebox.showinfo(t("actions.backup_done_title"), t("actions.backup_done", total=total, caminho=caminho))

        if acoes.criar_backup(ao_concluir=_ok, ao_falhar=lambda e: messagebox.showerror(t("actions.backup_error_title"), str(e))):
            self.app.toast(t("actions.toast_backup_start"))

    def _excluir_memorias(self):
        if not messagebox.askyesno(t("comum.confirmar"), t("actions.confirm_delete_memories")):
            return
        try:
            acoes.excluir_memorias()
        except Exception as e:
            messagebox.showerror(t("comum.erro"), str(e))
            return
        self.app.pagina("chat").recarregar_historico(forcar=True)
        self.app.toast(t("actions.toast_memories_deleted"))
