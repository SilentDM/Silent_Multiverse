"""
Propriedades do Obsidian (o bloco YAML no topo do arquivo, entre linhas "---").

Silent guarda os seus marcadores como propriedades, do jeito que o Obsidian mostra:

    ---
    status: segredo          # ou: secret, rascunho, draft (ou uma lista com vários)
    aliases: [O Rei das Cinzas]
    ---

Arquivos antigos podem ter "status: segredo" como linha solta no texto. Os dois jeitos são lidos;
quando Silent grava um arquivo (normalizar), as linhas soltas viram propriedade. O resto do bloco
YAML é mexido só na chave que muda: o que o Mestre escreveu fica como está.

Sem dependências (não usa PyYAML): o Obsidian só usa o subconjunto simples de YAML tratado aqui.
"""
import re

CHAVE_STATUS = "status"
VALORES_SEGREDO = ("segredo", "secret", "secreto")
VALORES_RASCUNHO = ("rascunho", "draft")
LINHAS_INICIAIS = 40            # marcadores antigos só contam no começo do arquivo

_CHAVE = re.compile(r"^([A-Za-z0-9_\-À-ÿ]+)\s*:(.*)$")
_LINHA_ANTIGA = re.compile(r"^\s*status\s*:\s*\"?'?([A-Za-zÀ-ÿ]+)'?\"?\s*$", re.IGNORECASE)


# ----------------------------------------------------------------------
# LEITURA
# ----------------------------------------------------------------------
def separar(texto: str):
    """(linhas do bloco YAML sem os "---", ou None se não há bloco; o corpo depois dele)."""
    texto = texto or ""
    if texto.startswith("﻿"):
        texto = texto[1:]
    linhas = texto.split("\n")
    if not linhas or linhas[0].strip() != "---":
        return None, texto
    for i in range(1, min(len(linhas), 300)):
        if linhas[i].strip() in ("---", "..."):
            corpo = "\n".join(linhas[i + 1:])
            return [l.rstrip("\r") for l in linhas[1:i]], corpo
    return None, texto


def _limpar(valor: str) -> str:
    valor = valor.strip()
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
        valor = valor[1:-1]
    return valor.strip()


def _valor_lista(bruto: str) -> list:
    bruto = bruto.strip()
    if bruto.startswith("[") and bruto.endswith("]"):
        return [_limpar(v) for v in bruto[1:-1].split(",") if _limpar(v)]
    return [_limpar(bruto)] if _limpar(bruto) else []


def ler(texto: str) -> dict:
    """{chave: valor} do bloco YAML. Listas viram list[str]; o resto, str."""
    linhas, _ = separar(texto)
    propriedades, chave = {}, None
    for linha in linhas or []:
        item = linha.strip()
        if chave and item.startswith("- ") and linha[:1] in (" ", "\t", "-"):
            atual = propriedades.get(chave)
            atual = atual if isinstance(atual, list) else ([atual] if atual else [])
            propriedades[chave] = atual + [_limpar(item[2:])]
            continue
        achado = _CHAVE.match(linha)
        if achado:
            chave, bruto = achado.group(1), achado.group(2).strip()
            propriedades[chave] = _valor_lista(bruto) if bruto.startswith("[") else _limpar(bruto)
    return propriedades


def lista(texto: str, chave: str) -> list:
    valor = ler(texto).get(chave)
    if isinstance(valor, list):
        return [v for v in valor if v]
    return [valor] if valor else []


def _linhas_antigas(corpo: str) -> list:
    """[(índice, valor)] das linhas "status: x" soltas no começo do corpo (formato antigo)."""
    achados = []
    for i, linha in enumerate(corpo.split("\n")[:LINHAS_INICIAIS]):
        achado = _LINHA_ANTIGA.match(linha)
        if achado and achado.group(1).lower() in VALORES_SEGREDO + VALORES_RASCUNHO:
            achados.append((i, achado.group(1).lower()))
    return achados


def estado(texto: str) -> dict:
    """{"segredo": bool, "rascunho": bool} lendo a propriedade status (e as tags) e as linhas antigas."""
    _, corpo = separar(texto)
    valores = [v.lower() for v in lista(texto, CHAVE_STATUS)]
    valores += [v.lower().lstrip("#") for v in lista(texto, "tags")]
    valores += [v for _, v in _linhas_antigas(corpo)]
    return {"segredo": any(v in VALORES_SEGREDO for v in valores),
            "rascunho": any(v in VALORES_RASCUNHO for v in valores)}


def eh_segredo(texto: str) -> bool:
    return estado(texto)["segredo"]


def eh_rascunho(texto: str) -> bool:
    return estado(texto)["rascunho"]


