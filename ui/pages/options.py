"""Página de Opções: idioma, credenciais, Discord, segredos, estilo e automações."""
import tkinter as tk
from tkinter import ttk, messagebox

import bot.runner as discord_runner
import core.atualizacoes as atualizacoes
import engine.acoes as acoes
import core.config as cfg
import core.i18n as i18n
import core.sistema as sistema
import core.tarefas as tarefas
import engine.style_manager as estilo
import ui.theme as tema
from core.i18n import t
from core.versao import VERSAO, URL_PROJETO
from ui.widgets import PaginaBase, GradeRolavel, cabecalho

CAMPOS_DISCORD = [
    ("discord_channels_knowledge", "options.discord_conhecimento", "options.discord_conhecimento_dica"),
    ("discord_prefix", "options.discord_prefixo", None),
    ("discord_roles_dm", "options.discord_cargos", None),
    ("discord_channels_allowed", "options.discord_permitidos", None),
    ("discord_channels_blocked", "options.discord_bloqueados", None),
    ("discord_cooldown_seconds", "options.discord_cooldown", None),
]
CREDENCIAIS = [("GOOGLE_API_KEY", "options.cred_gemini", True), ("CLAUDE_TOKEN", "options.cred_claude", True),
               ("PRO_API_KEY", "options.cred_openai", True), ("DISCORD_TOKEN", "options.cred_discord", True),
               ("MESTRE_DISCORD_ID", "options.cred_mestres", False)]


