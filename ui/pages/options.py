"""
Página de Opções, em abas verticais:
  Geral   — idioma, comportamento, sobre e atualizações (valem para o programa todo)
  IA      — chave do Gemini, cache e a ordem dos modelos (antiga página Performance Gemini)
  Projeto — estilo, sistema de regras, segredos e automação (salvos dentro da pasta do projeto)
  Discord — conta do bot e regras por servidor

Tudo salva sozinho; um "✓ Salvo" discreto confirma. Só interface: leitura e gravação
ficam em core.config, engine.acoes, engine.style_manager e core.atualizacoes.
"""
import tkinter as tk
from tkinter import ttk, messagebox

import bot.runner as discord_runner
import core.atualizacoes as atualizacoes
import core.config as cfg
import core.i18n as i18n
import core.sistema as sistema
import core.tarefas as tarefas
import engine.acoes as acoes
import engine.style_manager as estilo
import ui.theme as tema
from core.i18n import t
from core.versao import VERSAO, URL_PROJETO
from ui.pages.models import PaginaModelos
from ui.widgets import PaginaBase, ColunaRolavel, cabecalho

ABAS = ("geral", "ia", "projeto", "discord")
CAMPOS_DISCORD = [
    ("discord_channels_knowledge", "options.discord_conhecimento", "options.discord_conhecimento_dica"),
    ("discord_prefix", "options.discord_prefixo", None),
    ("discord_roles_dm", "options.discord_cargos", None),
    ("discord_channels_allowed", "options.discord_permitidos", None),
    ("discord_channels_blocked", "options.discord_bloqueados", None),
    ("discord_cooldown_seconds", "options.discord_cooldown", None),
]
ESPERA_DIGITACAO_MS = 900


