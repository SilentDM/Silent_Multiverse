"""Janela "Salvar como nota": guarda uma fala do Silent ou do Roleplay nas Notas do Mestre de um arquivo."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import engine.acoes as acoes
import engine.arquivos as arq
import ui.theme as tema
from core.i18n import t, tc


class JanelaNota(tk.Toplevel):
    def __init__(self, app, texto: str, origem: str, autor: str = "", nomes=(), arquivo_atual: str = None):
        super().__init__(app.root)
        self.app = app
        self.origem, self.autor = origem, autor
        self.title(t("nota.janela_titulo"))
        self.geometry("720x480")
        self.minsize(520, 360)
        self.configure(bg=tema.FUNDO)
        self.transient(app.root)

        chave_explicacao = "nota.explicacao_roleplay" if origem == "roleplay" else "nota.explicacao"
        tk.Label(self, text=t(chave_explicacao, nome=autor), bg=tema.FUNDO, fg=tema.SUAVE, font=("Segoe UI", 9),
                 justify="left", wraplength=680).pack(anchor=tk.W, padx=15, pady=(12, 6))

        linha = ttk.Frame(self)
        linha.pack(fill=tk.X, padx=15, pady=(0, 6))
        ttk.Label(linha, text=t("nota.destino")).pack(side=tk.LEFT)
        self._destinos = acoes.sugerir_destinos_nota(texto, arquivo_atual, nomes)
        self.combo = ttk.Combobox(linha, state="readonly", values=[self._rotulo(c) for c in self._destinos])
        self.combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        if self._destinos:
            self.combo.current(0)
        ttk.Button(linha, text=t("nota.procurar"), command=self._procurar).pack(side=tk.RIGHT)

        botoes = ttk.Frame(self)
        botoes.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=10)      # antes do texto: nunca some
        self.txt = tk.Text(self, wrap=tk.WORD, font=("Segoe UI", 10), bg=tema.PAINEL, fg=tema.TEXTO,
                           insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#3a3a3a",
                           highlightcolor=tema.VERDE)
        self.txt.pack(fill=tk.BOTH, expand=True, padx=15, pady=4)
        self.txt.insert("1.0", texto.strip())

        ttk.Button(botoes, text=t("nota.salvar"), command=lambda: self._salvar(False)).pack(side=tk.LEFT)
        ttk.Button(botoes, text=t("nota.salvar_aplicar"), command=lambda: self._salvar(True)).pack(side=tk.LEFT, padx=6)
        ttk.Button(botoes, text=t("comum.fechar"), command=self.destroy).pack(side=tk.RIGHT)

    @staticmethod
    def _rotulo(caminho):
        return arq.nome(caminho)

    def _procurar(self):
        caminho = filedialog.askopenfilename(parent=self, title=t("nota.procurar"), initialdir=acoes.projeto_ativo()[1],
                                             filetypes=[("Markdown", "*.md")])
        if caminho:
            self._destinos.insert(0, caminho)
            self.combo["values"] = [self._rotulo(c) for c in self._destinos]
            self.combo.current(0)

    def _salvar(self, aplicar: bool):
        indice = self.combo.current()
        if indice < 0:
            messagebox.showinfo(t("nota.janela_titulo"), t("nota.escolha_destino"), parent=self)
            return
        destino = self._destinos[indice]
        try:
            acoes.adicionar_nota(destino, self.txt.get("1.0", "end"), self.origem, self.autor)
        except Exception as e:
            messagebox.showerror(t("comum.erro"), str(e), parent=self)
            return
        self.app.toast(t("nota.toast_salva", nome=arq.nome(destino)))
        editor = self.app.pagina("editor")
        editor.atualizar_arvore()
        if editor.sessao.eh_atual(destino):
            editor.recarregar_arquivo(destino)
        self.destroy()
        if aplicar:
            self.app.abrir_requisicao("melhorar", destino)
            self.app.pagina("requisicoes").definir_objetivo(tc("nota.objetivo_aplicar"))