def apelidos(texto: str) -> list:
    """Os aliases do arquivo (o Obsidian também aceita a chave "alias")."""
    return lista(texto, "aliases") + lista(texto, "alias")


def corpo_limpo(texto: str) -> str:
    """O texto sem o bloco YAML e sem as linhas antigas de status (para o livro e a pré-visualização)."""
    _, corpo = separar(texto)
    remover = {i for i, _ in _linhas_antigas(corpo)}
    return "\n".join(l for i, l in enumerate(corpo.split("\n")) if i not in remover).lstrip("\n")


# ----------------------------------------------------------------------
# ESCRITA
# ----------------------------------------------------------------------
def _bloco_da_chave(linhas: list, chave: str):
    """(início, fim) das linhas da chave no bloco YAML (a chave e os itens de lista abaixo dela), ou None."""
    for i, linha in enumerate(linhas):
        achado = _CHAVE.match(linha)
        if achado and achado.group(1).lower() == chave.lower():
            fim = i + 1
            while fim < len(linhas) and (linhas[fim][:1] in (" ", "\t") or linhas[fim].strip().startswith("- ")):
                fim += 1
            return i, fim
    return None


def _formatar(chave: str, valores: list) -> list:
    if len(valores) == 1:
        return [f"{chave}: {valores[0]}"]
    return [f"{chave}:"] + [f"  - {v}" for v in valores]


def definir(linhas: list, chave: str, valores: list) -> list:
    """Troca (ou acrescenta) uma chave no bloco YAML; lista vazia remove a chave."""
    linhas = list(linhas)
    bloco = _bloco_da_chave(linhas, chave)
    novas = _formatar(chave, valores) if valores else []
    if bloco:
        linhas[bloco[0]:bloco[1]] = novas
    else:
        linhas += novas
    return linhas


def _valor_marcador(tipo: str) -> str:
    from core.i18n import tc
    return tc(f"propriedade.{tipo}")


def normalizar(texto: str, segredo=None, rascunho=None) -> str:
    """
    Texto com os marcadores de Silent como propriedades do Obsidian:
      - linhas antigas "status: x" no começo do corpo são retiradas e entram na propriedade status;
      - segredo/rascunho = True ou False ligam/desligam o marcador (None mantém como está).
    Sem nada para marcar, o texto volta igual (Silent não cria bloco YAML vazio).
    """
    linhas, corpo = separar(texto)
    antigas = _linhas_antigas(corpo)
    if antigas:
        remover = {i for i, _ in antigas}
        corpo = "\n".join(l for i, l in enumerate(corpo.split("\n")) if i not in remover)

    atuais = lista(texto, CHAVE_STATUS) if linhas is not None else []
    outros = [v for v in atuais if v.lower() not in VALORES_SEGREDO + VALORES_RASCUNHO]
    nossos = {"segredo": [v for v in atuais if v.lower() in VALORES_SEGREDO],
              "rascunho": [v for v in atuais if v.lower() in VALORES_RASCUNHO]}
    for _, valor in antigas:
        tipo = "segredo" if valor in VALORES_SEGREDO else "rascunho"
        if not nossos[tipo]:
            nossos[tipo] = [valor]
    for tipo, pedido in (("segredo", segredo), ("rascunho", rascunho)):
        if pedido is True and not nossos[tipo]:
            nossos[tipo] = [_valor_marcador(tipo)]
        elif pedido is False:
            nossos[tipo] = []

    valores = outros + nossos["rascunho"][:1] + nossos["segredo"][:1]
    if linhas is None and not valores:
        return texto if not antigas else corpo
    if linhas is None:
        linhas = []
    mudou = antigas or [v.lower() for v in valores] != [v.lower() for v in atuais]
    if not mudou:
        return texto
    linhas = definir(linhas, CHAVE_STATUS, valores)
    if not linhas:
        return corpo.lstrip("\n")
    return "---\n" + "\n".join(linhas) + "\n---\n" + corpo.lstrip("\n")


def mesclar(original: str, novo: str) -> str:
    """
    O texto 'novo' (ex.: a resposta da IA) com as propriedades do 'original': as chaves do original
    ficam como estavam; chaves que só existem no novo são acrescentadas.
    """
    # O original pode ter só a linha antiga "status: segredo": vira propriedade antes, para não se perder
    original = normalizar(original or "")
    linhas_orig, _ = separar(original)
    linhas_novo, corpo_novo = separar(novo or "")
    if linhas_orig is None and linhas_novo is None:
        return novo
    linhas = list(linhas_orig or [])
    if linhas_novo:
        chaves_orig = set(k.lower() for k in ler(original))
        for chave, valor in ler(novo).items():
            if chave.lower() not in chaves_orig:
                linhas = definir(linhas, chave, valor if isinstance(valor, list) else [valor])
    if not linhas:
        return corpo_novo.lstrip("\n")
    return "---\n" + "\n".join(linhas) + "\n---\n" + corpo_novo.lstrip("\n")