class PaginaOpcoes(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        topo = ttk.Frame(self)
        topo.pack(fill=tk.X)
        cabecalho(topo, t("options.titulo"), t("options.subtitulo")).pack_configure(side=tk.LEFT, fill=tk.X, expand=True)
        self.lbl_salvo = ttk.Label(topo, text="", style="Salvo.TLabel")
        self.lbl_salvo.pack(side=tk.RIGHT, padx=20)
        self._timer_salvo = None
        self._timers = {}

        corpo = ttk.Frame(self)
        corpo.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        lateral = ttk.Frame(corpo, width=190)
        lateral.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        lateral.pack_propagate(False)
        self.area = ttk.Frame(corpo)
        self.area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.botoes_aba, self.abas = {}, {}
        for aba in ABAS:
            botao = ttk.Button(lateral, text=t(f"options.aba.{aba}"), style="Aba.TButton",
                               command=lambda a=aba: self.mostrar_aba(a))
            botao.pack(fill=tk.X, pady=1)
            self.botoes_aba[aba] = botao
            quadro = ttk.Frame(self.area)
            quadro.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.abas[aba] = quadro

        self._montar_geral()
        self._montar_ia()
        self._montar_projeto()
        self._montar_discord()
        self.aba_atual = None
        self.mostrar_aba("geral")

    # ------------------------------------------------------------------
    # NAVEGAÇÃO, ROLAGEM E "✓ SALVO"
    # ------------------------------------------------------------------
    def mostrar_aba(self, aba):
        self.aba_atual = aba
        self.abas[aba].tkraise()
        for nome, botao in self.botoes_aba.items():
            botao.configure(style="AbaAtiva.TButton" if nome == aba else "Aba.TButton")
        if aba == "ia":
            self.modelos.atualizar()
            self._atualizar_status_cache()

    def ao_exibir(self):
        if self.aba_atual == "ia":
            self.modelos.atualizar()

    def projeto_alterado(self):
        self._preencher_projeto()

    def rolar(self, unidades):
        if self.aba_atual == "ia":
            self.modelos.rolar(unidades)
        else:
            self.colunas[self.aba_atual].rolar(unidades)

    def _salvo(self):
        self.lbl_salvo.config(text=t("options.salvo"))
        if self._timer_salvo:
            self.after_cancel(self._timer_salvo)
        self._timer_salvo = self.after(2200, lambda: self.lbl_salvo.config(text=""))

    def _ao_digitar(self, chave, funcao):
        """Salva depois que o usuário para de digitar (e não a cada tecla)."""
        if chave in self._timers:
            self.after_cancel(self._timers[chave])
        self._timers[chave] = self.after(ESPERA_DIGITACAO_MS, lambda: (self._timers.pop(chave, None), funcao()))

    # --- pequenos construtores ---
    @staticmethod
    def _rotulo(pai, texto, negrito=False):
        ttk.Label(pai, text=texto, font=("Segoe UI", 9, "bold") if negrito else ("Segoe UI", 10)).pack(
            anchor=tk.W, padx=12, pady=(8, 2))

    @staticmethod
    def _dica(pai, texto):
        ttk.Label(pai, text=texto, style="Dica.TLabel", wraplength=740, justify="left").pack(anchor=tk.W, padx=12, pady=(0, 4))

    @staticmethod
    def _combo(pai, opcoes, atual, ao_mudar):
        """Combobox de (id, rótulo)."""
        rotulos = [r for _, r in opcoes]
        combo = ttk.Combobox(pai, state="readonly", values=rotulos, font=("Segoe UI", 10))
        combo.set(dict(opcoes).get(atual, rotulos[0] if rotulos else ""))
        combo.pack(fill=tk.X, padx=12, pady=(0, 8))
        combo.bind("<<ComboboxSelected>>", lambda e: ao_mudar(opcoes[combo.current()][0]))
        return combo

    def _entrada_salva(self, pai, chave, valor, ao_salvar, oculta=False):
        """Campo que salva sozinho: ao parar de digitar e ao sair do campo."""
        var = tk.StringVar(value=valor)
        entrada = ttk.Entry(pai, textvariable=var, show="*" if oculta else "", font=("Segoe UI", 10))
        entrada.pack(fill=tk.X, padx=12, pady=(0, 8))
        salvar = lambda: (ao_salvar(var.get().strip()), self._salvo())
        entrada.bind("<KeyRelease>", lambda e: self._ao_digitar(chave, salvar))
        entrada.bind("<FocusOut>", lambda e: self._timers.get(chave) and (self.after_cancel(self._timers.pop(chave)), salvar()))
        return var

    def _nova_coluna(self, aba):
        coluna = ColunaRolavel(self.abas[aba])
        coluna.pack(fill=tk.BOTH, expand=True)
        self.colunas = getattr(self, "colunas", {})
        self.colunas[aba] = coluna
        ttk.Label(coluna.interno, text=t(f"options.aba_desc.{aba}"), style="Dica.TLabel", wraplength=760,
                  justify="left").pack(anchor=tk.W, padx=4, pady=(0, 12))
        return coluna

    # ------------------------------------------------------------------
    # GERAL
    # ------------------------------------------------------------------
    def _montar_geral(self):
        coluna = self._nova_coluna("geral")
        secao = coluna.nova_secao(t("options.idioma_titulo"), t("options.idioma_texto"))
        self._combo(secao, list(i18n.IDIOMAS.items()), i18n.idioma_ativo(), self._mudar_idioma)

        secao = coluna.nova_secao(t("options.comportamento_titulo"))
        self.var_requisicoes = tk.BooleanVar(value=bool(cfg.obter("abrir_requisicoes", True)))
        ttk.Checkbutton(secao, text=t("options.abrir_requisicoes"), variable=self.var_requisicoes,
                        command=lambda: (cfg.atualizar_configuracoes({"abrir_requisicoes": bool(self.var_requisicoes.get())}),
                                         self._salvo())).pack(anchor=tk.W, padx=12, pady=(10, 2))
        self._dica(secao, t("options.abrir_requisicoes_dica"))

        secao = coluna.nova_secao(t("options.sobre_titulo"))
        ttk.Label(secao, text=t("options.sobre_versao", versao=VERSAO), font=("Segoe UI", 10, "bold"),
                  foreground=tema.VERDE).pack(anchor=tk.W, padx=12, pady=(10, 4))
        self.var_verificar = tk.BooleanVar(value=atualizacoes.verificacao_automatica_ativa())
        ttk.Checkbutton(secao, text=t("options.sobre_verificar_auto"), variable=self.var_verificar,
                        command=lambda: (atualizacoes.definir_verificacao_automatica(self.var_verificar.get()), self._salvo())
                        ).pack(anchor=tk.W, padx=12, pady=(2, 6))
        linha = ttk.Frame(secao)
        linha.pack(fill=tk.X, padx=12, pady=(0, 8))
        self.btn_verificar = ttk.Button(linha, text=t("options.sobre_verificar_agora"), command=self._verificar_agora)
        self.btn_verificar.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(linha, text=t("options.sobre_pagina"), command=lambda: sistema.abrir_link(URL_PROJETO)).pack(side=tk.LEFT)
        self._dica(secao, t("options.sobre_legal"))
        ttk.Button(secao, text=t("options.sobre_legal_completo"),
                   command=lambda: self.app.mostrar_pagina("manual")).pack(anchor=tk.W, padx=12, pady=(2, 12))

    def _mudar_idioma(self, codigo):
        i18n.definir_idioma(codigo)
        estilo.aplicar_idioma()                       # modelos iniciais no novo idioma
        self._salvo()
        self.app.toast(t("options.toast_idioma", nome=i18n.IDIOMAS[codigo]))
        if codigo != i18n.idioma_interface():
            messagebox.showinfo(t("options.idioma_reiniciar_titulo"), t("options.idioma_reiniciar"))

    def _verificar_agora(self):
        self.btn_verificar.config(state=tk.DISABLED)
        self.app.toast(t("update.toast_verificando"))

        def _fim(nova):
            self.btn_verificar.config(state=tk.NORMAL)
            if nova:
                self.app.abrir_atualizacao()
            else:
                self.app.toast(t("update.toast_atualizado", versao=VERSAO))

        def _erro(e):
            self.btn_verificar.config(state=tk.NORMAL)
            self.app.toast(t("update.toast_erro", erro=e))

        tarefas.executar_em_segundo_plano(atualizacoes.verificar, ao_concluir=_fim, ao_falhar=_erro)

    # ------------------------------------------------------------------
    # IA (GEMINI)
    # ------------------------------------------------------------------
    def _montar_ia(self):
        quadro = self.abas["ia"]
        topo = ttk.Frame(quadro)
        topo.pack(fill=tk.X)
        ttk.Label(topo, text=t("options.aba_desc.ia"), style="Dica.TLabel", wraplength=760,
                  justify="left").pack(anchor=tk.W, padx=4, pady=(0, 12))
        secao = ttk.LabelFrame(topo, text=t("options.ia_chave_titulo"))
        secao.pack(fill=tk.X, padx=(4, 12), pady=(0, 6))
        self._dica(secao, t("options.ia_chave_dica"))
        self._entrada_salva(secao, "GOOGLE_API_KEY", cfg.credencial_para_edicao("GOOGLE_API_KEY"),
                            lambda v: (cfg.salvar_credenciais({"GOOGLE_API_KEY": v}), self._atualizar_status_cache()),
                            oculta=True)
        linha = ttk.Frame(secao)
        linha.pack(fill=tk.X, padx=12, pady=(0, 10))
        self.lbl_cache = ttk.Label(linha, text="", font=("Segoe UI", 9), wraplength=560, justify="left")
        self.lbl_cache.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(linha, text=t("options.cache_tentar"), command=self._reativar_cache).pack(side=tk.RIGHT)
        self.modelos = PaginaModelos(quadro, self.app)
        self.modelos.pack(fill=tk.BOTH, expand=True)

    def _atualizar_status_cache(self):
        status = acoes.status_cache_gemini()
        if status["sem_suporte"]:
            self.lbl_cache.config(text=t("options.cache_desativado", data=status["data"]), foreground=tema.AMARELO)
        else:
            self.lbl_cache.config(text=t("options.cache_ativo"), foreground=tema.SUAVE)

    def _reativar_cache(self):
        acoes.reativar_cache_gemini()
        self._atualizar_status_cache()
        self.app.toast(t("options.toast_cache"))

    # ------------------------------------------------------------------
    # PROJETO (salvo na pasta do projeto)
    # ------------------------------------------------------------------
    def _montar_projeto(self):
        self._nova_coluna("projeto")
        self._preencher_projeto()

    def _preencher_projeto(self):
        coluna = self.colunas["projeto"]
        for filho in coluna.interno.winfo_children()[1:]:       # mantém a descrição da aba
            filho.destroy()
        nome, _ = acoes.projeto_ativo()
        ttk.Label(coluna.interno, text=t("options.projeto_cabecalho", projeto=nome), foreground=tema.AZUL_CLARO,
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, padx=4, pady=(0, 12))

        secao = coluna.nova_secao(t("options.estilo_titulo"), t("options.estilo_texto"))
        for eixo, (atual, opcoes) in acoes.estilos_do_projeto().items():
            self._rotulo(secao, t(f"req.eixo.{eixo}"), negrito=True)
            self._combo(secao, opcoes, atual, lambda ident, e=eixo: self._mudar_estilo(e, ident))

        secao = coluna.nova_secao(t("options.sistema_titulo"), t("options.sistema_texto"))
        self._combo(secao, estilo.listar_sistemas(), estilo.sistema_ativo(), self._mudar_sistema)

        secao = coluna.nova_secao(t("options.segredos_titulo"), t("options.segredos_texto"))
        self._rotulo(secao, t("options.segredos_rotulo"), negrito=True)
        self._entrada_salva(secao, "termos_secretos", cfg.obter("termos_secretos", ""),
                            lambda v: cfg.atualizar_configuracoes({"termos_secretos": v}))
        self._dica(secao, t("options.segredos_dica"))

        secao = coluna.nova_secao(t("options.auto_titulo"))
        self.var_auto = tk.BooleanVar(value=bool(cfg.obter("auto_expander", False)))
        ttk.Checkbutton(secao, text=t("options.auto_texto"), variable=self.var_auto,
                        command=self._mudar_auto).pack(anchor=tk.W, padx=12, pady=(10, 12))

    def _mudar_estilo(self, eixo, ident):
        acoes.definir_estilo_do_projeto(eixo, ident)
        self._salvo()

    def _mudar_sistema(self, sistema_rpg):
        estilo.definir_sistema(sistema_rpg)
        self._salvo()

    def _mudar_auto(self):
        cfg.atualizar_configuracoes({"auto_expander": bool(self.var_auto.get())})
        self._salvo()

    # ------------------------------------------------------------------
    # DISCORD
    # ------------------------------------------------------------------
    def _montar_discord(self):
        coluna = self._nova_coluna("discord")
        secao = coluna.nova_secao(t("options.discord_conta_titulo"), t("options.discord_conta_dica"))
        self._rotulo(secao, t("options.cred_discord"), negrito=True)
        self._entrada_salva(secao, "DISCORD_TOKEN", cfg.credencial_para_edicao("DISCORD_TOKEN"),
                            lambda v: cfg.salvar_credenciais({"DISCORD_TOKEN": v}), oculta=True)
        self._rotulo(secao, t("options.cred_mestres"), negrito=True)
        self._entrada_salva(secao, "MESTRE_DISCORD_ID", cfg.credencial_para_edicao("MESTRE_DISCORD_ID"),
                            lambda v: cfg.salvar_credenciais({"MESTRE_DISCORD_ID": v}))

        secao = coluna.nova_secao(t("options.discord_titulo"), t("options.discord_regras_dica"))
        self._rotulo(secao, t("options.discord_servidor"), negrito=True)
        self.servidor = "global"
        self.combo_servidores = ttk.Combobox(secao, state="readonly", font=("Segoe UI", 10))
        self.combo_servidores.pack(fill=tk.X, padx=12, pady=(0, 8))
        self.combo_servidores.bind("<<ComboboxSelected>>", self._servidor_escolhido)
        self.vars_discord = {}
        for chave, rotulo, dica in CAMPOS_DISCORD:
            self._rotulo(secao, t(rotulo))
            if dica:
                self._dica(secao, t(dica))
            var = tk.StringVar()
            entrada = ttk.Entry(secao, textvariable=var, font=("Segoe UI", 10))
            entrada.pack(fill=tk.X, padx=12, pady=(0, 6))
            entrada.bind("<KeyRelease>", lambda e: self._ao_digitar("discord", self._salvar_discord))
            self.vars_discord[chave] = var
        ttk.Button(secao, text=t("options.discord_sync"), command=self._sincronizar).pack(fill=tk.X, padx=12, pady=(6, 12))
        self.atualizar_servidores()
        self._carregar_discord()

    def atualizar_servidores(self):
        self._mapa_servidores = {t("options.discord_global"): "global"}
        for gid, nome in cfg.servidores_conhecidos():
            self._mapa_servidores[f"🏰 {nome} ({gid})"] = gid
        self.combo_servidores["values"] = list(self._mapa_servidores)
        atual = next((r for r, g in self._mapa_servidores.items() if g == self.servidor), t("options.discord_global"))
        self.combo_servidores.set(atual)

    def _servidor_escolhido(self, _evento=None):
        self.servidor = self._mapa_servidores.get(self.combo_servidores.get(), "global")
        self._carregar_discord()

    def _carregar_discord(self):
        valores = cfg.valores_discord_para_edicao(self.servidor)
        for chave, var in self.vars_discord.items():
            var.set(str(valores.get(chave, "")))

    def _salvar_discord(self):
        dados = {k: v.get().strip() for k, v in self.vars_discord.items() if k != "discord_cooldown_seconds"}
        cooldown = self.vars_discord["discord_cooldown_seconds"].get().strip()
        if cooldown.isdigit():
            dados["discord_cooldown_seconds"] = int(cooldown)
        cfg.salvar_configuracao_discord(self.servidor, dados)
        self._salvo()

    def _sincronizar(self):
        iniciou = discord_runner.sincronizar_canais(
            self.servidor,
            ao_concluir=lambda r: self.app.toast(t("options.toast_sync_ok", canais=r[0], mensagens=r[1])),
            ao_falhar=lambda e: self.app.toast(t("options.toast_sync_erro")))
        self.app.toast(t("options.toast_sync_inicio") if iniciou else t("options.toast_sync_offline"))
