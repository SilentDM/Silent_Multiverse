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


class Dica:
    """Dica flutuante (tooltip) que aparece ao parar o mouse sobre um widget."""

    def __init__(self, widget, texto: str, atraso: int = 500, condicao=None, largura: int = 320, destaque=False):
        self.widget, self.texto, self.atraso = widget, texto, atraso
        self.condicao, self.largura, self.destaque = condicao, largura, destaque
        self._agendado = self._janela = None
        widget.bind("<Enter>", self._agendar, add="+")
        widget.bind("<Leave>", self._esconder, add="+")
        widget.bind("<ButtonPress>", self._esconder, add="+")

    def _agendar(self, _evento=None):
        self._esconder()
        if self.condicao is None or self.condicao():
            self._agendado = self.widget.after(self.atraso, self._mostrar)

    def mostrar_agora(self, _evento=None):
        self._esconder()
        if self.condicao is None or self.condicao():
            self._mostrar()

    def _mostrar(self):
        self._agendado = None
        try:
            self._janela = tk.Toplevel(self.widget)
            self._janela.overrideredirect(True)
            self._janela.attributes("-topmost", True)
            borda = tema.VERDE_ESCURO if self.destaque else "#3a3a3a"
            tk.Label(self._janela, text=self.texto, bg=tema.PAINEL, fg=tema.TEXTO, font=("Segoe UI", 9),
                     padx=10 if self.destaque else 8, pady=6 if self.destaque else 4, justify="left",
                     wraplength=self.largura, highlightthickness=1, highlightbackground=borda).pack()
            self._janela.update_idletasks()
            x = min(self.widget.winfo_rootx(), self.widget.winfo_screenwidth() - self._janela.winfo_width() - 8)
            y = self.widget.winfo_rooty() - self._janela.winfo_height() - 4
            if y < 0:
                y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            self._janela.geometry(f"+{x}+{y}")
        except tk.TclError:
            self._janela = None

    def _esconder(self, _evento=None):
        if self._agendado:
            try:
                self.widget.after_cancel(self._agendado)
            except tk.TclError:
                pass
            self._agendado = None
        if self._janela is not None:
            try:
                self._janela.destroy()
            except tk.TclError:
                pass
            self._janela = None


# ----------------------------------------------------------------------
# AJUDA CONTEXTUAL: o círculo com "?" ao lado de uma opção. Passar o mouse
# (ou clicar) mostra o que a opção faz. Opções → Geral liga/desliga todos.
# ----------------------------------------------------------------------
COR_AJUDA, COR_AJUDA_ATIVA = "#6b7280", tema.VERDE
_icones_ajuda = []                       # rótulos criados (para esconder/mostrar sem reiniciar)
_preferencia_ajuda = {"visivel": None}   # lida da configuração uma vez só


def ajuda_visivel() -> bool:
    if _preferencia_ajuda["visivel"] is None:
        import core.config as cfg
        _preferencia_ajuda["visivel"] = bool(cfg.obter("mostrar_ajuda", True))
    return _preferencia_ajuda["visivel"]


def definir_ajuda_visivel(visivel: bool):
    """Salva a preferência e mostra/esconde na hora todos os ícones de ajuda abertos."""
    import core.config as cfg
    cfg.atualizar_configuracoes({"mostrar_ajuda": bool(visivel)})
    _preferencia_ajuda["visivel"] = bool(visivel)
    atualizar_ajudas()


def ajuda(parent, texto: str, bg=None):
    """Ícone "?" com a explicação 'texto' (as chaves ajuda.* do locale). Devolve o rótulo (o chamador posiciona)."""
    import ui.icones as icones
    janela = parent.winfo_toplevel()
    rotulo = tk.Label(parent, bg=bg or tema.FUNDO, bd=0, padx=2, cursor="question_arrow")
    rotulo.janela_icones = janela
    dica = rotulo.dica = Dica(rotulo, texto, atraso=150, condicao=ajuda_visivel, largura=360, destaque=True)
    rotulo.bind("<Button-1>", dica.mostrar_agora, add="+")
    rotulo.bind("<Enter>", lambda e: _pintar_ajuda(rotulo, COR_AJUDA_ATIVA), add="+")
    rotulo.bind("<Leave>", lambda e: _pintar_ajuda(rotulo, COR_AJUDA), add="+")
    _pintar_ajuda(rotulo, COR_AJUDA)
    _icones_ajuda.append(rotulo)
    return rotulo


def _pintar_ajuda(rotulo, cor):
    import ui.icones as icones
    try:
        if ajuda_visivel():
            rotulo.config(image=icones.ajuda(rotulo.janela_icones, cor))
        else:
            rotulo.config(image=icones.vazio(rotulo.janela_icones))
    except tk.TclError:
        pass


