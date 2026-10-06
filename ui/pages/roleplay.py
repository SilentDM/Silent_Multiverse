"""Página de Roleplay: conversar com personas do mundo e gerar retratos."""
import tkinter as tk
from tkinter import ttk, simpledialog, filedialog, messagebox

from PIL import Image, ImageTk

import core.sistema as sistema
import core.tarefas as tarefas
import engine.persona_engine as pe
import ui.theme as tema
from core.i18n import t
from ui.dialogs.note import JanelaNota
from ui.widgets import PaginaBase, cabecalho, texto_rolavel, anexar_texto, substituir_texto, ajuda, caixa_com_ajuda


class PaginaRoleplay(PaginaBase):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        cabecalho(self, t("rp.titulo"), t("rp.subtitulo"))
        self.persona_atual = None
        self._falas = []                 # respostas do personagem; a tag "falaN" marca o texto da fala N
        self._caminho_retrato = None
        self._foto = None

        painel = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        painel.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # --- Ficha (esquerda) ---
        esquerda = caixa_com_ajuda(painel, t("rp.persona_ativa"), t("ajuda.rp.persona"))
        painel.add(esquerda, weight=1)
        topo = ttk.Frame(esquerda)
        topo.pack(fill=tk.X, padx=10, pady=8)
        self.combo = ttk.Combobox(topo, state="readonly", font=("Segoe UI", 10))
        self.combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.combo.bind("<<ComboboxSelected>>", lambda e: self._carregar(self.combo.get()))
        ttk.Button(topo, text=t("rp.nova"), command=self._nova_persona).pack(side=tk.RIGHT)

        moldura = tk.Frame(esquerda, bg=tema.CARTAO)
        moldura.pack(fill=tk.X, padx=10, pady=(6, 2))
        self.lbl_retrato = tk.Label(moldura, bg=tema.CARTAO, cursor="hand2")
        self.lbl_retrato.bind("<Double-1>", lambda e: self._abrir_retrato())
        self.lbl_retrato.bind("<Button-3>", self._menu_retrato)
        self.menu_retrato = tk.Menu(self, tearoff=0, bg=tema.PAINEL, fg=tema.TEXTO, activebackground=tema.VERDE_ESCURO)
        self.menu_retrato.add_command(label=t("rp.menu_abrir"), command=self._abrir_retrato)
        self.menu_retrato.add_command(label=t("rp.menu_salvar"), command=self._salvar_retrato)
        self.menu_retrato.add_separator()
        self.menu_retrato.add_command(label=t("rp.menu_revelar"), command=self._revelar_retrato)

        linha_retrato = ttk.Frame(esquerda)
        linha_retrato.pack(fill=tk.X, padx=10, pady=(2, 6))
        self.btn_retrato = ttk.Button(linha_retrato, text=t("rp.gerar_retrato"), command=self._gerar_retrato)
        self.btn_retrato.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ajuda(linha_retrato, t("ajuda.rp.retrato")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(esquerda, text=t("rp.caracteristicas"), font=("Segoe UI", 8, "bold"),
                  foreground=tema.SUAVE).pack(anchor=tk.W, padx=10, pady=(4, 2))
        self.ficha = texto_rolavel(esquerda, fonte=("Consolas", 10))
        self.ficha.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        # --- Diálogo (direita) ---
        direita = caixa_com_ajuda(painel, t("rp.dialogo"), t("ajuda.rp.dialogo"))
        painel.add(direita, weight=2)
        self.chat = texto_rolavel(direita)
        self.chat.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        self.chat.tag_config("usuario", foreground=tema.AZUL, font=("Segoe UI", 10, "bold"))
        self.chat.tag_config("npc", foreground=tema.AMARELO, font=("Segoe UI", 10, "bold"))
        self.chat.tag_config("sistema", foreground=tema.SUAVE, font=("Segoe UI", 9, "italic"))
        self.chat.bind("<Button-3>", self._menu_fala)
        self.menu_fala = tk.Menu(self, tearoff=0, bg=tema.PAINEL, fg=tema.TEXTO, activebackground=tema.VERDE_ESCURO)
        entrada = ttk.Frame(direita)
        entrada.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.entrada = ttk.Entry(entrada, font=("Segoe UI", 10))
        self.entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.entrada.bind("<Return>", lambda e: self._falar())
        ttk.Button(entrada, text=t("rp.btn_depoimento"), command=self._depoimento_ultima_fala).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(entrada, text=t("rp.falar"), command=self._falar).pack(side=tk.RIGHT)

        self._atualizar_lista()

    # --- lista e carregamento ---
    def _atualizar_lista(self, selecionar=None):
        nomes = pe.listar_personas_disponiveis()
        self.combo["values"] = nomes
        if nomes:
            alvo = selecionar if selecionar in nomes else nomes[0]
            self.combo.set(alvo)
            self._carregar(alvo)
        else:
            self.combo.set("")
            substituir_texto(self.ficha, t("rp.nenhuma"))

    def _carregar(self, nome):
        if not nome:
            return
        self.persona_atual = nome
        dados = pe.ficha(nome)
        substituir_texto(self.ficha, dados["markdown"])
        substituir_texto(self.chat, "")
        self._falas = []
        anexar_texto(self.chat, t("rp.narrador") + ": ", "sistema")
        anexar_texto(self.chat, t("rp.frente_a_frente", nome=nome) + "\n\n")
        for item in dados["historico"]:
            if item.get("autor") == pe.AUTOR_INTERLOCUTOR:
                anexar_texto(self.chat, t("rp.voce") + ": ", "usuario")
                anexar_texto(self.chat, f"{item.get('texto', '')}\n\n")
            else:
                anexar_texto(self.chat, f"{nome}: ", "npc")
                self._anexar_fala(item.get("texto", ""))
        self._exibir_retrato(dados["retrato"])

    def _exibir_retrato(self, caminho):
        self._caminho_retrato = caminho
        if caminho:
            try:
                imagem = Image.open(caminho).resize((150, 150), Image.Resampling.LANCZOS)
                self._foto = ImageTk.PhotoImage(imagem)
                self.lbl_retrato.config(image=self._foto)
                self.lbl_retrato.pack(anchor="center", pady=(4, 6))
                self.btn_retrato.config(text=t("rp.recriar_retrato"))
                return
            except Exception:
                pass
        self._caminho_retrato, self._foto = None, None
        self.lbl_retrato.config(image="")
        self.lbl_retrato.pack_forget()
        self.btn_retrato.config(text=t("rp.gerar_retrato"))

    # --- criar persona ---
    def _nova_persona(self):
        nome = simpledialog.askstring(t("rp.nova_titulo"), t("rp.nova_nome"), parent=self)
        if not nome or not nome.strip():
            return
        descricao = simpledialog.askstring(t("rp.diretrizes_titulo"), t("rp.diretrizes", nome=nome), parent=self)
        if descricao is None:
            return
        self.app.toast(t("rp.toast_forjando", nome=nome))
        tarefas.executar_em_segundo_plano(
            pe.forjar_nova_persona, nome.strip(), descricao.strip(),
            ao_concluir=lambda salvo: (self.app.toast(t("rp.toast_pronta", nome=salvo)), self._atualizar_lista(salvo)),
            ao_falhar=lambda e: self.app.toast(t("rp.toast_erro_forjar")))

    # --- diálogo ---
    def _falar(self):
        if not self.persona_atual:
            self.app.toast(t("rp.selecione"))
            return
        mensagem = self.entrada.get().strip()
        if not mensagem:
            return
        self.entrada.delete(0, tk.END)
        persona = self.persona_atual
        anexar_texto(self.chat, t("rp.voce") + ": ", "usuario")
        anexar_texto(self.chat, f"{mensagem}\n\n")
        anexar_texto(self.chat, f"{persona}: ", "npc")
        anexar_texto(self.chat, "...\n\n", "sistema")

        def _trocar_reticencias(texto, tag=None):
            if self.persona_atual != persona:
                return  # o usuário mudou de persona; a resposta já ficou salva no histórico dela
            self.chat.config(state=tk.NORMAL)
            self.chat.delete("end-3l", "end")
            self.chat.config(state=tk.DISABLED)
            anexar_texto(self.chat, f"{persona}: " if tag is None else t("rp.narrador") + ": ", "npc" if tag is None else "sistema")
            if tag is None:
                self._anexar_fala(texto)
            else:
                anexar_texto(self.chat, f"{texto}\n\n", tag)

        tarefas.executar_em_segundo_plano(
            pe.dialogar_com_persona, persona, mensagem,
            ao_concluir=_trocar_reticencias,
            ao_falhar=lambda e: _trocar_reticencias(t("rp.sem_resposta", erro=e), "sistema"))

    # --- depoimentos (Notas do Mestre) ---
    def _anexar_fala(self, texto):
        anexar_texto(self.chat, f"{texto}\n\n", f"fala{len(self._falas)}")
        self._falas.append(texto)

    def _menu_fala(self, evento):
        indice = self.chat.index(f"@{evento.x},{evento.y}")
        fala = next((self._falas[int(tag[4:])] for tag in self.chat.tag_names(indice)
                     if tag.startswith("fala") and tag[4:].isdigit() and int(tag[4:]) < len(self._falas)), None)
        if fala is None:
            return
        self.menu_fala.delete(0, tk.END)
        self.menu_fala.add_command(label=t("rp.menu_depoimento"), command=lambda: self._salvar_depoimento(fala))
        self.menu_fala.post(evento.x_root, evento.y_root)

    def _depoimento_ultima_fala(self):
        if not self._falas:
            self.app.toast(t("rp.sem_fala"))
            return
        self._salvar_depoimento(self._falas[-1])

    def _salvar_depoimento(self, texto):
        persona = self.persona_atual or ""
        JanelaNota(self.app, texto, "roleplay", autor=persona, nomes=[persona],
                   arquivo_atual=self.app.pagina("editor").sessao.arquivo_atual)

    # --- retrato ---
    def _gerar_retrato(self):
        if not self.persona_atual:
            self.app.toast(t("rp.selecione"))
            return
        persona = self.persona_atual
        self.btn_retrato.config(state=tk.DISABLED)
        self.app.toast(t("rp.toast_gerando_retrato", nome=persona))

        def _pronto(caminho):
            self.btn_retrato.config(state=tk.NORMAL)
            if not caminho:
                self.app.toast(t("rp.toast_retrato_falhou"))
                return
            if self.persona_atual == persona:
                self._exibir_retrato(caminho)
            self.app.toast(t("rp.toast_retrato_ok", nome=persona))

        tarefas.executar_em_segundo_plano(pe.gerar_retrato, persona, ao_concluir=_pronto,
                                          ao_falhar=lambda e: _pronto(None))

    def _menu_retrato(self, evento):
        if self._caminho_retrato:
            self.menu_retrato.post(evento.x_root, evento.y_root)

    def _abrir_retrato(self):
        if self._caminho_retrato:
            sistema.abrir_no_sistema(self._caminho_retrato)

    def _revelar_retrato(self):
        if self._caminho_retrato:
            sistema.revelar_no_explorer(self._caminho_retrato)

    def _salvar_retrato(self):
        if not self._caminho_retrato:
            return
        destino = filedialog.asksaveasfilename(
            title=t("rp.salvar_retrato_titulo"), initialfile=pe.nome_sugerido_retrato(self.persona_atual or "persona"),
            defaultextension=".png", filetypes=[("PNG", "*.png"), (t("comum.todos_arquivos"), "*.*")], parent=self)
        if destino:
            try:
                pe.exportar_retrato(self._caminho_retrato, destino)
                self.app.toast(t("rp.toast_retrato_exportado"))
            except Exception as e:
                messagebox.showerror(t("comum.erro_salvar"), str(e), parent=self)
