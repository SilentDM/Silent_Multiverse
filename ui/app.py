"""
Janela principal: barra lateral, troca de páginas, barra de status e bandeja.

Só interface. Logs, estado das tarefas e do Discord chegam pelo barramento de
eventos (core.eventos); ações são chamadas nos módulos de lógica.
"""
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pystray
from PIL import Image

import bot.runner as discord_runner
import core.atualizacoes as atualizacoes
import core.eventos as ev
import core.modelos_gemini as modelos
import core.sistema as sistema
import core.tarefas as tarefas
import engine.acoes as acoes
import ui.gui_logger as gl
import ui.icones as icones
import ui.theme as tema
from core.i18n import t
from core.versao import VERSAO
from ui.pages.actions import PaginaAcoes
from ui.pages.chat import PaginaChat
from ui.pages.council import PaginaConselho
from ui.pages.editor import PaginaEditor
from ui.pages.log import PaginaLog
from ui.pages.manual import PaginaManual
from ui.pages.options import PaginaOpcoes
from ui.pages.requests import PaginaRequisicoes
from ui.pages.roleplay import PaginaRoleplay
from ui.pages.worldbuilder import PaginaWorldBuilder
from ui.widgets import mostrar_toast, Dica

# Menu lateral em grupos; "sistema" fica no rodapé. Requisições não tem botão próprio:
# aparece como sub-item do Editor enquanto há um pedido aberto.
GRUPOS_NAV = [("escrever", ["editor"]), ("criar", ["worldbuilder", "council", "roleplay", "chat"]),
              ("projeto", ["actions"])]
GRUPO_RODAPE = ("sistema", ["options", "log", "manual"])
ICONES_NAV = {"editor": "✎", "worldbuilder": "◈", "council": "⚖", "roleplay": "♟", "chat": "◎",
              "actions": "⚒", "options": "⚙", "log": "≡", "manual": "§"}
CLASSES_PAGINAS = {
    "editor": PaginaEditor, "requisicoes": PaginaRequisicoes, "worldbuilder": PaginaWorldBuilder, "actions": PaginaAcoes,
    "chat": PaginaChat, "roleplay": PaginaRoleplay, "council": PaginaConselho,
    "options": PaginaOpcoes, "log": PaginaLog, "manual": PaginaManual,
}
COR_ICONE = "#9a9a9a"
QUADROS_SPINNER = ["◐", "◓", "◑", "◒"]


class SilentApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.paginas = {}
        self.botoes_nav = {}
        self.pagina_atual = None
        self.tamanho_fonte = 11
        self._acoes_rodando = []
        self._quadro_spinner = 0
        self._spinner_ativo = False

        tarefas.definir_despachante(root.after)
        self._configurar_janela()
        tema.aplicar_tema(root)

        self._montar_barra_status()
        self._montar_layout()
        self._conectar_eventos()
        self._configurar_atalhos()

        self.mostrar_pagina("editor")
        discord_runner.iniciar(ao_descobrir_servidores=self._servidores_descobertos)
        tarefas.executar_em_segundo_plano(modelos.atualizar_se_necessario)
        tarefas.executar_em_segundo_plano(atualizacoes.verificar_na_inicializacao)
        self._iniciar_bandeja()

    # ------------------------------------------------------------------
    # JANELA E LAYOUT
    # ------------------------------------------------------------------
    def _configurar_janela(self):
        self.root.title(f"Silent Multiverse Nexus {VERSAO}")
        self.root.geometry("1300x700")
        self.root.minsize(1050, 550)
        self.root.state("zoomed")
        self.root.configure(bg=tema.FUNDO)
        icone = sistema.caminho_icone()
        if icone:
            try:
                self.root.iconbitmap(str(icone))
            except tk.TclError:
                pass
        self.root.protocol("WM_DELETE_WINDOW", self.minimizar_para_bandeja)

    def _montar_layout(self):
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        lateral = tk.Frame(container, bg=tema.FUNDO_SIDEBAR, width=200)
        lateral.grid(row=0, column=0, sticky="ns")
        lateral.pack_propagate(False)
        tk.Label(lateral, text="🜂 Silent Console", bg=tema.FUNDO_SIDEBAR, fg=tema.VERDE,
                 font=("Segoe UI", 13, "bold")).pack(anchor=tk.W, padx=16, pady=(22, 26))
        self._montar_seletor_projeto(lateral)

        for grupo, chaves in GRUPOS_NAV:
            self._titulo_grupo(lateral, grupo)
            for chave in chaves:
                self._botao_nav(lateral, chave)
                if chave == "editor":
                    # Sub-item que só aparece enquanto há uma Requisição aberta
                    self.btn_requisicao = ttk.Button(lateral, style="NavSub.TButton",
                                                     command=lambda: self.mostrar_pagina("requisicoes"))
                    self.botoes_nav["requisicoes"] = self.btn_requisicao

        self.lbl_discord = tk.Label(lateral, text=t("discord.estado.conectando"), bg=tema.FUNDO_SIDEBAR, fg=tema.TEXTO,
                                    font=("Segoe UI", 8, "bold"), anchor="w", justify="left", wraplength=175)
        self.lbl_discord.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=(4, 10))
        ttk.Separator(lateral, orient="horizontal").pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(6, 0))
        for chave in reversed(GRUPO_RODAPE[1]):
            self._botao_nav(lateral, chave, lado=tk.BOTTOM)
        self._titulo_grupo(lateral, GRUPO_RODAPE[0], lado=tk.BOTTOM)

        area = ttk.Frame(container)
        area.grid(row=0, column=1, sticky="nsew")
        # A página de Log é criada primeiro para já receber as mensagens das outras
        for chave in ["log"] + [c for c in CLASSES_PAGINAS if c != "log"]:
            pagina = CLASSES_PAGINAS[chave](area, self)
            pagina.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.paginas[chave] = pagina

    @staticmethod
    def _titulo_grupo(parent, grupo, lado=tk.TOP):
        tk.Label(parent, text=t(f"nav.grupo.{grupo}").upper(), bg=tema.FUNDO_SIDEBAR, fg=tema.SUAVE,
                 font=("Segoe UI", 7, "bold"), anchor="w").pack(side=lado, fill=tk.X, padx=18, pady=(10, 2))

    def _botao_nav(self, parent, chave, lado=tk.TOP):
        botao = ttk.Button(parent, text=f"  {t(f'nav.{chave}')}", style="Nav.TButton", compound="left",
                           image=icones.icone(self.root, ICONES_NAV[chave], COR_ICONE), command=lambda: self.mostrar_pagina(chave))
        botao.pack(side=lado, fill=tk.X, padx=8, pady=1)
        self.botoes_nav[chave] = botao

    def requisicao_aberta(self, nome: str = None):
        """Mostra (com o nome do arquivo) ou esconde o sub-item Requisição do menu."""
        if nome:
            nome = nome[:-3] if nome.lower().endswith(".md") else nome
            if len(nome) > 18:
                nome = nome[:17] + "…"
            self.btn_requisicao.config(text=t("nav.requisicao_aberta", nome=nome))
            self.btn_requisicao.pack(fill=tk.X, padx=(22, 8), pady=1, after=self.botoes_nav["editor"])
        else:
            self.btn_requisicao.pack_forget()

    def _montar_seletor_projeto(self, parent):
        quadro = tk.Frame(parent, bg=tema.FUNDO_SIDEBAR)
        quadro.pack(fill=tk.X, padx=12, pady=(0, 15))
        tk.Label(quadro, text=t("app.projeto_ativo"), bg=tema.FUNDO_SIDEBAR, fg=tema.SUAVE,
                 font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, pady=(0, 2))
        linha = tk.Frame(quadro, bg=tema.FUNDO_SIDEBAR)
        linha.pack(fill=tk.X)
        self.combo_projetos = ttk.Combobox(linha, state="readonly", font=("Segoe UI", 9))
        self.combo_projetos.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.combo_projetos.bind("<<ComboboxSelected>>", self._projeto_selecionado)
        ttk.Button(linha, text="📁", width=3, command=self._procurar_projeto).pack(side=tk.RIGHT)
        self._atualizar_lista_projetos()

    def _atualizar_lista_projetos(self):
        self._recentes = acoes.projetos_recentes()
        self.combo_projetos["values"] = list(self._recentes.keys())
        self.combo_projetos.set(acoes.projeto_ativo()[0])

    def _projeto_selecionado(self, _evento=None):
        caminho = self._recentes.get(self.combo_projetos.get())
        if caminho:
            self.trocar_projeto(caminho)

    def _procurar_projeto(self):
        pasta = filedialog.askdirectory(title=t("app.escolher_projeto"), initialdir=acoes.projeto_ativo()[1])
        if pasta:
            self.trocar_projeto(pasta)

    def trocar_projeto(self, caminho):
        self.salvar_editor()
        try:
            nome = acoes.trocar_projeto(caminho)
        except Exception as e:
            messagebox.showerror(t("app.erro_projeto_titulo"), t("app.erro_projeto", erro=e))
            return
        self._atualizar_lista_projetos()
        self.lbl_status_projeto.config(text=t("app.status_projeto", projeto=nome))
        for pagina in self.paginas.values():
            if hasattr(pagina, "projeto_alterado"):
                pagina.projeto_alterado()
        self.toast(t("app.toast_projeto", projeto=nome))

    # ------------------------------------------------------------------
    # BARRA DE STATUS + SPINNER (dirigido pelos eventos "acao.estado")
    # ------------------------------------------------------------------
    def _montar_barra_status(self):
        barra = tk.Frame(self.root, bg=tema.FUNDO_SIDEBAR, height=28)
        barra.pack(side=tk.BOTTOM, fill=tk.X)
        self.lbl_status_projeto = tk.Label(barra, text=t("app.status_projeto", projeto=acoes.projeto_ativo()[0]),
                                           bg=tema.FUNDO_SIDEBAR, fg=tema.VERDE, font=("Segoe UI", 9))
        self.lbl_status_projeto.pack(side=tk.LEFT, padx=12)
        ttk.Separator(barra, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, pady=4)
        self.lbl_status_estatisticas = tk.Label(barra, text=t("app.nenhum_arquivo"), bg=tema.FUNDO_SIDEBAR,
                                                fg=tema.SUAVE, font=("Segoe UI", 9))
        self.lbl_status_estatisticas.pack(side=tk.LEFT, padx=12)
        # Zoom do texto: A− tamanho A+
        zoom = tk.Frame(barra, bg=tema.FUNDO_SIDEBAR)
        zoom.pack(side=tk.RIGHT, padx=(4, 10))
        for texto, delta in (("A−", -1), (None, 0), ("A+", 1)):
            if texto is None:
                self.lbl_zoom = tk.Label(zoom, text=str(self.tamanho_fonte), bg=tema.FUNDO_SIDEBAR, fg=tema.SUAVE,
                                         font=("Segoe UI", 8), width=3)
                self.lbl_zoom.pack(side=tk.LEFT)
                continue
            rotulo = tk.Label(zoom, text=texto, bg=tema.FUNDO_SIDEBAR, fg=tema.TEXTO, font=("Segoe UI", 9, "bold"),
                              cursor="hand2", padx=4)
            rotulo.pack(side=tk.LEFT)
            rotulo.bind("<Button-1>", lambda e, d=delta: self.alterar_fonte(d))
            Dica(rotulo, t("app.zoom_dica"))
        ttk.Separator(barra, orient="vertical").pack(side=tk.RIGHT, fill=tk.Y, pady=4)

        # Barra de tarefas: uma etiqueta por tarefa em andamento, cada uma com o seu ✕ (parar só ela)
        self.lbl_status_tarefa = tk.Label(barra, text=t("app.pronto"), bg=tema.FUNDO_SIDEBAR, fg=tema.VERDE,
                                          font=("Segoe UI", 9, "bold"))
        self.lbl_status_tarefa.pack(side=tk.RIGHT, padx=12)
        self.btn_parar_tudo = tk.Label(barra, text=t("app.parar_tudo"), bg=tema.FUNDO_SIDEBAR, fg=tema.VERMELHO,
                                       font=("Segoe UI", 9, "bold"), cursor="hand2", padx=8)
        self.btn_parar_tudo.bind("<Button-1>", lambda e: self.parar_tudo())
        self.quadro_tarefas = tk.Frame(barra, bg=tema.FUNDO_SIDEBAR)
        self.quadro_tarefas.pack(side=tk.RIGHT)
        self._chips = {}
        # Aparece só quando há uma versão nova no GitHub
        self.lbl_atualizacao = tk.Label(barra, text="", bg=tema.FUNDO_SIDEBAR, fg=tema.AMARELO,
                                        font=("Segoe UI", 9, "bold", "underline"), cursor="hand2")
        self.lbl_atualizacao.bind("<Button-1>", lambda e: self.abrir_atualizacao())
        self._nova_versao = None

    def atualizar_estatisticas(self, est: dict = None):
        if not est:
            self.lbl_status_estatisticas.config(text=t("app.nenhum_arquivo"), fg=tema.SUAVE)
            return
        self.lbl_status_estatisticas.config(fg=tema.TEXTO, text=t(
            "app.estatisticas", palavras=f"{est['palavras']:,}", caracteres=f"{est['caracteres']:,}",
            linhas=f"{est['linhas']:,}", tokens=f"{est['tokens']:,}"))

    def _estado_acao(self, dados):
        nome = dados["acao"]
        if dados["rodando"]:
            if nome not in self._acoes_rodando:
                self._acoes_rodando.append(nome)
                self._criar_chip(nome)
            if not self._spinner_ativo:
                self._spinner_ativo = True
                self._animar_spinner()
        else:
            if nome in self._acoes_rodando:
                self._acoes_rodando.remove(nome)
            chip = self._chips.pop(nome, None)
            if chip is not None:
                chip[0].destroy()
        self._atualizar_barra_tarefas()

    def _criar_chip(self, nome):
        chip = tk.Frame(self.quadro_tarefas, bg=tema.PAINEL, highlightthickness=1, highlightbackground="#2d2d2d")
        chip.pack(side=tk.LEFT, padx=3, pady=3)
        rotulo = tk.Label(chip, text=acoes.nome_tarefa(nome), bg=tema.PAINEL, fg=tema.AZUL, font=("Segoe UI", 8, "bold"),
                          padx=6)
        rotulo.pack(side=tk.LEFT)
        fechar = tk.Label(chip, text="✕", bg=tema.PAINEL, fg=tema.SUAVE, font=("Segoe UI", 8, "bold"), cursor="hand2",
                          padx=4)
        fechar.pack(side=tk.LEFT)
        fechar.bind("<Button-1>", lambda e: self._parar_tarefa(nome))
        fechar.bind("<Enter>", lambda e: fechar.config(fg=tema.VERMELHO))
        fechar.bind("<Leave>", lambda e: fechar.config(fg=tema.SUAVE))
        Dica(fechar, t("app.parar_tarefa_dica"))
        self._chips[nome] = (chip, rotulo)

    def _atualizar_barra_tarefas(self):
        if self._acoes_rodando:
            self.lbl_status_tarefa.pack_forget()
            if len(self._acoes_rodando) > 1:
                self.btn_parar_tudo.pack(side=tk.RIGHT, before=self.quadro_tarefas)
            else:
                self.btn_parar_tudo.pack_forget()
        else:
            self._spinner_ativo = False
            self.btn_parar_tudo.pack_forget()
            self.lbl_status_tarefa.pack(side=tk.RIGHT, padx=12, before=self.quadro_tarefas)

    def _parar_tarefa(self, nome):
        acoes.parar(nome)
        chip = self._chips.get(nome)
        if chip is not None:
            chip[1].config(fg=tema.AMARELO)
        self.toast(t("app.toast_parando_tarefa", tarefa=acoes.nome_tarefa(nome)))

    def parar_tudo(self):
        acoes.parar_tudo()
        self.toast(t("actions.toast_stopping"))

    def _animar_spinner(self):
        if not self._spinner_ativo or not self._acoes_rodando:
            return
        quadro = QUADROS_SPINNER[self._quadro_spinner % len(QUADROS_SPINNER)]
        self._quadro_spinner += 1
        for nome, (_chip, rotulo) in self._chips.items():
            rotulo.config(text=f"{quadro} {acoes.nome_tarefa(nome)}")
        self.root.after(120, self._animar_spinner)

    # ------------------------------------------------------------------
    # EVENTOS, LOG E ATALHOS
    # ------------------------------------------------------------------
    def _conectar_eventos(self):
        log = self.paginas["log"]
        ev.inscrever_log(lambda msg: tarefas.na_interface(log.adicionar, msg))
        ev.inscrever_evento("acao.estado", lambda d: tarefas.na_interface(self._estado_acao, d))
        ev.inscrever_evento("discord.estado", lambda e: tarefas.na_interface(self._estado_discord, e))
        ev.inscrever_evento("atualizacao.disponivel", lambda n: tarefas.na_interface(self._atualizacao_disponivel, n))
        # print()/erros de qualquer módulo também viram mensagens do barramento
        # (chegam ao Log e ao log ao vivo do WorldBuilder)
        sys.stdout = gl.GuiOutput(ev.log)
        sys.stderr = gl.GuiOutput(ev.log)
        self.root.bind_all("<MouseWheel>", self._roda_do_mouse)

    def _estado_discord(self, estado):
        cores = {"online": tema.VERDE, "erro": tema.VERMELHO, "desativado": tema.SUAVE, "conectando": tema.AMARELO}
        self.lbl_discord.config(text=t(f"discord.estado.{estado}"), fg=cores.get(estado, tema.TEXTO))

    def _atualizacao_disponivel(self, nova):
        primeira_vez = self._nova_versao is None
        self._nova_versao = nova
        self.lbl_atualizacao.config(text=t("update.status", versao=nova.versao))
        self.lbl_atualizacao.pack(side=tk.RIGHT, padx=12)
        if primeira_vez:
            self.toast(t("update.toast_disponivel", versao=nova.versao))

    def abrir_atualizacao(self):
        nova = self._nova_versao
        if nova and messagebox.askyesno(t("update.perguntar_titulo"),
                                        t("update.perguntar", versao=nova.versao, atual=VERSAO)):
            sistema.abrir_link(nova.url)

    def _servidores_descobertos(self, servidores):
        self.paginas["options"].atualizar_servidores()
        self.toast(t("discord.toast_servidores", total=len(servidores)))

    def _roda_do_mouse(self, evento):
        try:
            if evento.widget.winfo_toplevel() is not self.root:
                return
        except (AttributeError, tk.TclError):
            return
        pagina = self.paginas.get(self.pagina_atual)
        if pagina is not None:
            pagina.rolar(int(-1 * (evento.delta / 120)))

    def _configurar_atalhos(self):
        self.root.bind("<Control-KeyPress-equal>", lambda e: self.alterar_fonte(1))
        self.root.bind("<Control-KeyPress-plus>", lambda e: self.alterar_fonte(1))
        self.root.bind("<Control-KeyPress-minus>", lambda e: self.alterar_fonte(-1))
        self.root.bind("<Control-MouseWheel>", lambda e: self.alterar_fonte(1 if e.delta > 0 else -1))

    def alterar_fonte(self, delta: int):
        self.tamanho_fonte = max(8, min(24, self.tamanho_fonte + delta))
        self.lbl_zoom.config(text=str(self.tamanho_fonte))
        for pagina in self.paginas.values():
            if hasattr(pagina, "ajustar_fonte"):
                pagina.ajustar_fonte(self.tamanho_fonte)

    # ------------------------------------------------------------------
    # SERVIÇOS PARA AS PÁGINAS
    # ------------------------------------------------------------------
    def mostrar_pagina(self, chave: str):
        if chave not in self.paginas:
            return
        self.pagina_atual = chave
        pagina = self.paginas[chave]
        pagina.ao_exibir()
        pagina.tkraise()
        for nome, botao in self.botoes_nav.items():
            ativo = nome == chave
            if nome == "requisicoes":
                botao.configure(style="NavSubActive.TButton" if ativo else "NavSub.TButton")
            else:
                botao.configure(style="NavActive.TButton" if ativo else "Nav.TButton",
                                image=icones.icone(self.root, ICONES_NAV[nome], tema.VERDE if ativo else COR_ICONE))

    def abrir_requisicao(self, tipo: str, caminho: str):
        """Abre a aba Requisições para um pedido de nível médio sobre o arquivo."""
        self.paginas["requisicoes"].abrir(tipo, caminho)
        self.mostrar_pagina("requisicoes")

    def pagina(self, chave: str):
        return self.paginas[chave]

    def toast(self, mensagem: str):
        mostrar_toast(self.root, mensagem)

    def salvar_editor(self):
        editor = self.paginas.get("editor")
        if editor is not None:
            editor.salvar_agora()

    # ------------------------------------------------------------------
    # BANDEJA DO SISTEMA
    # ------------------------------------------------------------------
    def _iniciar_bandeja(self):
        try:
            icone = sistema.caminho_icone()
            imagem = Image.open(icone) if icone else Image.new("RGB", (64, 64), color=(16, 185, 129))
            menu = pystray.Menu(
                pystray.MenuItem(t("tray.abrir"), self._restaurar_da_bandeja, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(t("tray.encerrar"), self.encerrar),
            )
            self.bandeja = pystray.Icon("SilentMultiverse", imagem, t("tray.dica"), menu)
            self.bandeja.run_detached()
        except Exception as e:
            ev.log(t("tray.erro", erro=e))
            self.bandeja = None

    def minimizar_para_bandeja(self):
        self.salvar_editor()
        self.root.withdraw()
        self.toast(t("tray.toast_minimizado"))
        sistema.liberar_memoria()

    def _restaurar_da_bandeja(self, *_):
        def _restaurar():
            self.root.deiconify()
            self.root.state("zoomed")
            self.root.lift()
            self.root.focus_force()
        tarefas.na_interface(_restaurar)

    def encerrar(self, *_):
        ev.log(t("tray.log_encerrando"))
        if getattr(self, "bandeja", None):
            try:
                self.bandeja.stop()
            except Exception:
                pass
        discord_runner.parar()
        tarefas.na_interface(self._destruir)

    def _destruir(self):
        self.salvar_editor()
        self.root.destroy()


def main():
    root = tk.Tk()
    SilentApp(root)
    root.mainloop()