def juntar_template(cabecalho: str, template: str) -> str:
    """Esboço + template: se o template tiver propriedades, elas sobem para o topo do arquivo (onde o Obsidian lê)."""
    linhas, corpo = separar(template or "")
    if linhas is None:
        return f"{cabecalho}\n{template or ''}"
    return "---\n" + "\n".join(linhas) + "\n---\n" + f"{cabecalho}\n{corpo.lstrip()}"


# ----------------------------------------------------------------------
# ESQUEMA: as chaves que um arquivo deve ter (vindas do template)
# ----------------------------------------------------------------------
# Hierarquia ao preencher: o que já está no arquivo (inclusive vindo do Obsidian) > o que a IA preencheu
# nas chaves vazias > o valor padrão do template. Chaves fora do esquema que a IA inventar são descartadas.
CHAVES_BASE = (("type", None), ("tags", []), ("aliases", []))
# Chaves antigas (em português) que já valem pela chave em inglês do esquema
EQUIVALENTES = {"type": ("tipo",), "system": ("sistema",),
                "level": ("nivel", "nível", "nivel_recomendado", "recommended_level")}


def vazio(valor) -> bool:
    if isinstance(valor, list):
        return not [v for v in valor if str(v).strip()]
    return not str(valor or "").strip()


def valor_de(propriedades: dict, chave: str):
    """Valor da chave (ou de uma chave equivalente antiga, ex.: tipo para type), ignorando maiúsculas."""
    nomes = (chave,) + EQUIVALENTES.get(chave, ())
    for nome, valor in propriedades.items():
        if nome.lower() in nomes and not vazio(valor):
            return valor
    return None


def esquema_de(texto: str) -> list:
    """[(chave, padrão)] na ordem do bloco YAML (ex.: o de um template). Padrão vazio vira None ou []."""
    linhas, _ = separar(texto)
    esquema = []
    for chave, valor in ler(texto).items():
        if isinstance(valor, list):
            esquema.append((chave, valor))
        else:
            bruto = next((l for l in linhas or [] if _CHAVE.match(l) and _CHAVE.match(l).group(1) == chave), "")
            lista_vazia = bruto.split(":", 1)[-1].strip() == "[]"
            esquema.append((chave, [] if lista_vazia else (valor or None)))
    return esquema


def _yaml_escalar(valor) -> str:
    valor = str(valor).strip()
    if not valor:
        return ""
    if valor.startswith(("[", "{", "*", "&", "!", "%", "@", "`", "'", '"')) or ": " in valor or " #" in valor:
        return '"' + valor.replace('"', "'") + '"'
    return valor


def _yaml_valor(valor) -> str:
    if isinstance(valor, list):
        return "[" + ", ".join(_yaml_escalar(v) for v in valor if str(v).strip()) + "]"
    return _yaml_escalar(valor)


def aplicar_esquema(original: str, novo: str, esquema: list, valores_ia: dict = None, incluir_vazias: bool = True) -> str:
    """
    O corpo do texto 'novo' com o bloco de propriedades do 'original' completado pelo esquema:
    as chaves do original ficam como estão; chaves do esquema vazias ou ausentes recebem o valor
    da IA (valores_ia) ou, sem ele, o padrão do template. Nada fora do esquema é acrescentado.
    incluir_vazias=False não acrescenta chaves que ficariam sem valor (esquema básico, sem template).
    """
    original = normalizar(original or "")
    linhas, _ = separar(original)
    linhas = list(linhas or [])
    atuais = ler(original)
    valores_ia = valores_ia or {}
    for chave, padrao in esquema:
        if chave.lower() == CHAVE_STATUS or valor_de(atuais, chave) is not None:
            continue                                              # o arquivo já tem: vence sempre
        valor = valor_de(valores_ia, chave)
        if valor is None:
            valor = padrao
        if isinstance(padrao, list) and valor is not None and not isinstance(valor, list):
            valor = [v.strip() for v in str(valor).split(",") if v.strip()]
        bloco = _bloco_da_chave(linhas, chave)
        texto_valor = _yaml_valor(valor) if valor is not None else ""
        if vazio(valor) and not incluir_vazias:
            continue
        if not texto_valor and isinstance(padrao, list):
            texto_valor = "[]"
        nova = f"{chave}: {texto_valor}".rstrip()
        if bloco:
            linhas[bloco[0]:bloco[1]] = [nova]
        else:
            linhas.append(nova)
    _, corpo_novo = separar(novo or "")
    if not linhas:
        return corpo_novo.lstrip("\n")
    return "---\n" + "\n".join(linhas) + "\n---\n" + corpo_novo.lstrip("\n")
