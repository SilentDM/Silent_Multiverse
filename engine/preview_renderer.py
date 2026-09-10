import re, os
from pathlib import Path
import engine.project_utils as pu

CSS_OBSIDIAN_THEME_OLD = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&family=Cinzel:wght@600;800&display=swap');

:root {
    --bg-primary: #1e1e20;
    --bg-secondary: #26262a;
    --bg-tertiary: #18181a;
    --text-normal: #dcddde;
    --text-muted: #999ba0;
    --accent-emerald: #10b981;
    --accent-gold: #d97706;
    --accent-blue: #38bdf8;
    --border-color: #36363a;
}

body {
    background-color: var(--bg-primary);
    color: var(--text-normal);
    font-family: 'Inter', -apple-system, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 0;
}

.container {
    max-width: 860px;
    margin: 0 auto;
    padding: 40px 24px 80px 24px;
}

/* Banner de Capa */
.banner-container {
    width: 100%;
    height: 240px;
    overflow: hidden;
    position: relative;
    border-radius: 8px;
    margin-bottom: 24px;
    background: linear-gradient(135deg, #10b98122, #38bdf822);
}

.banner-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

/* Painel de Propriedades (Obsidian Properties) */
.properties-box {
    background-color: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 28px;
}

.properties-header {
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-muted);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.property-row {
    display: flex;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid #323236;
    font-size: 0.9rem;
}

.property-row:last-child {
    border-bottom: none;
}

.property-key {
    width: 130px;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
}

.property-val {
    flex: 1;
    color: #e4e4e7;
    font-weight: 500;
}

.property-tag {
    background: #10b98122;
    color: #34d399;
    border: 1px solid #10b98155;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.8rem;
    display: inline-block;
    margin-right: 4px;
}

/* Títulos */
h1 { font-size: 2.2rem; color: #ffffff; margin-bottom: 16px; border-bottom: 1px solid var(--border-color); padding-bottom: 8px; }
h2 { font-size: 1.5rem; color: var(--accent-emerald); margin-top: 32px; border-bottom: 1px solid #2d2d30; padding-bottom: 6px; }
h3 { font-size: 1.2rem; color: var(--accent-blue); margin-top: 24px; }

/* Callouts Nativos do Obsidian */
.callout {
    border-radius: 6px;
    margin: 16px 0;
    padding: 14px 16px;
    background: var(--bg-secondary);
    border-left: 4px solid var(--accent-emerald);
}

.callout-title {
    font-weight: 700;
    text-transform: uppercase;
    font-size: 0.85rem;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.callout-quote { border-left-color: #60a5fa; }
.callout-quote .callout-title { color: #60a5fa; }

.callout-warning { border-left-color: #f59e0b; }
.callout-warning .callout-title { color: #f59e0b; }

.callout-danger { border-left-color: #ef4444; }
.callout-danger .callout-title { color: #ef4444; }

.callout-tip { border-left-color: #10b981; }
.callout-tip .callout-title { color: #10b981; }

.callout-summary { border-left-color: #a855f7; }
.callout-summary .callout-title { color: #a855f7; }

/* Tabelas */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 0.95rem;
}

th, td {
    padding: 10px 14px;
    border: 1px solid var(--border-color);
    text-align: left;
}

th {
    background-color: var(--bg-secondary);
    color: var(--accent-emerald);
    font-weight: 600;
}

tr:nth-child(even) {
    background-color: var(--bg-tertiary);
}

/* Wikilinks */
.wikilink {
    color: var(--accent-blue);
    text-decoration: none;
    font-weight: 500;
    background: #38bdf815;
    padding: 2px 6px;
    border-radius: 4px;
    border-bottom: 1px solid #38bdf855;
}

.wikilink:hover {
    background: #38bdf833;
    text-decoration: underline;
}

/* Imagens */
img {
    max-width: 100%;
    border-radius: 6px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    margin: 16px 0;
}

blockquote {
    border-left: 3px solid var(--accent-gold);
    background: #111827;
    margin: 16px 0;
    padding: 10px 18px;
    color: #d1d5db;
    font-style: italic;
    border-radius: 0 4px 4px 0;
}

hr {
    border: none;
    height: 1px;
    background: linear-gradient(to right, transparent, var(--border-color), transparent);
    margin: 32px 0;
}
"""

# Em engine/preview_renderer.py

CSS_OBSIDIAN_THEME = """
html {
    background-color: #1e1e20 !important;
    color: #dcddde !important;
}

body {
    background-color: #1e1e20 !important;
    color: #dcddde !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 0;
}

.container {
    max-width: 860px;
    margin: 0 auto;
    padding: 30px 20px 80px 20px;
}

/* Banner de Capa */
.banner-container {
    width: 100%;
    height: 220px;
    overflow: hidden;
    position: relative;
    border-radius: 8px;
    margin-bottom: 24px;
    background-color: #18181c;
    border: 1px solid #36363a;
}

.banner-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

/* Painel de Propriedades (Obsidian Properties) */
.properties-box {
    background-color: #26262a !important;
    border: 1px solid #36363a;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 28px;
}

.properties-header {
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #999ba0;
    margin-bottom: 10px;
}

.property-row {
    display: flex;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid #323236;
    font-size: 0.9rem;
}

.property-row:last-child {
    border-bottom: none;
}

.property-key {
    width: 140px;
    color: #999ba0;
    font-family: 'Consolas', monospace;
    font-size: 0.85rem;
}

.property-val {
    flex: 1;
    color: #e4e4e7;
    font-weight: 500;
}

.property-tag {
    background-color: #064e3b;
    color: #34d399;
    border: 1px solid #059669;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.8rem;
    display: inline-block;
    margin-right: 4px;
    margin-bottom: 2px;
}

/* Títulos */
h1 {
    font-size: 2.1rem;
    color: #ffffff;
    margin-top: 10px;
    margin-bottom: 16px;
    border-bottom: 2px solid #36363a;
    padding-bottom: 8px;
}

h2 {
    font-size: 1.5rem;
    color: #10b981;
    margin-top: 32px;
    margin-bottom: 12px;
    border-bottom: 1px solid #2d2d30;
    padding-bottom: 6px;
}

h3 {
    font-size: 1.2rem;
    color: #38bdf8;
    margin-top: 24px;
    margin-bottom: 8px;
}

p {
    margin: 12px 0;
    color: #d1d5db;
}

/* Callouts Nativos do Obsidian */
.callout {
    border-radius: 6px;
    margin: 16px 0;
    padding: 12px 16px;
    background-color: #26262a;
    border-left: 4px solid #10b981;
}

.callout-title {
    font-weight: 700;
    text-transform: uppercase;
    font-size: 0.85rem;
    margin-bottom: 6px;
    letter-spacing: 0.5px;
}

.callout-quote { border-left-color: #60a5fa; background-color: #1e293b; }
.callout-quote .callout-title { color: #60a5fa; }

.callout-warning { border-left-color: #f59e0b; background-color: #291e0a; }
.callout-warning .callout-title { color: #f59e0b; }

.callout-danger { border-left-color: #ef4444; background-color: #331518; }
.callout-danger .callout-title { color: #ef4444; }

.callout-tip { border-left-color: #10b981; background-color: #062e24; }
.callout-tip .callout-title { color: #34d399; }

.callout-summary { border-left-color: #a855f7; background-color: #2b173d; }
.callout-summary .callout-title { color: #c084fc; }

/* Tabelas */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 0.95rem;
    background-color: #26262a;
    border: 1px solid #36363a;
}

th, td {
    padding: 10px 14px;
    border: 1px solid #36363a;
    text-align: left;
}

th {
    background-color: #18181c;
    color: #10b981;
    font-weight: 600;
}

tr:nth-child(even) {
    background-color: #1f1f23;
}

/* Wikilinks */
.wikilink {
    color: #38bdf8;
    text-decoration: none;
    font-weight: 500;
    background-color: #0c2838;
    padding: 2px 6px;
    border-radius: 4px;
    border-bottom: 1px solid #0284c7;
}

/* Imagens */
img {
    max-width: 100%;
    border-radius: 6px;
    margin: 16px 0;
    border: 1px solid #36363a;
}

blockquote {
    border-left: 4px solid #d97706;
    background-color: #18181c;
    margin: 16px 0;
    padding: 10px 16px;
    color: #e5e7eb;
    font-style: italic;
    border-radius: 0 4px 4px 0;
}

li {
    margin: 6px 0;
    color: #d1d5db;
}

hr {
    border: none;
    height: 1px;
    background-color: #36363a;
    margin: 28px 0;
}

code {
    background-color: #18181c;
    color: #f97316;
    font-family: 'Consolas', monospace;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
}
"""

def _extrair_frontmatter(texto: str) -> tuple[dict, str]:
    """Separa o bloco YAML --- do restante do texto."""
    if texto.startswith("---"):
        partes = texto.split("---", 2)
        if len(partes) >= 3:
            raw_yaml = partes[1].strip()
            corpo = partes[2].strip()
            metadados = {}
            for linha in raw_yaml.splitlines():
                if ":" in linha and not linha.strip().startswith("#"):
                    k, v = linha.split(":", 1)
                    metadados[k.strip().lower()] = v.strip().strip("\"'")
            return metadados, corpo
    return {}, texto

def _markdown_para_html_rico(conteudo_md: str, caminho_base_arquivo: Path) -> str:
    """Converte sintaxe de Markdown para HTML completo com suporte a tabelas, Callouts e imagens."""
    linhas = []
    em_tabela = False
    em_blockquote = False

    for linha in conteudo_md.splitlines():
        linha_str = linha.strip()

        # Callouts do Obsidian: > [!tipo] Titulo
        match_callout = re.match(r'^>\s*\[!(\w+)\]\s*(.*)$', linha_str, re.IGNORECASE)
        if match_callout:
            tipo = match_callout.group(1).lower()
            titulo = match_callout.group(2).strip() or tipo.title()
            linhas.append(f'<div class="callout callout-{tipo}"><div class="callout-title">📌 {titulo}</div>')
            em_blockquote = True
            continue

        if em_blockquote and not linha_str.startswith(">"):
            linhas.append('</div>')
            em_blockquote = False

        # Tabelas Markdown (| col | col |)
        if linha_str.startswith("|") and linha_str.endswith("|"):
            if not em_tabela:
                linhas.append('<table>')
                em_tabela = True
                # Cabeçalho
                celulas = [c.strip() for c in linha_str.split("|")[1:-1]]
                linhas.append("<tr>" + "".join(f"<th>{c}</th>" for c in celulas) + "</tr>")
                continue
            elif "---" in linha_str:
                continue # Linha separadora do Markdown | :--- |
            else:
                celulas = [c.strip() for c in linha_str.split("|")[1:-1]]
                linhas.append("<tr>" + "".join(f"<td>{c}</td>" for c in celulas) + "</tr>")
                continue
        elif em_tabela:
            linhas.append('</table>')
            em_tabela = False

        if linha_str.startswith("### "):
            linhas.append(f"<h3>{linha_str[4:]}</h3>")
        elif linha_str.startswith("## "):
            linhas.append(f"<h2>{linha_str[3:]}</h2>")
        elif linha_str.startswith("# "):
            linhas.append(f"<h1>{linha_str[2:]}</h1>")
        elif linha_str.startswith("---") or linha_str.startswith("***"):
            linhas.append("<hr>")
        elif linha_str.startswith(">"):
            txt_quote = linha_str.lstrip(">").strip()
            linhas.append(f"<blockquote>{txt_quote}</blockquote>")
        elif linha_str.startswith("- ") or linha_str.startswith("* "):
            linhas.append(f"<li>{linha_str[2:]}</li>")
        elif not linha_str:
            continue
        else:
            linhas.append(f"<p>{linha_str}</p>")

    if em_tabela: linhas.append('</table>')
    if em_blockquote: linhas.append('</div>')

    html = "\n".join(linhas)

    # Negrito e Itálico
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)

    # Wikilinks Obsidian [[Alvo|Alias]] ou [[Alvo]]
    def _sub_wiki(m):
        alvo = m.group(1).strip()
        alias = m.group(2).strip() if m.group(2) else alvo
        return f'<span class="wikilink">🔗 {alias}</span>'

    html = re.sub(r'\[\[([^\|\]]+)(?:\|([^\]]+))?\]\]', _sub_wiki, html)

    # Imagens do Obsidian ![[imagem.png]] ou ![](caminho.png)
    def _sub_img(m):
        nome_img = m.group(1).strip()
        # Tenta resolver o caminho relativo ou na pasta do projeto
        caminho_img = caminho_base_arquivo.parent / nome_img
        if not caminho_img.exists():
            caminho_img = Path(pu.CAMINHO_PROJETO) / nome_img
        uri = caminho_img.as_uri() if caminho_img.exists() else nome_img
        return f'<img src="{uri}" alt="{nome_img}">'

    html = re.sub(r'!\[\[(.*?)\]\]', _sub_img, html)
    html = re.sub(r'!\[.*?\]\((.*?)\)', _sub_img, html)

    return html

def gerar_preview_documento(caminho_arquivo: Path) -> Path:
    """Gera um arquivo HTML temporário formatado como o Obsidian e retorna o caminho."""
    caminho = Path(caminho_arquivo)
    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
        texto = f.read()

    metadados, corpo = _extrair_frontmatter(texto)
    corpo_html = _markdown_para_html_rico(corpo, caminho)

    # Monta a caixa de Propriedades do Obsidian se houver metadados
    caixa_propriedades = ""
    if metadados:
        linhas_props = []
        for k, v in metadados.items():
            if k == "tags":
                tags_html = "".join(f'<span class="property-tag">#{t.strip()}</span>' for t in v.replace("[","").replace("]","").split(","))
                linhas_props.append(f'<div class="property-row"><span class="property-key">{k}</span><span class="property-val">{tags_html}</span></div>')
            else:
                linhas_props.append(f'<div class="property-row"><span class="property-key">{k}</span><span class="property-val">{v}</span></div>')

        caixa_propriedades = f"""
        <div class="properties-box">
            <div class="properties-header">🗂️ Propriedades</div>
            {"".join(linhas_props)}
        </div>
        """

    # Suporte a Banner (se houver 'banner: imagem.png' nas propriedades)
    banner_html = ""
    if "banner" in metadados:
        banner_path = caminho.parent / metadados["banner"]
        if banner_path.exists():
            banner_html = f'<div class="banner-container"><img class="banner-img" src="{banner_path.as_uri()}"></div>'

    html_completo = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Preview: {caminho.stem}</title>
    <style>{CSS_OBSIDIAN_THEME}</style>
</head>
<body>
    <div class="container">
        {banner_html}
        {caixa_propriedades}
        {corpo_html}
    </div>
</body>
</html>
"""

    pasta_preview = pu.PASTA_DADOS_NEXUS / "preview"
    pasta_preview.mkdir(parents=True, exist_ok=True)
    caminho_preview = pasta_preview / f"preview_{caminho.stem}.html"

    with open(caminho_preview, "w", encoding="utf-8") as f:
        f.write(html_completo)

    return caminho_preview

def gerar_html_string_preview(conteudo_md: str, caminho_arquivo: Path = None) -> str:
    """Retorna a string completa do HTML com o CSS estilo Obsidian pronto para o HtmlFrame."""
    metadados, corpo = _extrair_frontmatter(conteudo_md)
    base_path = caminho_arquivo if caminho_arquivo else Path(pu.CAMINHO_PROJETO) / "temp.md"
    corpo_html = _markdown_para_html_rico(corpo, base_path)

    # Caixa de Propriedades (Properties / YAML)
    caixa_propriedades = ""
    if metadados:
        linhas_props = []
        for k, v in metadados.items():
            if k == "tags":
                tags_html = "".join(f'<span class="property-tag">#{t.strip()}</span>' for t in v.replace("[","").replace("]","").split(","))
                linhas_props.append(f'<div class="property-row"><span class="property-key">{k}</span><span class="property-val">{tags_html}</span></div>')
            else:
                linhas_props.append(f'<div class="property-row"><span class="property-key">{k}</span><span class="property-val">{v}</span></div>')

        caixa_propriedades = f"""
        <div class="properties-box">
            <div class="properties-header">🗂️ Propriedades</div>
            {"".join(linhas_props)}
        </div>
        """

    # Suporte a Banner
    banner_html = ""
    if "banner" in metadados and caminho_arquivo:
        banner_path = caminho_arquivo.parent / metadados["banner"]
        if banner_path.exists():
            banner_html = f'<div class="banner-container"><img class="banner-img" src="{banner_path.as_uri()}"></div>'

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <style>{CSS_OBSIDIAN_THEME}</style>
</head>
<body>
    <div class="container">
        {banner_html}
        {caixa_propriedades}
        {corpo_html}
    </div>
</body>
</html>
"""