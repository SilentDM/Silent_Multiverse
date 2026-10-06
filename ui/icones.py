"""
Ícones monocromáticos do menu, desenhados a partir dos símbolos da fonte Segoe UI Symbol.

O Tk mistura fontes (e emojis coloridos) quando o texto do botão tem símbolos, e cada ícone
sai de um tamanho; como imagem, todos têm a mesma caixa e a mesma cor.
"""
from PIL import Image, ImageDraw, ImageFont, ImageTk

FONTES = ("seguisym.ttf", "segoeui.ttf", "DejaVuSans.ttf")


def _fonte(tamanho):
    for nome in FONTES:
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            continue
    return ImageFont.load_default()


def icone(janela, simbolo: str, cor: str, lado: int = 18):
    """PhotoImage quadrada com o símbolo centralizado, ligada à janela (fica em cache: o Tk precisa da referência viva)."""
    if not hasattr(janela, "_icones_nexus"):
        janela._icones_nexus = {}
    _cache = janela._icones_nexus
    chave = (simbolo, cor, lado)
    if chave not in _cache:
        escala = 4                      # desenha grande e reduz, para as bordas ficarem suaves
        grande = lado * escala
        imagem = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
        desenho = ImageDraw.Draw(imagem)
        fonte = _fonte(int(grande * 0.8))
        caixa = desenho.textbbox((0, 0), simbolo, font=fonte)
        x = (grande - (caixa[2] - caixa[0])) / 2 - caixa[0]
        y = (grande - (caixa[3] - caixa[1])) / 2 - caixa[1]
        desenho.text((x, y), simbolo, font=fonte, fill=cor)
        _cache[chave] = ImageTk.PhotoImage(imagem.resize((lado, lado), Image.LANCZOS), master=janela)
    return _cache[chave]
