"""Componentes visuais reutilizados pelas páginas (sem lógica de negócio)."""
import tkinter as tk
from tkinter import ttk, scrolledtext

import ui.theme as tema


def cabecalho(parent, titulo: str, subtitulo: str = ""):
    frame = ttk.Frame(parent)
    frame.pack(fill=tk.X, padx=18, pady=(18, 10))
    ttk.Label(frame, text=titulo, font=("Segoe UI", 14, "bold"), foreground=tema.VERDE).pack(anchor=tk.W)
    if subtitulo:
        ttk.Label(frame, text=subtitulo, font=("Segoe UI", 9), foreground=tema.SUAVE).pack(anchor=tk.W, pady=(3, 0))
    return frame


def mostrar_toast(root, mensagem: str, duracao: int = 3500):
    """Aviso flutuante no canto inferior direito da janela principal."""
    def _criar():
        try:
            popup = tk.Toplevel(root)
            popup.overrideredirect(True)
            popup.attributes("-topmost", True)
            popup.configure(bg=tema.PAINEL)
            moldura = tk.Frame(popup, bg=tema.PAINEL, highlightbackground=tema.VERDE, highlightthickness=1)
            moldura.pack(fill=tk.BOTH, expand=True)
            tk.Label(moldura, text=mensagem, bg=tema.PAINEL, fg=tema.TEXTO, font=("Segoe UI", 9, "bold"),
                     padx=14, pady=10, wraplength=360, justify="left").pack()
            popup.update_idletasks()
            x = max(10, root.winfo_x() + root.winfo_width() - popup.winfo_width() - 25)
            y = max(10, root.winfo_y() + root.winfo_height() - popup.winfo_height() - 35)
            popup.geometry(f"+{x}+{y}")
            popup.after(duracao, popup.destroy)
        except tk.TclError:
            pass
    root.after(0, _criar)


def texto_rolavel(parent, fonte=("Segoe UI", 10), somente_leitura=True, **kwargs):
    widget = scrolledtext.ScrolledText(
        parent, wrap=tk.WORD, font=fonte, bg=tema.PAINEL, fg=tema.TEXTO, insertbackground="white",
        selectbackground=tema.VERDE_ESCURO, selectforeground="white", bd=0, highlightthickness=0, **kwargs
    )
    if somente_leitura:
        widget.config(state=tk.DISABLED)
    return widget


def anexar_texto(widget, texto: str, tag=None, rolar=True):
    """Acrescenta texto a um ScrolledText somente leitura."""
    widget.config(state=tk.NORMAL)
    widget.insert(tk.END, texto, tag)
    if rolar:
        widget.see(tk.END)
    widget.config(state=tk.DISABLED)


def substituir_texto(widget, texto: str, somente_leitura=True):
    widget.config(state=tk.NORMAL)
    widget.delete("1.0", tk.END)
    widget.insert("1.0", texto)
    if somente_leitura:
        widget.config(state=tk.DISABLED)


class GradeRolavel(ttk.Frame):
    """
    Área rolável com quadros (LabelFrames) dispostos em 1 ou 2 colunas conforme a largura.
    Uso: grade = GradeRolavel(pagina); caixa = grade.nova_caixa(" Título "); ... ; grade.organizar()
    """
    LARGURA_DUAS_COLUNAS = 720

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=tema.FUNDO, highlightthickness=0, bd=0)
        barra = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.interno = ttk.Frame(self.canvas)
        self.interno.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._janela = self.canvas.create_window((0, 0), window=self.interno, anchor="nw")
        self.canvas.configure(yscrollcommand=barra.set)
        self.canvas.bind("<Configure>", self._ao_redimensionar)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 0), pady=(0, 15))
        barra.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 15), pady=(0, 15))
        self.caixas = []
        self._colunas = 0

    def nova_caixa(self, titulo: str) -> ttk.LabelFrame:
        caixa = ttk.LabelFrame(self.interno, text=titulo)
        self.caixas.append(caixa)
        return caixa

    def rolar(self, unidades: int):
        self.canvas.yview_scroll(unidades, "units")

    def _ao_redimensionar(self, evento):
        self.canvas.itemconfig(self._janela, width=evento.width)
        self.organizar()

    def organizar(self, forcar=False):
        largura = self.canvas.winfo_width()
        if largura < 100:
            largura = 800
        colunas = 2 if largura >= self.LARGURA_DUAS_COLUNAS else 1
        if colunas == self._colunas and not forcar:
            return
        self._colunas = colunas
        for c in range(2):
            self.interno.columnconfigure(c, weight=1 if c < colunas else 0)
        for i, caixa in enumerate(self.caixas):
            caixa.grid_forget()
            caixa.grid(row=i // colunas, column=i % colunas, sticky="nsew", padx=8, pady=8)


class PaginaBase(ttk.Frame):
    """Toda página recebe o 'app' (para toasts, status e navegação) e pode ser rolada pela roda do mouse."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

    def ao_exibir(self):
        """Chamado quando a página passa a ser exibida."""

    def rolar(self, unidades: int):
        """Rolagem pela roda do mouse (páginas com GradeRolavel sobrescrevem)."""
