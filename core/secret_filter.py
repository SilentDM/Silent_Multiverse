# core/secret_filter.py
import re
from typing import Optional

# Tags explícitas que sempre indicam segredo
TAGS_FIXAS_SEGREDO = [
    "[segredo]", 
    "[segredos]", 
    "<!-- segredo -->", 
    "<-- segredo", 
    "status: segredo", 
    "🤫"
]

def obter_termos_secretos_configurados() -> list[str]:
    """Lê as palavras secretas cadastradas nas Opções e unifica com as tags fixas."""
    termos = list(TAGS_FIXAS_SEGREDO)
    try:
        import ui.settings as st
        cfg = st.carregar_configuracoes()
        raw_palavras = cfg.get("termos_secretos", "")
        if raw_palavras:
            # Separa por vírgula ou ponto-e-vírgula
            extras = [p.strip() for p in raw_palavras.replace(";", ",").split(",") if p.strip()]
            for item in extras:
                if item.lower() not in [t.lower() for t in termos]:
                    termos.append(item)
    except Exception:
        pass
    return termos

def _contem_termo_secreto(texto: str, lista_termos: list[str]) -> bool:
    """
    Verifica se o texto contém qualquer um dos termos secretos.
    Para tags com caracteres especiais (ex: [segredo], 🤫), usa busca direta.
    Para palavras normais (ex: 'Hastur'), usa regex com \b para evitar falsos positivos em substrings.
    """
    if not texto or not lista_termos:
        return False

    texto_lower = texto.lower()

    for termo in lista_termos:
        t_lower = termo.lower()
        # Se contiver símbolos/emojis, compara direto
        if any(c in t_lower for c in "[]<>-:🤫"):
            if t_lower in texto_lower:
                return True
        else:
            # Palavra pura: usa limite de palavra (\b)
            padrao = r'\b' + re.escape(t_lower) + r'\b'
            if re.search(padrao, texto_lower):
                return True

    return False

def filtrar_conteudo_por_permissao(texto_markdown: str, is_dm: bool = True, termos_custom: Optional[list[str]] = None) -> str:
    """
    Se is_dm=True: Retorna o texto 100% completo com todos os segredos.
    Se is_dm=False: Remove seções marcadas, títulos ou parágrafos que mencionem os termos secretos.
    """
    if is_dm or not texto_markdown:
        return texto_markdown

    termos_secretos = termos_custom if termos_custom is not None else obter_termos_secretos_configurados()

    # 1. Checagem de Arquivo Inteiro (se o H1 principal ou YAML tiver a palavra secreta, elimina o arquivo)
    primeiras_linhas = texto_markdown[:1200].splitlines()
    for l in primeiras_linhas:
        l_str = l.strip()
        if l_str.startswith("# ") and _contem_termo_secreto(l_str[2:], termos_secretos):
            return ""
        if "status: segredo" in l.lower():
            return ""
        if "tags:" in l.lower() and _contem_termo_secreto(l, termos_secretos):
            return ""

    linhas = texto_markdown.splitlines()
    linhas_finais = []

    ocultando_secao = False
    nivel_secao_oculta = 0

    # Buffer para processar parágrafos e tópicos completos
    buffer_paragrafo = []

    def flush_buffer():
        nonlocal buffer_paragrafo
        if not buffer_paragrafo:
            return
        bloco_texto = "\n".join(buffer_paragrafo)
        # Se o parágrafo ou bloco contiver a palavra proibida, ele é descartado inteiro
        if not _contem_termo_secreto(bloco_texto, termos_secretos):
            linhas_finais.extend(buffer_paragrafo)
        buffer_paragrafo = []

    for linha in linhas:
        linha_str = linha.strip()

        # Checa se a linha é um Cabeçalho (#, ##, ###)
        match_header = re.match(r'^(#{1,6})\s+(.*)$', linha_str)

        if match_header:
            flush_buffer()
            nivel_atual = len(match_header.group(1))
            header_texto = match_header.group(2)

            # Se estávamos ocultando uma seção e encontramos um cabeçalho de mesmo nível ou superior
            if ocultando_secao and nivel_atual <= nivel_secao_oculta:
                ocultando_secao = False

            # Se o novo cabeçalho contiver o termo proibido (ex: ### A Seita de Hastur)
            if _contem_termo_secreto(header_texto, termos_secretos):
                ocultando_secao = True
                nivel_secao_oculta = nivel_atual
                continue

            if not ocultando_secao:
                linhas_finais.append(linha)
            continue

        # Se estamos dentro de uma seção oculta, ignora tudo até o fim dela
        if ocultando_secao:
            continue

        # Linha em branco marca o fim de um parágrafo
        if not linha_str:
            flush_buffer()
            linhas_finais.append(linha)
            continue

        # Se for início de um item de lista (- ou * ou 1.), avalia o item anterior
        if linha_str.startswith(("- ", "* ", "> ")) or re.match(r'^\d+\.\s', linha_str):
            flush_buffer()

        buffer_paragrafo.append(linha)

    flush_buffer()
    return "\n".join(linhas_finais).strip()