class PaginaOpcoes(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("options.titulo"), t("options.subtitulo"))
        self.grade = GradeRolavel(self)
        self.grade.pack(fill=tk.BOTH, expand=True)
        self._caixa_idioma()
        self._caixa_credenciais()
        self._caixa_discord()
        self._caixa_segredos()
        self._caixa_estilo()
        self._caixa_automacao()
        self._caixa_sobre()
        self.grade.organizar()

    def rolar(self, unidades):
        self.grade.rolar(unidades)

    @staticmethod
    def _rotulo(caixa, texto, **kwargs):
        ttk.Label(caixa, text=texto, **kwargs).pack(anchor=tk.W, padx=10, pady=(6, 2))

    def _combo(self, caixa, opcoes, atual, ao_mudar):
        """Combobox de (id, rótulo). Devolve o widget."""
        rotulos = [r for _, r in opcoes]
        combo = ttk.Combobox(caixa, state="readonly", values=rotulos, font=("Segoe UI", 10))
        combo.set(dict(opcoes).get(atual, rotulos[0]))
        combo.pack(fill=tk.X, padx=10, pady=(0, 10))
        combo.bind("<<ComboboxSelected>>", lambda e: ao_mudar(opcoes[combo.current()][0]))
        return combo

    # ------------------------------------------------------------------
    def _caixa_idioma(self):
        caixa = self.grade.nova_caixa(t("options.idioma_titulo"))
        self._rotulo(caixa, t("options.idioma_texto"), wraplength=420)
        self._combo(caixa, list(i18n.IDIOMAS.items()), i18n.idioma_ativo(), self._mudar_idioma)

    def _mudar_idioma(self, codigo):
        i18n.definir_idioma(codigo)
        estilo.aplicar_idioma()                       # modelos e diretriz de estilo no novo idioma
        self.app.toast(t("options.toast_idioma", nome=i18n.IDIOMAS[codigo]))
        if codigo != i18n.idioma_interface():
            messagebox.showinfo(t("options.idioma_reiniciar_titulo"), t("options.idioma_reiniciar"))

    # ------------------------------------------------------------------
    def _caixa_credenciais(self):
        caixa = self.grade.nova_caixa(t("options.cred_titulo"))
        self._rotulo(caixa, t("options.provedor"))
        provedores = [(r, r) for r in cfg.PROVEDORES_IA]
        self._combo(caixa, provedores, cfg.provedor_ia_ativo(), self._mudar_provedor)
        self.entradas_cred = {}
        for chave, rotulo, oculto in CREDENCIAIS:
            self._rotulo(caixa, t(rotulo))
            entrada = ttk.Entry(caixa, show="*" if oculto else "", font=("Segoe UI", 10))
            entrada.insert(0, cfg.credencial_para_edicao(chave))
            entrada.pack(fill=tk.X, padx=10, pady=(0, 4))
            self.entradas_cred[chave] = entrada
        ttk.Button(caixa, text=t("options.cred_salvar"), command=self._salvar_credenciais).pack(anchor=tk.E, padx=10, pady=10)
        linha_cache = ttk.Frame(caixa)
        linha_cache.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.lbl_cache = ttk.Label(linha_cache, text="", font=("Segoe UI", 8), wraplength=300, justify="left")
        self.lbl_cache.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(linha_cache, text=t("options.cache_tentar"), command=self._reativar_cache).pack(side=tk.RIGHT)
        self._atualizar_status_cache()

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

    def _mudar_provedor(self, rotulo):
        cfg.definir_provedor_ia(rotulo)
        self.app.toast(t("options.toast_provedor", nome=rotulo))

    def _salvar_credenciais(self):
        cfg.salvar_credenciais({k: e.get().strip() for k, e in self.entradas_cred.items()})
        self.app.toast(t("options.toast_cred"))

    # ------------------------------------------------------------------
    def _caixa_discord(self):
        caixa = self.grade.nova_caixa(t("options.discord_titulo"))
        self._rotulo(caixa, t("options.discord_servidor"), font=("Segoe UI", 9, "bold"))
        self.servidor = "global"
        self.combo_servidores = ttk.Combobox(caixa, state="readonly", font=("Segoe UI", 10))
        self.combo_servidores.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.combo_servidores.bind("<<ComboboxSelected>>", self._servidor_escolhido)
        self.vars_discord = {}
        for chave, rotulo, dica in CAMPOS_DISCORD:
            self._rotulo(caixa, t(rotulo))
            if dica:
                ttk.Label(caixa, text=t(dica), font=("Segoe UI", 8), foreground=tema.SUAVE).pack(anchor=tk.W, padx=10)
            var = tk.StringVar()
            entrada = ttk.Entry(caixa, textvariable=var, font=("Segoe UI", 10))
            entrada.pack(fill=tk.X, padx=10, pady=(0, 4))
            entrada.bind("<KeyRelease>", lambda e: self._salvar_discord())
            self.vars_discord[chave] = var
        ttk.Button(caixa, text=t("options.discord_sync"), command=self._sincronizar).pack(fill=tk.X, padx=10, pady=10)
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

    def _sincronizar(self):
        iniciou = discord_runner.sincronizar_canais(
            self.servidor,
            ao_concluir=lambda r: self.app.toast(t("options.toast_sync_ok", canais=r[0], mensagens=r[1])),
            ao_falhar=lambda e: self.app.toast(t("options.toast_sync_erro")))
        self.app.toast(t("options.toast_sync_inicio") if iniciou else t("options.toast_sync_offline"))

    # ------------------------------------------------------------------
    def _caixa_segredos(self):
        caixa = self.grade.nova_caixa(t("options.segredos_titulo"))
        self._rotulo(caixa, t("options.segredos_rotulo"), font=("Segoe UI", 9, "bold"), foreground=tema.VERDE)
        ttk.Label(caixa, text=t("options.segredos_texto"), font=("Segoe UI", 8), foreground=tema.SUAVE,
                  wraplength=420).pack(anchor=tk.W, padx=10, pady=(0, 6))
        self.var_segredos = tk.StringVar(value=cfg.obter("termos_secretos", ""))
        entrada = ttk.Entry(caixa, textvariable=self.var_segredos, font=("Segoe UI", 10))
        entrada.pack(fill=tk.X, padx=10, pady=(0, 8))
        entrada.bind("<KeyRelease>", lambda e: cfg.atualizar_configuracoes({"termos_secretos": self.var_segredos.get().strip()}))
        ttk.Label(caixa, text=t("options.segredos_dica"), font=("Segoe UI", 8, "italic"),
                  foreground=tema.AZUL).pack(anchor=tk.W, padx=10, pady=(0, 10))

    def _caixa_estilo(self):
        caixa = self.grade.nova_caixa(t("options.tom_titulo"))
        self._rotulo(caixa, t("options.tom_texto"))
        self._combo(caixa, estilo.listar_perfis_tom(), estilo.perfil_tom_ativo(), self._mudar_tom)
        estilo.escrever_arquivo_estilo_tom()
        caixa = self.grade.nova_caixa(t("options.sistema_titulo"))
        self._rotulo(caixa, t("options.sistema_texto"))
        self._combo(caixa, estilo.listar_sistemas(), estilo.sistema_ativo(), self._mudar_sistema)

    def _mudar_tom(self, perfil):
        estilo.definir_perfil_tom(perfil)
        self.app.toast(t("options.toast_tom", nome=t(f"style.tom.{perfil}")))

    def _mudar_sistema(self, sistema):
        estilo.definir_sistema(sistema)
        self.app.toast(t("options.toast_sistema", nome=t(f"style.sistema.{sistema}")))

    def _caixa_automacao(self):
        caixa = self.grade.nova_caixa(t("options.auto_titulo"))
        self._rotulo(caixa, t("options.auto_texto"), wraplength=420)
        self.var_auto = tk.BooleanVar(value=bool(cfg.obter("auto_expander", False)))
        linha = ttk.Frame(caixa)
        linha.pack(anchor=tk.W, padx=10, pady=(0, 12))
        for valor, rotulo in ((False, t("comum.desabilitado")), (True, t("comum.habilitado"))):
            ttk.Radiobutton(linha, text=rotulo, value=valor, variable=self.var_auto,
                            command=self._mudar_auto).pack(side=tk.LEFT, padx=(0, 20))

    def _mudar_auto(self):
        ligado = bool(self.var_auto.get())
        cfg.atualizar_configuracoes({"auto_expander": ligado})
        self.app.toast(t("options.toast_auto", estado=t("comum.habilitado") if ligado else t("comum.desabilitado")))

    # ------------------------------------------------------------------
    def _caixa_sobre(self):
        caixa = self.grade.nova_caixa(t("options.sobre_titulo"))
        self._rotulo(caixa, t("options.sobre_versao", versao=VERSAO), font=("Segoe UI", 10, "bold"), foreground=tema.VERDE)
        self.var_verificar = tk.BooleanVar(value=atualizacoes.verificacao_automatica_ativa())
        ttk.Checkbutton(caixa, text=t("options.sobre_verificar_auto"), variable=self.var_verificar,
                        command=lambda: atualizacoes.definir_verificacao_automatica(self.var_verificar.get())
                        ).pack(anchor=tk.W, padx=10, pady=(4, 6))
        linha = ttk.Frame(caixa)
        linha.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.btn_verificar = ttk.Button(linha, text=t("options.sobre_verificar_agora"), command=self._verificar_agora)
        self.btn_verificar.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(linha, text=t("options.sobre_pagina"), command=lambda: sistema.abrir_link(URL_PROJETO)).pack(side=tk.LEFT)
        ttk.Label(caixa, text=t("options.sobre_legal"), font=("Segoe UI", 8), foreground=tema.SUAVE,
                  wraplength=420, justify="left").pack(anchor=tk.W, padx=10, pady=(4, 4))
        ttk.Button(caixa, text=t("options.sobre_legal_completo"),
                   command=lambda: self.app.mostrar_pagina("manual")).pack(anchor=tk.W, padx=10, pady=(0, 10))

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
