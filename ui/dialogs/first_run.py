"""
Assistente de primeira execução: Idioma → Chave do Gemini → Pasta do projeto → Pronto.

Aparece sozinho só para quem ainda não configurou a chave (e pode ser reaberto em Opções → Geral).
Os textos do assistente seguem o idioma escolhido no passo 1 na hora; o resto da interface
troca ao reiniciar, e o assistente oferece reiniciar no fim.
"""
import tkinter as tk
from tkinter import ttk, filedialog

import core.i18n as i18n
import core.sistema as sistema
import engine.acoes as acoes
import engine.style_manager as estilo
import ui.theme as tema

PASSOS = ("idioma", "chave", "projeto", "pronto")


class AssistenteInicial(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.idioma = i18n.idioma_ativo()
        self.passo = 0
        self.var_idioma = tk.StringVar(value=self.idioma)
        self.var_chave = tk.StringVar()
        self.pasta = acoes.projeto_ativo()[1]
        self.configure(bg=tema.FUNDO)
        self.transient(app.root)
        largura, altura = 720, 520
        x = app.root.winfo_rootx() + max(0, (app.root.winfo_width() - largura) // 2)
        y = app.root.winfo_rooty() + max(0, (app.root.winfo_height() - altura) // 3)
        self.geometry(f"{largura}x{altura}+{x}+{y}")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._pular)

        self.lbl_titulo = tk.Label(self, bg=tema.FUNDO, fg=tema.VERDE, font=("Segoe UI", 16, "bold"), anchor="w")
        self.lbl_titulo.pack(fill=tk.X, padx=24, pady=(20, 4))
        self.quadro_passos = tk.Frame(self, bg=tema.FUNDO)
        self.quadro_passos.pack(fill=tk.X, padx=24, pady=(0, 10))
        ttk.Separator(self, orient="horizontal").pack(fill=tk.X, padx=24)
        self.corpo = ttk.Frame(self)
        self.corpo.pack(fill=tk.BOTH, expand=True, padx=24, pady=14)

        rodape = ttk.Frame(self)
        rodape.pack(fill=tk.X, padx=24, pady=(0, 18))
        self.btn_pular = ttk.Button(rodape, command=self._pular, style="Ferramenta.TButton")
        self.btn_pular.pack(side=tk.LEFT)
        self.btn_proximo = ttk.Button(rodape, command=self._proximo, style="Primario.TButton")
        self.btn_proximo.pack(side=tk.RIGHT)
        self.btn_voltar = ttk.Button(rodape, command=self._voltar)
        self.btn_voltar.pack(side=tk.RIGHT, padx=8)

        self._mostrar()
        self.grab_set()
        self.focus_force()

    def tx(self, chave, **variaveis):
        """Texto no idioma escolhido no passo 1 (não no da interface)."""
        return i18n.traduzir(chave, self.idioma, **variaveis)

    # ------------------------------------------------------------------
    def _mostrar(self):
        for filho in self.corpo.winfo_children():
            filho.destroy()
        for filho in self.quadro_passos.winfo_children():
            filho.destroy()
        self.title(self.tx("wizard.titulo"))
        self.lbl_titulo.config(text=self.tx("wizard.titulo"))
        for i, passo in enumerate(PASSOS):
            cor = tema.VERDE if i == self.passo else (tema.TEXTO if i < self.passo else tema.SUAVE)
            fonte = ("Segoe UI", 9, "bold") if i == self.passo else ("Segoe UI", 9)
            marca = "✓" if i < self.passo else str(i + 1)
            tk.Label(self.quadro_passos, text=f"{marca}  {self.tx('wizard.passo.' + passo)}", bg=tema.FUNDO, fg=cor,
                     font=fonte).pack(side=tk.LEFT, padx=(0, 22))
        getattr(self, f"_passo_{PASSOS[self.passo]}")()
        self.btn_pular.config(text=self.tx("wizard.pular"))
        self.btn_voltar.config(text=self.tx("wizard.voltar"), state=tk.NORMAL if self.passo else tk.DISABLED)
        ultimo = self.passo == len(PASSOS) - 1
        self.btn_proximo.config(text=self.tx("wizard.comecar" if ultimo else "wizard.proximo"))

    def _texto(self, chave, **variaveis):
        ttk.Label(self.corpo, text=self.tx(chave, **variaveis), wraplength=660, justify="left",
                  font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(0, 10))

    def _dica(self, chave, **variaveis):
        ttk.Label(self.corpo, text=self.tx(chave, **variaveis), style="Dica.TLabel", wraplength=660,
                  justify="left").pack(anchor=tk.W, pady=(6, 0))

    def _passo_idioma(self):
        self._texto("wizard.idioma_texto")
        for codigo, nome in i18n.IDIOMAS.items():
            ttk.Radiobutton(self.corpo, text=nome, value=codigo, variable=self.var_idioma,
                            command=self._idioma_escolhido).pack(anchor=tk.W, padx=8, pady=4)
        self._dica("wizard.idioma_dica")

    def _idioma_escolhido(self):
        self.idioma = self.var_idioma.get()
        self._mostrar()

    def _passo_chave(self):
        self._texto("wizard.chave_texto")
        ttk.Button(self.corpo, text=self.tx("wizard.btn_ai_studio"),
                   command=lambda: sistema.abrir_link(acoes.URL_CHAVE_GEMINI)).pack(anchor=tk.W, pady=(0, 12))
        ttk.Label(self.corpo, text=self.tx("wizard.chave_rotulo")).pack(anchor=tk.W)
        entrada = ttk.Entry(self.corpo, textvariable=self.var_chave, show="*", font=("Segoe UI", 10))
        entrada.pack(fill=tk.X, pady=(2, 0))
        entrada.focus_set()
        if acoes.tem_chave_gemini() and not self.var_chave.get():
            self._dica("wizard.chave_ja_existe")
        self._dica("wizard.chave_pular")

    def _passo_projeto(self):
        self._texto("wizard.projeto_texto")
        ttk.Button(self.corpo, text=self.tx("wizard.btn_escolher_pasta"), command=self._escolher_pasta).pack(anchor=tk.W)
        self.lbl_pasta = ttk.Label(self.corpo, text=self.tx("wizard.projeto_atual", caminho=self.pasta),
                                   foreground=tema.AZUL_CLARO, wraplength=660, justify="left")
        self.lbl_pasta.pack(anchor=tk.W, pady=(10, 0))
        self._dica("wizard.projeto_dica")

    def _escolher_pasta(self):
        pasta = filedialog.askdirectory(parent=self, title=self.tx("wizard.btn_escolher_pasta"), initialdir=self.pasta)
        if pasta:
            self.pasta = pasta
            self.lbl_pasta.config(text=self.tx("wizard.projeto_atual", caminho=self.pasta))

    def _passo_pronto(self):
        self._texto("wizard.pronto_texto")
        if self.idioma != i18n.idioma_interface():
            self._dica("wizard.reiniciar_aviso")

    # ------------------------------------------------------------------
    def _voltar(self):
        if self.passo:
            self.passo -= 1
            self._mostrar()

    def _proximo(self):
        if self.passo < len(PASSOS) - 1:
            self.passo += 1
            self._mostrar()
        else:
            self._concluir()

    def _aplicar(self):
        """Grava o que foi escolhido (idioma, chave e projeto)."""
        if self.idioma != i18n.idioma_ativo():
            i18n.definir_idioma(self.idioma)
            estilo.aplicar_idioma()
        acoes.salvar_chave_gemini(self.var_chave.get())
        if self.pasta and self.pasta != acoes.projeto_ativo()[1]:
            self.app.trocar_projeto(self.pasta)
        acoes.concluir_assistente()

    def _concluir(self):
        self._aplicar()
        reiniciar = self.idioma != i18n.idioma_interface()
        self.grab_release()
        self.destroy()
        if reiniciar:
            self.app.reiniciar()

    def _pular(self):
        acoes.concluir_assistente()
        self.grab_release()
        self.destroy()
