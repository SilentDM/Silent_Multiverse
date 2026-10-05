"""Tema escuro (ttk) do programa. Puramente visual."""
from tkinter import ttk

FUNDO = "#121212"
FUNDO_SIDEBAR = "#0a0a0a"
CARTAO = "#18181c"
PAINEL = "#1e1e1e"
TEXTO = "#e3e3e3"
SUAVE = "#888888"
VERDE = "#10b981"
VERDE_ESCURO = "#0f766e"
AZUL = "#60a5fa"
AZUL_CLARO = "#38bdf8"
AMARELO = "#f59e0b"
VERMELHO = "#ef4444"
LARANJA = "#f97316"


def aplicar_tema(root):
    style = ttk.Style()
    style.theme_use('clam')

    root.option_add('*TCombobox*Listbox.background', '#252526')
    root.option_add('*TCombobox*Listbox.foreground', '#ffffff')
    root.option_add('*TCombobox*Listbox.selectBackground', '#0f766e')
    root.option_add('*TCombobox*Listbox.selectForeground', '#ffffff')
    root.option_add('*TCombobox*Listbox.font', ('Segoe UI', 10))

    style.configure('.',
        background='#121212',
        foreground='#e3e3e3',
        fieldbackground='#1e1e1e',
        font=('Segoe UI', 10),
        bordercolor='#2d2d2d',
        lightcolor='#121212',
        darkcolor='#121212'
    )
    style.map('.',
        background=[('active', '#2d2d2d'), ('disabled', '#121212')],
        foreground=[('disabled', '#6b6b6b')]
    )

    style.configure('TPanedwindow', background='#121212')
    style.configure('Sash', background='#2d2d2d', bordercolor='#2d2d2d', sashthickness=3)

    # Cartões com o MESMO fundo dos textos e linhas dentro deles (antes ficavam "caixinhas" escuras atrás de cada texto)
    style.configure('TLabelframe', background='#121212', bordercolor='#2d2d2d', borderwidth=1, relief='solid')
    style.configure('TLabelframe.Label', background='#121212', foreground='#10b981', font=('Segoe UI', 10, 'bold'))
    style.configure('Dica.TLabel', foreground='#888888', font=('Segoe UI', 9))
    style.configure('Salvo.TLabel', foreground='#10b981', font=('Segoe UI', 9, 'bold'))

    style.configure('TButton',
        background='#252526', foreground='#e3e3e3', bordercolor='#2d2d2d',
        lightcolor='#2d2d2d', darkcolor='#121212', borderwidth=1, padding=6
    )
    style.map('TButton',
        background=[('active', '#333333'), ('pressed', '#121212')],
        foreground=[('active', '#ffffff')]
    )

    style.configure('TEntry', fieldbackground='#252526', foreground='#ffffff', bordercolor='#2d2d2d', lightcolor='#252526', darkcolor='#252526')

    style.configure('TCombobox',
        fieldbackground='#252526',
        background='#252526',
        foreground='#ffffff',
        bordercolor='#2d2d2d',
        lightcolor='#252526',
        darkcolor='#252526',
        arrowcolor='#e3e3e3'
    )
    style.map('TCombobox',
        fieldbackground=[('readonly', '#252526'), ('focus', '#252526'), ('active', '#252526')],
        foreground=[('readonly', '#ffffff'), ('focus', '#ffffff'), ('active', '#ffffff')],
        selectbackground=[('readonly', '#0f766e'), ('focus', '#0f766e')],
        selectforeground=[('readonly', '#ffffff'), ('focus', '#ffffff')]
    )

    style.configure('Treeview', background='#1e1e1e', foreground='#e3e3e3', fieldbackground='#1e1e1e', bordercolor='#2d2d2d', borderwidth=1, rowheight=24)
    style.map('Treeview',
        background=[('selected', '#0f766e')],
        foreground=[('selected', '#ffffff')]
    )
    style.configure('Heading', background='#121212', foreground='#10b981', bordercolor='#2d2d2d', font=('Segoe UI', 9, 'bold'))
    style.map('Heading', background=[('active', '#2d2d2d')])

    style.configure('Vertical.TScrollbar', background='#252526', troughcolor='#121212', bordercolor='#2d2d2d', lightcolor='#252526', darkcolor='#252526', arrowcolor='#e3e3e3')
    style.map('Vertical.TScrollbar', background=[('active', '#2d2d2d')])

    style.configure('Nav.TButton',
        background='#121212', foreground='#cccccc', borderwidth=0,
        anchor='w', padding=(16, 12), font=('Segoe UI', 10)
    )
    style.map('Nav.TButton', background=[('active', '#1e1e1e')])

    style.configure('NavActive.TButton',
        background='#1e1e1e', foreground='#10b981', borderwidth=0,
        anchor='w', padding=(16, 12), font=('Segoe UI', 10, 'bold')
    )
    style.map('NavActive.TButton', background=[('active', '#1e1e1e')])

    # Abas verticais (Opções)
    style.configure('Aba.TButton', background='#121212', foreground='#bbbbbb', borderwidth=0,
                    anchor='w', padding=(14, 10), font=('Segoe UI', 10))
    style.map('Aba.TButton', background=[('active', '#1b1b1f')])
    style.configure('AbaAtiva.TButton', background='#1e1e1e', foreground='#10b981', borderwidth=0,
                    anchor='w', padding=(14, 10), font=('Segoe UI', 10, 'bold'))
    style.map('AbaAtiva.TButton', background=[('active', '#1e1e1e')])

    # Botões compactos da barra de ferramentas do Editor
    style.configure('Ferramenta.TButton', padding=(8, 3), font=('Segoe UI', 9))
    style.configure('FerramentaAtiva.TButton', padding=(8, 3), font=('Segoe UI', 9, 'bold'),
                    background='#0f766e', foreground='#ffffff')
    style.map('FerramentaAtiva.TButton', background=[('active', '#0f766e')])
    style.configure('TMenubutton', background='#252526', foreground='#e3e3e3', bordercolor='#2d2d2d',
                    arrowcolor='#e3e3e3', padding=(8, 3), font=('Segoe UI', 9))
    style.map('TMenubutton', background=[('active', '#333333')])
    return style