def icones_ajuda_abertos() -> list:
    """Os ícones de ajuda que ainda existem (esquece os de janelas já fechadas)."""
    vivos = []
    for rotulo in _icones_ajuda:
        try:
            if rotulo.winfo_exists():
                vivos.append(rotulo)
        except tk.TclError:
            pass
    _icones_ajuda[:] = vivos
    return vivos


def atualizar_ajudas():
    """Reaplica a preferência mostrar/esconder em todos os ícones de ajuda abertos."""
    for rotulo in icones_ajuda_abertos():
        _pintar_ajuda(rotulo, COR_AJUDA)


def rotulo_com_ajuda(parent, texto: str, ajuda_texto: str, **opcoes_rotulo):
    """Frame com um rótulo e o "?" logo depois (para usar no lugar de um ttk.Label em grids e linhas)."""
    quadro = ttk.Frame(parent)
    ttk.Label(quadro, text=texto, **opcoes_rotulo).pack(side=tk.LEFT)
    ajuda(quadro, ajuda_texto).pack(side=tk.LEFT, padx=(3, 0))
    return quadro


def caixa_com_ajuda(parent, titulo: str, ajuda_texto: str):
    """ttk.LabelFrame cujo título tem o "?" ao lado."""
    cabeca = ttk.Frame(parent)
    ttk.Label(cabeca, text=titulo.strip(), style="TLabelframe.Label").pack(side=tk.LEFT)
    ajuda(cabeca, ajuda_texto).pack(side=tk.LEFT, padx=(4, 0))
    return ttk.LabelFrame(parent, labelwidget=cabeca)


class LinhaFluida(tk.Frame):
    """Organiza os filhos da esquerda para a direita, quebrando a linha quando falta largura."""

    def __init__(self, parent, espaco=4, **kwargs):
        kwargs.setdefault("bg", tema.FUNDO)
        super().__init__(parent, **kwargs)
        self.espaco = espaco
        self._largura = 0
        self.bind("<Configure>", self._ao_redimensionar)

    def _ao_redimensionar(self, evento):
        if evento.width != self._largura:
            self._largura = evento.width
            self.organizar()

    def organizar(self):
        largura = self._largura or self.winfo_width() or 800
        x = y = altura_linha = 0
        for filho in self.winfo_children():
            filho.update_idletasks()
            w, h = filho.winfo_reqwidth(), filho.winfo_reqheight()
            if x and x + w > largura:
                x, y, altura_linha = 0, y + altura_linha + self.espaco, 0
            filho.place(x=x, y=y)
            x += w + self.espaco
            altura_linha = max(altura_linha, h)
        self.configure(height=max(1, y + altura_linha))


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

    def nova_caixa(self, titulo: str, explicacao: str = "", estilo: str = "TLabelframe") -> ttk.LabelFrame:
        caixa = ttk.LabelFrame(self.interno, text=titulo, style=estilo)
        if explicacao:
            ttk.Label(caixa, text=explicacao, style="Dica.TLabel", wraplength=420,
                      justify="left").pack(anchor=tk.W, padx=10, pady=(6, 0))
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


class ColunaRolavel(ttk.Frame):
    """
    Área rolável com seções empilhadas numa coluna de largura confortável para leitura.
    Uso: coluna = ColunaRolavel(pai); secao = coluna.nova_secao(" Título ", "explicação opcional")
    """
    LARGURA_MAXIMA = 820

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=tema.FUNDO, highlightthickness=0, bd=0)
        barra = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.interno = ttk.Frame(self.canvas)
        self.interno.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._janela = self.canvas.create_window((0, 0), window=self.interno, anchor="nw")
        self.canvas.configure(yscrollcommand=barra.set)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(
            self._janela, width=min(e.width, self.LARGURA_MAXIMA)))
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        barra.pack(side=tk.RIGHT, fill=tk.Y)

    def nova_secao(self, titulo: str, explicacao: str = "") -> ttk.LabelFrame:
        secao = ttk.LabelFrame(self.interno, text=titulo)
        secao.pack(fill=tk.X, padx=(4, 12), pady=(0, 14))
        if explicacao:
            ttk.Label(secao, text=explicacao, style="Dica.TLabel", wraplength=self.LARGURA_MAXIMA - 60,
                      justify="left").pack(anchor=tk.W, padx=12, pady=(8, 2))
        return secao

    def limpar(self):
        for filho in self.interno.winfo_children():
            filho.destroy()

    def rolar(self, unidades: int):
        self.canvas.yview_scroll(unidades, "units")


class PaginaBase(ttk.Frame):
    """Toda página recebe o 'app' (para toasts, status e navegação) e pode ser rolada pela roda do mouse."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

    def ao_exibir(self):
        """Chamado quando a página passa a ser exibida."""

    def rolar(self, unidades: int):
        """Rolagem pela roda do mouse (páginas com GradeRolavel sobrescrevem)."""
